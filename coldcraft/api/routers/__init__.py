"""Versioned API routers for /api/v1."""
from .campaigns import get_campaigns_router
from .config import get_config_router
from .drafts import get_drafts_router
from .features import get_features_router
from .health import health_router
from .integrations import get_integrations_router
from .intel import get_intel_router
from .jobs import get_jobs_router
from .policies import get_policies_router
from .profile import get_profile_router
from .tracking import get_tracking_router

__all__ = [
    "health_router",
    "get_drafts_router",
    "get_campaigns_router",
    "get_config_router",
    "get_features_router",
    "get_integrations_router",
    "get_intel_router",
    "get_jobs_router",
    "get_policies_router",
    "get_profile_router",
    "get_tracking_router",
]
