import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ...config.secrets import encrypt_secret
from ...infrastructure.gmail_client import GmailClient
from ..middleware.rate_limit import check_send_rate_limit

logger = logging.getLogger(__name__)

class InboxSendReplyRequest(BaseModel):
    subject: str
    body: str
    to_email: str

class BulkUnsubscribeRequest(BaseModel):
    thread_ids: list[str]

def get_inbox_router(campaigns_repo) -> APIRouter:
    """Inbox Hub Router.
    
    GET /api/v1/inbox/connect -> returns Google OAuth2 redirect URL.
    GET /api/v1/inbox/callback -> exchanges code for credentials and saves them.
    GET /api/v1/inbox/threads -> lists threads.
    POST /api/v1/inbox/threads/{id}/reply -> generates a reply draft.
    """
    router = APIRouter(prefix="/inbox", tags=["inbox"])

    def find_credential_and_thread(thread_id: str, all_creds: list[dict]):
        """Checks each credential to find the one that owns the given thread_id.
        Returns (decrypted_credential, parsed_thread).
        If thread_id is mock, returns (None, mock_parsed_thread).
        If not found in any, raises 404 HTTPException.
        """
        from ...infrastructure.gmail_client import MOCK_THREADS, MOCK_UNSUBSCRIBE_THREADS
        mock_thread = next((t for t in MOCK_THREADS + MOCK_UNSUBSCRIBE_THREADS if t["id"] == thread_id), None)
        if mock_thread:
            import copy
            return None, copy.deepcopy(mock_thread)

        if not all_creds:
            raise HTTPException(status_code=404, detail="Thread not found (no Gmail accounts connected)")

        client = GmailClient()
        for cred in all_creds:
            import datetime
            from datetime import timezone
            now = datetime.datetime.now(timezone.utc)
            updated_at = cred["updated_at"]
            access_token = cred["access_token"]
            refresh_token = cred["refresh_token"]
            client_id = cred["client_id"]
            client_secret = cred["client_secret"]
            email = cred.get("email") or "unknown@gmail.com"

            needs_refresh = False
            if updated_at:
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if (now - updated_at).total_seconds() > 3000:
                    needs_refresh = True

            if needs_refresh and refresh_token and client_id and client_secret:
                try:
                    tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                    access_token = tokens["access_token"]
                    new_access_enc = encrypt_secret(access_token)
                    campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                    cred["access_token"] = access_token
                except Exception as e:
                    logger.error(f"Failed to refresh access token during thread lookup for {email}: {e}")

            try:
                parsed_t = client.get_parsed_thread(access_token, thread_id)
                return cred, parsed_t
            except Exception as e:
                if "HTTP Error 401" in str(e) and refresh_token and client_id and client_secret:
                    try:
                        tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                        access_token = tokens["access_token"]
                        new_access_enc = encrypt_secret(access_token)
                        campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                        cred["access_token"] = access_token
                        parsed_t = client.get_parsed_thread(access_token, thread_id)
                        return cred, parsed_t
                    except Exception:
                        pass
                continue

        raise HTTPException(status_code=404, detail="Thread not found in any connected Gmail account")

    @router.get("/connect")
    def connect(redirect_uri: str = "http://localhost:8000/api/v1/inbox/callback"):
        import os
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        
        decrypted = campaigns_repo.get_decrypted_gmail_credentials()
        if decrypted and decrypted.get("client_id"):
            client_id = decrypted["client_id"]
            
        client = GmailClient()
        url = client.get_authorization_url(client_id, redirect_uri)
        return {"redirect_url": url}

    @router.get("/callback")
    def callback(code: str, redirect_uri: str = "http://localhost:8000/api/v1/inbox/callback"):
        import os
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        
        decrypted = campaigns_repo.get_decrypted_gmail_credentials()
        if decrypted:
            if decrypted.get("client_id"):
                client_id = decrypted["client_id"]
            if decrypted.get("client_secret"):
                client_secret = decrypted["client_secret"]

        client = GmailClient()
        try:
            tokens = client.get_tokens_from_code(
                client_id=client_id or "mock_client_id",
                client_secret=client_secret or "mock_client_secret",
                redirect_uri=redirect_uri,
                code=code
            )
        except Exception as e:
            logger.exception("Failed to exchange authorization code for tokens")
            raise HTTPException(status_code=400, detail=str(e))
            
        try:
            client_id_enc = encrypt_secret(client_id or "mock_client_id")
            client_secret_enc = encrypt_secret(client_secret or "mock_client_secret")
            access_token_enc = encrypt_secret(tokens["access_token"])
            refresh_token_enc = encrypt_secret(tokens.get("refresh_token") or "mock_refresh_token")
        except Exception as e:
            logger.exception("Failed to encrypt Gmail secrets")
            raise HTTPException(status_code=500, detail="Failed to encrypt secrets")

        email = "unknown@gmail.com"
        if tokens.get("access_token"):
            try:
                profile_info = client.get_user_profile(tokens["access_token"])
                if profile_info.get("emailAddress"):
                    email = profile_info["emailAddress"]
            except Exception as e:
                logger.error(f"Failed to fetch Google user email: {e}")

        campaigns_repo.save_gmail_credentials(
            email=email,
            client_id_enc=client_id_enc,
            client_secret_enc=client_secret_enc,
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            token_uri=tokens.get("token_uri") or "https://oauth2.googleapis.com/token",
            scopes=tokens.get("scopes") or tokens.get("scope", "").split() or ["https://www.googleapis.com/auth/gmail.modify"],
        )
        
        return {"status": "connected", "message": f"Gmail account {email} connected successfully."}

    @router.get("/threads")
    def list_threads(page_token: str | None = None):
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        if not all_creds:
            # Return mock threads
            client = GmailClient()
            return {
                "threads": client.list_threads(access_token="mock_access_token"),
                "next_page_token": None
            }

        client = GmailClient()
        all_threads = []
        import datetime
        import base64
        import json
        from datetime import timezone
        
        # Decode multi-account page tokens
        tokens = {}
        if page_token:
            try:
                decoded = base64.b64decode(page_token.encode()).decode()
                tokens = json.loads(decoded)
            except Exception:
                pass

        next_tokens = {}
        for decrypted in all_creds:
            access_token = decrypted["access_token"]
            refresh_token = decrypted["refresh_token"]
            client_id = decrypted["client_id"]
            client_secret = decrypted["client_secret"]
            email = decrypted.get("email") or "unknown@gmail.com"
            
            # Token refresh logic
            now = datetime.datetime.now(timezone.utc)
            updated_at = decrypted["updated_at"]
            
            needs_refresh = False
            if updated_at:
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if (now - updated_at).total_seconds() > 3000:
                    needs_refresh = True
                    
            if needs_refresh and refresh_token and client_id and client_secret:
                try:
                    tokens_refresh = client.refresh_access_token(client_id, client_secret, refresh_token)
                    new_access_token = tokens_refresh["access_token"]
                    new_access_enc = encrypt_secret(new_access_token)
                    campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                    access_token = new_access_token
                except Exception as e:
                    logger.error(f"Failed to refresh access token for {email}: {e}")

            page_token_for_cred = tokens.get(email)
            try:
                res_dict = client.list_threads_paginated(access_token, page_token=page_token_for_cred)
                threads = res_dict.get("threads", [])
                for t in threads:
                    t["connected_email"] = email
                all_threads.extend(threads)
                
                next_tok = res_dict.get("next_page_token")
                if next_tok:
                    next_tokens[email] = next_tok
            except Exception as e:
                # Retry once if 401
                if "HTTP Error 401" in str(e) and refresh_token and client_id and client_secret:
                    try:
                        tokens_refresh = client.refresh_access_token(client_id, client_secret, refresh_token)
                        new_access_token = tokens_refresh["access_token"]
                        new_access_enc = encrypt_secret(new_access_token)
                        campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                        res_dict = client.list_threads_paginated(new_access_token, page_token=page_token_for_cred)
                        threads = res_dict.get("threads", [])
                        for t in threads:
                            t["connected_email"] = email
                        all_threads.extend(threads)
                        next_tok = res_dict.get("next_page_token")
                        if next_tok:
                            next_tokens[email] = next_tok
                        continue
                    except Exception as retry_err:
                        logger.error(f"Failed retry to fetch threads for {email}: {retry_err}")
                logger.error(f"Failed to list Gmail threads for {email}: {e}")

        # Dedup threads by ID in case they show up in multiple accounts or query
        seen_threads = {}
        for t in all_threads:
            seen_threads[t["id"]] = t
        unique_threads = list(seen_threads.values())
        unique_threads.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Encode next page tokens
        next_page_token = None
        if next_tokens:
            try:
                encoded = base64.b64encode(json.dumps(next_tokens).encode()).decode()
                next_page_token = encoded
            except Exception:
                pass
                
        return {
            "threads": unique_threads,
            "next_page_token": next_page_token
        }

    @router.post("/threads/{thread_id}/reply")
    def create_reply(thread_id: str):
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        cred, matched = find_credential_and_thread(thread_id, all_creds)
        client = GmailClient()
        
        subject = matched["subject"]
        body = matched["body"]
        to_email = matched["from_email"]
        message_id = matched.get("message_id", "")

        draft_content = client.generate_reply_draft(subject, body)
        reply_subject = draft_content.get("subject") or f"Re: {subject}"
        reply_body = draft_content.get("body") or ""
        
        response_data = {
            "thread_id": thread_id,
            "subject": reply_subject,
            "body": reply_body,
            "to_email": to_email
        }
        
        active_token = cred["access_token"] if cred else None
        if active_token and not active_token.startswith("mock_"):
            try:
                g_draft = client.create_draft_reply(
                    access_token=active_token,
                    thread_id=thread_id,
                    reply_subject=reply_subject,
                    reply_body=reply_body,
                    to_email=to_email,
                    message_id=message_id
                )
                if "id" in g_draft:
                    response_data["draft_id"] = g_draft["id"]
            except Exception as e:
                logger.error(f"Failed to create Gmail draft: {e}")
                
        return response_data

    @router.post("/threads/{thread_id}/send")
    def send_reply(thread_id: str, payload: InboxSendReplyRequest, request: Request):
        # ── Rate limit: guest IPs get 5 sends/hr, authed users 50/day ────────
        # Resolve the caller's email from the Fernet session token (if present)
        _user_email: str | None = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            _raw_token = auth_header[7:].strip()
            try:
                from ...auth import service as _auth_svc
                _user_email = _auth_svc.verify_token(_raw_token)
            except Exception:
                pass
        check_send_rate_limit(request, user_email=_user_email)
        # ─────────────────────────────────────────────────────────────────────

        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        cred, matched = find_credential_and_thread(thread_id, all_creds)
        
        client = GmailClient()
        access_token = cred["access_token"] if cred else "mock_access_token"
        matched_message_id = matched.get("message_id", "")
        
        try:
            sent_id = client.send_reply(
                access_token=access_token,
                thread_id=thread_id,
                reply_subject=payload.subject,
                reply_body=payload.body,
                to_email=payload.to_email,
                message_id=matched_message_id
            )
            return {"status": "sent", "message_id": sent_id}
        except Exception as e:
            logger.error(f"Failed to send reply for thread {thread_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/unsubscribe/scan")
    def scan_unsubscribe():
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        if not all_creds:
            client = GmailClient()
            return client.scan_unsubscribed_targets(access_token="mock_access_token")

        client = GmailClient()
        all_candidates = []
        import datetime
        from datetime import timezone
        
        for decrypted in all_creds:
            access_token = decrypted["access_token"]
            refresh_token = decrypted["refresh_token"]
            client_id = decrypted["client_id"]
            client_secret = decrypted["client_secret"]
            email = decrypted.get("email") or "unknown@gmail.com"
            
            # Token refresh logic
            now = datetime.datetime.now(timezone.utc)
            updated_at = decrypted["updated_at"]
            
            needs_refresh = False
            if updated_at:
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if (now - updated_at).total_seconds() > 3000:
                    needs_refresh = True
                    
            if needs_refresh and refresh_token and client_id and client_secret:
                try:
                    tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                    new_access_token = tokens["access_token"]
                    new_access_enc = encrypt_secret(new_access_token)
                    campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                    access_token = new_access_token
                except Exception as e:
                    logger.error(f"Failed to refresh access token for {email}: {e}")

            try:
                candidates = client.scan_unsubscribed_targets(access_token)
                for c in candidates:
                    c["connected_email"] = email
                all_candidates.extend(candidates)
            except Exception as e:
                if "HTTP Error 401" in str(e) and refresh_token and client_id and client_secret:
                    try:
                        tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                        new_access_token = tokens["access_token"]
                        new_access_enc = encrypt_secret(new_access_token)
                        campaigns_repo.save_gmail_credentials(email=email, access_token_enc=new_access_enc)
                        candidates = client.scan_unsubscribed_targets(new_access_token)
                        for c in candidates:
                            c["connected_email"] = email
                        all_candidates.extend(candidates)
                        continue
                    except Exception as retry_err:
                        logger.error(f"Failed retry to scan threads for {email}: {retry_err}")
                logger.error(f"Failed to scan Gmail threads for {email}: {e}")

        # Group candidates by from_email (only keep the latest thread per sender)
        seen_senders = {}
        for c in all_candidates:
            email_key = c["from_email"].lower().strip()
            if email_key not in seen_senders:
                seen_senders[email_key] = c
            else:
                if c["timestamp"] > seen_senders[email_key]["timestamp"]:
                    seen_senders[email_key] = c
        unique_candidates = list(seen_senders.values())
        unique_candidates.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return unique_candidates

    @router.post("/threads/{thread_id}/unsubscribe")
    def unsubscribe_thread(thread_id: str):
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        cred, _ = find_credential_and_thread(thread_id, all_creds)
        
        client = GmailClient()
        access_token = cred["access_token"] if cred else "mock_access_token"
        try:
            res = client.unsubscribe_thread(access_token, thread_id)
            return res
        except Exception as e:
            logger.error(f"Failed to unsubscribe thread {thread_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/unsubscribe/bulk")
    def bulk_unsubscribe(payload: BulkUnsubscribeRequest):
        results = []
        for tid in payload.thread_ids:
            try:
                res = unsubscribe_thread(tid)
                results.append({"thread_id": tid, "status": "success", "details": res})
            except Exception as e:
                results.append({"thread_id": tid, "status": "failed", "error": str(e)})
        return {"results": results}

    @router.post("/threads/{thread_id}/archive")
    def archive_thread(thread_id: str):
        """Archive a thread. Tries all credentials until one succeeds.
        Does NOT pre-fetch the thread (avoids 404 on archived/trashed threads).
        """
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        client = GmailClient()

        if not all_creds:
            # Mock mode
            return {"status": "archived", "thread_id": thread_id}

        last_err = None
        for cred in all_creds:
            access_token = cred.get("access_token", "")
            try:
                res = client.archive_thread(access_token, thread_id)
                return res
            except Exception as e:
                last_err = e
                # If 401, try refreshing once
                if "HTTP Error 401" in str(e):
                    refresh_token = cred.get("refresh_token")
                    client_id = cred.get("client_id")
                    client_secret = cred.get("client_secret")
                    email = cred.get("email", "unknown@gmail.com")
                    if refresh_token and client_id and client_secret:
                        try:
                            tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                            access_token = tokens["access_token"]
                            encrypt_secret(access_token)  # store update
                            campaigns_repo.save_gmail_credentials(email=email, access_token_enc=encrypt_secret(access_token))
                            res = client.archive_thread(access_token, thread_id)
                            return res
                        except Exception as re_err:
                            last_err = re_err
                continue

        logger.error(f"Failed to archive thread {thread_id} across all credentials: {last_err}")
        raise HTTPException(status_code=500, detail=f"Archive failed: {last_err}")

    @router.post("/threads/{thread_id}/trash")
    def trash_thread(thread_id: str):
        """Trash a thread. Tries all credentials until one succeeds.
        Does NOT pre-fetch the thread (avoids 404 on threads not in normal list).
        """
        all_creds = campaigns_repo.get_all_decrypted_gmail_credentials()
        client = GmailClient()

        if not all_creds:
            # Mock mode
            return {"status": "trashed", "thread_id": thread_id}

        last_err = None
        for cred in all_creds:
            access_token = cred.get("access_token", "")
            try:
                res = client.trash_thread(access_token, thread_id)
                return res
            except Exception as e:
                last_err = e
                if "HTTP Error 401" in str(e):
                    refresh_token = cred.get("refresh_token")
                    client_id = cred.get("client_id")
                    client_secret = cred.get("client_secret")
                    email = cred.get("email", "unknown@gmail.com")
                    if refresh_token and client_id and client_secret:
                        try:
                            tokens = client.refresh_access_token(client_id, client_secret, refresh_token)
                            access_token = tokens["access_token"]
                            campaigns_repo.save_gmail_credentials(email=email, access_token_enc=encrypt_secret(access_token))
                            res = client.trash_thread(access_token, thread_id)
                            return res
                        except Exception as re_err:
                            last_err = re_err
                continue

        logger.error(f"Failed to trash thread {thread_id} across all credentials: {last_err}")
        raise HTTPException(status_code=500, detail=f"Trash failed: {last_err}")

    return router
