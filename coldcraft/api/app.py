import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..agent import MailerAgent
from ..db.session import init_db
from ..infrastructure.persistence.repositories import SQLAlchemyCampaignRepository
from .routers import (
    get_auth_router,
    get_campaigns_router,
    get_config_router,
    get_drafts_router,
    get_features_router,
    get_integrations_router,
    get_intel_router,
    get_jobs_router,
    get_policies_router,
    get_profile_router,
    get_providers_router,
    get_resumes_router,
    health_router,
    get_tracking_router,
)
from .schemas import DraftRequest, ReplyRequest

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        logger.info("Database initialized")
        yield

    app = FastAPI(title="Coldcraft API", version="0.1.0", lifespan=lifespan)
    agent = MailerAgent(config=None)
    campaigns = SQLAlchemyCampaignRepository()

    # CORS. Localhost dev origins are always allowed; deployed frontend origins
    # come from CORS_ORIGINS (comma-separated), e.g.
    #   CORS_ORIGINS=https://gtm-zeta-nine.vercel.app,https://app.coldcraft.io
    import os

    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra = os.environ.get("CORS_ORIGINS", "")
    allowed_origins += [o.strip() for o in extra.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        # Allow Vercel preview deployments (https://<project>-<hash>.vercel.app)
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Primary mounts under /api/v1 (API-first Phase 1)
    app.include_router(health_router, prefix="/api/v1")

    # Email-OTP login (passwordless)
    app.include_router(get_auth_router(), prefix="/api/v1")
    drafts_router = get_drafts_router(agent, campaigns)
    campaigns_router = get_campaigns_router(campaigns, agent)
    app.include_router(drafts_router, prefix="/api/v1")
    app.include_router(campaigns_router, prefix="/api/v1")

    # Config (real implementation for p1-config-api)
    config_router = get_config_router(campaigns)
    app.include_router(config_router, prefix="/api/v1")

    # Profile (p1-profile-api)
    profile_router = get_profile_router(campaigns)
    app.include_router(profile_router, prefix="/api/v1")

    # Policies (p1-policies-api) - clamped to constitution
    policies_router = get_policies_router(campaigns)
    app.include_router(policies_router, prefix="/api/v1")

    # Features (p1-features-api)
    features_router = get_features_router(campaigns)
    app.include_router(features_router, prefix="/api/v1")

    # Integrations (p2-integration-config)
    integrations_router = get_integrations_router(campaigns)
    app.include_router(integrations_router, prefix="/api/v1")

    # Providers / API keys (LLM + scraper provider keys, encrypted at rest)
    providers_router = get_providers_router(campaigns)
    app.include_router(providers_router, prefix="/api/v1")

    # Resumes / cover letters (LaTeX docs: store + compile to PDF)
    resumes_router = get_resumes_router(campaigns)
    app.include_router(resumes_router, prefix="/api/v1")

    # Jobs scraper (p2-scraper)
    jobs_router = get_jobs_router(campaigns)
    app.include_router(jobs_router, prefix="/api/v1")

    # Intel reports (p2-intel-report)
    intel_router = get_intel_router(campaigns)
    app.include_router(intel_router, prefix="/api/v1")

    # Tracking (p1-tracking-api): public /track/* (no /api/v1 for pixel compat in emails)
    tracking_router = get_tracking_router(campaigns)
    app.include_router(tracking_router, prefix="")

    # Stats (p1-stats-api) - simple aggregates using repo
    @app.get("/api/v1/stats")
    def get_stats():
        sent_today = campaigns.sent_today_count()
        # pending_approvals: qa_passed or user_approved
        pending = campaigns.count_by_status("qa_passed") + campaigns.count_by_status("user_approved")
        # rough open_rate: (opened + replied) / sent if sent>0
        sent = campaigns.count_by_status("sent")
        opened = campaigns.count_by_status("opened") + campaigns.count_by_status("replied")
        open_rate = (opened / sent) if sent > 0 else 0.0
        return {
            "sent_today": sent_today,
            "open_rate": round(open_rate, 2),
            "pending_approvals": pending,
        }

    return app


app = create_app()