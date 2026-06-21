import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ...config.secrets import encrypt_secret
from ..schemas import IntegrationResponse, IntegrationUpdate, serialize_integrations

logger = logging.getLogger(__name__)


def get_integrations_router(campaigns_repo) -> APIRouter:
    """Integration config router.

    GET/PUT /api/v1/integrations for scraper, Apify, IMAP etc.

    - Secrets (apify_token etc.) are encrypted on write and **never** returned in GET responses.
    - Uses the same encryption key as SMTP config.
    - Singleton row (upsert pattern).
    """
    router = APIRouter(prefix="/integrations", tags=["integrations"])

    @router.get("", response_model=IntegrationResponse)
    def get_integrations():
        data = campaigns_repo.get_integrations()
        return serialize_integrations(data)

    @router.put("", response_model=IntegrationResponse)
    def put_integrations(body: IntegrationUpdate):
        apify_enc = None
        if body.apify_token:
            try:
                apify_enc = encrypt_secret(body.apify_token)
            except RuntimeError:
                logger.exception("Failed to encrypt integration secret")
                raise HTTPException(status_code=500, detail="Internal server error") from None
        # If no new token provided, we pass None so repo preserves existing enc value

        campaigns_repo.save_integrations(
            apify_token_enc=apify_enc,
            scraper_sources=body.scraper_sources,
        )

        data = campaigns_repo.get_integrations()
        return serialize_integrations(data)

    @router.get("/github/connect")
    def connect_github(
        redirect_uri: str | None = None,
        frontend_origin: str | None = None,
    ):
        """
        Returns the GitHub OAuth authorization URL.

        redirect_uri — the callback URL GitHub will redirect to after auth.
          Defaults to {API_BASE}/api/v1/integrations/github/callback so that
          the backend handles the code exchange and redirects the browser
          to the frontend settings page (avoids redirect_uri_mismatch errors).

        frontend_origin — where to send the user after a successful exchange.
          Defaults to http://localhost:5173.
        """
        client_id = os.environ.get("GITHUB_CLIENT_ID") or "mock_github_client_id"
        api_base = os.environ.get("API_BASE_URL", "http://localhost:8000")
        callback_uri = redirect_uri or f"{api_base}/api/v1/integrations/github/callback"
        if frontend_origin:
            # Encode origin so callback knows where to redirect the browser
            import urllib.parse
            callback_uri += f"?frontend_origin={urllib.parse.quote(frontend_origin, safe='')}"
        url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={callback_uri}"
            f"&scope=repo,user"
        )
        return {"redirect_url": url}

    @router.get("/github/callback")
    def callback_github(
        code: str,
        frontend_origin: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ):
        """
        GitHub sends the browser here after the user authorises the app.
        We exchange the code for a token, save it, then redirect the browser
        back to the frontend settings page with ?github=connected (or ?github=error).
        """
        # Where to send the browser after exchange
        origin = frontend_origin or os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
        settings_url = f"{origin}/settings?tab=integrations"

        # GitHub can send an error back (e.g. user denied)
        if error:
            logger.warning(f"GitHub OAuth error: {error} — {error_description}")
            return RedirectResponse(url=f"{settings_url}&github=error&reason={error}")

        client_id = os.environ.get("GITHUB_CLIENT_ID") or "mock_github_client_id"
        client_secret = os.environ.get("GITHUB_CLIENT_SECRET") or "mock_github_client_secret"

        if code.startswith("mock_") or client_id == "mock_github_client_id":
            token = "mock_github_token_" + code
            username = "mock_github_user"
        else:
            try:
                import httpx
                headers = {"Accept": "application/json"}
                data = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                }
                res = httpx.post(
                    "https://github.com/login/oauth/access_token",
                    headers=headers,
                    json=data,
                    timeout=10.0,
                )
                res_data = res.json()
                if "error" in res_data:
                    err_msg = res_data.get("error_description", res_data["error"])
                    logger.error(f"GitHub token exchange failed: {err_msg}")
                    return RedirectResponse(url=f"{settings_url}&github=error&reason={err_msg}")

                token = res_data.get("access_token")
                if not token:
                    return RedirectResponse(url=f"{settings_url}&github=error&reason=no_access_token")

                user_res = httpx.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=5.0,
                )
                if user_res.status_code != 200:
                    return RedirectResponse(url=f"{settings_url}&github=error&reason=user_fetch_failed")

                username = user_res.json().get("login") or "github_user"
            except Exception as e:
                logger.error(f"GitHub OAuth callback failed: {e}")
                return RedirectResponse(url=f"{settings_url}&github=error&reason=exception")

        try:
            token_enc = encrypt_secret(token)
            campaigns_repo.save_integrations(github_token_enc=token_enc, github_username=username)
        except Exception as e:
            logger.error(f"Failed to store GitHub token: {e}")
            return RedirectResponse(url=f"{settings_url}&github=error&reason=storage_failed")

        # Redirect browser back to the frontend settings page
        return RedirectResponse(url=f"{settings_url}&github=connected&username={username}")

    @router.post("/github/disconnect", response_model=IntegrationResponse)
    def disconnect_github():
        """Clear the stored GitHub token. Uses clear_github=True so the repo
        explicitly nulls both columns rather than treating None as 'don't update'.
        """
        campaigns_repo.save_integrations(clear_github=True)
        data = campaigns_repo.get_integrations()
        return serialize_integrations(data)

    return router
