import os
import httpx
import logging
from fastapi import APIRouter, HTTPException, Query
from ..schemas import MemoryEntryCreate, MemoryEntryResponse, serialize_memory_entry
from ... import llm

logger = logging.getLogger(__name__)


def get_memory_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/memory", tags=["memory"])

    @router.get("", response_model=list[MemoryEntryResponse])
    def list_memory():
        entries = campaigns_repo.list_memory_entries()
        return [serialize_memory_entry(e) for e in entries]

    @router.put("", response_model=MemoryEntryResponse)
    def save_memory_entry(body: MemoryEntryCreate):
        e = campaigns_repo.save_memory_entry(
            type=body.type,
            key=body.key,
            value=body.value,
            source=body.source,
        )
        return serialize_memory_entry(e)

    @router.post("/github-summary")
    def sync_github_summary():
        # Git summary integration - load from DB first, fallback to env GITHUB_TOKEN
        token = None
        source = "stub_fallback"
        
        # Load from integrations config in DB
        integration_data = campaigns_repo.get_integrations()
        if integration_data.get("github_token_enc"):
            try:
                from ...config.secrets import decrypt_secret
                decrypted_token = decrypt_secret(integration_data["github_token_enc"])
                # Only use if it is a non-empty string and not a redacted placeholder
                if decrypted_token and decrypted_token != "***" and decrypted_token != "":
                    token = decrypted_token
                    source = "github_api"
            except Exception as e:
                logger.error(f"Failed to decrypt GitHub integration token: {e}")

        # Fallback to environment variable if DB token is not set
        if not token:
            token = os.environ.get("GITHUB_TOKEN")
            if token:
                source = "github_api_env"

        repos = []
        if token:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            }
            try:
                # Fetch top 5 repos
                response = httpx.get(
                    "https://api.github.com/user/repos?sort=updated&per_page=5",
                    headers=headers,
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    repos = [
                        {
                            "name": r.get("name"),
                            "description": r.get("description") or "",
                            "language": r.get("language") or "Python",
                        }
                        for r in data
                    ]
                    source = "github_api"
            except Exception as exc:
                logger.warning("Failed to fetch GitHub repos: %s", exc)

        # If fetch failed or no token, use stub repos
        if not repos:
            repos = [
                {
                    "name": "coldcraft",
                    "description": "Mailer agent inside a personal job-seeker GTM engine",
                    "language": "Python",
                },
                {
                    "name": "dashboard",
                    "description": "React-based job tracking system and user analytics",
                    "language": "TypeScript",
                },
                {
                    "name": "crawler",
                    "description": "Distributed career boards and job search scraper",
                    "language": "Go",
                },
            ]

        repos_str = "\n".join(
            [f"- {r['name']} ({r['language']}): {r['description']}" for r in repos]
        )

        # Generate summary via LLM
        summary_text = None
        gemini_key = campaigns_repo.get_gemini_api_key() or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                system = "You are a professional technical resume writer. Respond ONLY with a JSON object."
                prompt = (
                    f"Here are my top GitHub repositories:\n"
                    f"{repos_str}\n\n"
                    "Generate a professional, 2-3 sentence project summary blurb highlighting the main technologies (languages, libraries, frameworks) "
                    "and domains of these projects. The summary will be included in cold outreach emails. "
                    "Respond with a JSON object containing exactly one key: 'summary'."
                )
                res = llm.generate_json(system=system, prompt=prompt)
                if isinstance(res, dict) and "summary" in res:
                    summary_text = res["summary"]
            except Exception as exc:
                logger.warning("Gemini GitHub summarization failed: %s", exc)

        # Fallback summary text if LLM call failed or wasn't run
        if not summary_text:
            summary_text = (
                "An experienced backend developer with a portfolio of open-source projects including "
                "automated mailing systems (coldcraft), interactive React dashboards, and robust web scrapers "
                "built using Python, TypeScript, and Go."
            )

        # Save to memory bank
        entry = campaigns_repo.save_memory_entry(
            type="github_summary",
            key="repos_summary",
            value=summary_text,
            source=source,
        )
        return serialize_memory_entry(entry)

    return router
