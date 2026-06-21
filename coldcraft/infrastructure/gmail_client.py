import base64
import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from ..llm import generate_json

logger = logging.getLogger(__name__)

MOCK_THREADS = [
    {
        "id": "thread_mock_1",
        "subject": "Update on your application for Software Engineer",
        "snippet": "Unfortunately, we have decided to move forward with other candidates at this time.",
        "from_email": "careers@google.com",
        "from_name": "Google Careers",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "status": "rejected",
        "timestamp": "2026-06-20T10:00:00Z",
        "body": "Hi Biraj, Thank you for taking the time to apply and speak with us. Unfortunately, we have decided to move forward with other candidates at this time. We will keep your resume on file. Best, Google Recruiting.",
        "message_id": "<mock_msg_1@google.com>"
    },
    {
        "id": "thread_mock_2",
        "subject": "Interview scheduling: Coldcraft developer role",
        "snippet": "We loved your cold email and projects! We would like to invite you to a 30-minute technical interview.",
        "from_email": "hr@37signals.com",
        "from_name": "37signals Recruiting",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "status": "interview",
        "timestamp": "2026-06-21T09:30:00Z",
        "body": "Hello Biraj, We loved your cold email and projects! We would like to invite you to a 30-minute technical interview. Please use this calendly link to schedule a time: calendly.com/37signals-hr/30min. Looking forward to chatting!",
        "message_id": "<mock_msg_2@37signals.com>"
    },
    {
        "id": "thread_mock_3",
        "subject": "Quick question about your GitHub projects",
        "snippet": "Hey Biraj, I saw your Coldcraft project on GitHub. It looks really interesting. Are you still looking for a role?",
        "from_email": "hiring@replit.com",
        "from_name": "Replit Team",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "status": "follow-up",
        "timestamp": "2026-06-21T11:00:00Z",
        "body": "Hey Biraj, I saw your Coldcraft project on GitHub. It looks really interesting. Are you still looking for a role? We have an opening for a backend engineer. Let me know when you'd be free to chat.",
        "message_id": "<mock_msg_3@replit.com>"
    },
    {
        "id": "thread_mock_4",
        "subject": "Application Received: Frontend Engineer",
        "snippet": "Thank you for applying to the Frontend Engineer role at Stripe. We have received your application and will review it shortly.",
        "from_email": "jobs@stripe.com",
        "from_name": "Stripe Jobs",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "status": "applied",
        "timestamp": "2026-06-19T14:22:00Z",
        "body": "Thank you for applying to the Frontend Engineer role at Stripe. We have received your application and will review it shortly. You can track your status in our portal.",
        "message_id": "<mock_msg_4@stripe.com>"
    }
]

MOCK_UNSUBSCRIBE_THREADS = [
    {
        "id": "thread_unsub_mock_1",
        "subject": "Weekly Newsletter: AI Trends",
        "snippet": "Learn about the latest trends in Generative AI and agentic workflows.",
        "from_email": "newsletter@aitrends.com",
        "from_name": "AI Trends",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "timestamp": "2026-05-15T08:00:00Z",
        "body": "This is our weekly newsletter. If you want to unsubscribe, click the link below.",
        "list_unsubscribe": "<mailto:unsub-123@aitrends.com?subject=unsubscribe>, <https://aitrends.com/unsub/123>",
        "unsubscribe_mailto": "mailto:unsub-123@aitrends.com?subject=unsubscribe",
        "unsubscribe_url": "https://aitrends.com/unsub/123",
        "status": "pending"
    },
    {
        "id": "thread_unsub_mock_2",
        "subject": "Special Offer: 50% Off Premium Plan",
        "snippet": "Don't miss our summer sale! Upgrade now to get full access.",
        "from_email": "promo@saasbox.io",
        "from_name": "SaaSBox Support",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "timestamp": "2026-05-10T12:30:00Z",
        "body": "Special summer offer for our premium service.",
        "list_unsubscribe": "<https://saasbox.io/unsubscribe?token=abcxyz>",
        "unsubscribe_mailto": None,
        "unsubscribe_url": "https://saasbox.io/unsubscribe?token=abcxyz",
        "status": "pending"
    },
    {
        "id": "thread_unsub_mock_3",
        "subject": "Your Daily Digest of Coding Questions",
        "snippet": "Solve today's coding challenges and improve your software engineering skills.",
        "from_email": "digest@codingdaily.org",
        "from_name": "Coding Daily Digest",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "timestamp": "2026-05-20T06:00:00Z",
        "body": "Here are today's questions.",
        "list_unsubscribe": "<mailto:unsubscribe@codingdaily.org>",
        "unsubscribe_mailto": "mailto:unsubscribe@codingdaily.org",
        "unsubscribe_url": None,
        "status": "pending"
    },
    {
        "id": "thread_unsub_mock_4",
        "subject": "Spammy Notifications Without Unsubscribe Link",
        "snippet": "Just a spammy notification email that doesn't include any unsubscribe headers.",
        "from_email": "notifications@spammybrand.com",
        "from_name": "Spammy Brand",
        "to_email": "birajdarushi@gmail.com",
        "to_name": "Biraj",
        "timestamp": "2026-04-01T15:00:00Z",
        "body": "Some notification details.",
        "list_unsubscribe": None,
        "unsubscribe_mailto": None,
        "unsubscribe_url": None,
        "status": "pending"
    }
]

def _make_request(url: str, headers: dict = None, data: dict = None, method: str = 'GET') -> dict:
    headers = headers or {}
    req_data = None
    if data is not None:
        if isinstance(data, dict):
            req_data = json.dumps(data).encode('utf-8')
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
        elif isinstance(data, str):
            req_data = data.encode('utf-8')
        else:
            req_data = data

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            err_json = json.loads(err_body)
            error_msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            error_msg = err_body
        logger.error(f"HTTP Error {e.code} during request to {url}: {error_msg}")
        raise Exception(f"HTTP Error {e.code}: {error_msg}")

def _extract_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

def _extract_body(payload: dict) -> str:
    """Recursively extract plain text or HTML body from Gmail message payload."""
    body_data = payload.get("body", {}).get("data", "")
    mime_type = payload.get("mimeType", "")
    
    if body_data:
        try:
            # Gmail uses base64url encoding
            decoded = base64.urlsafe_b64decode(body_data.encode('ascii')).decode('utf-8', errors='ignore')
            return decoded
        except Exception:
            pass

    parts = payload.get("parts", [])
    text_content = []
    for part in parts:
        part_body = _extract_body(part)
        if part_body:
            text_content.append(part_body)
    
    return "\n".join(text_content)

def _parse_email_address(raw_email: str) -> tuple[str, str]:
    """Parse format like 'Name <email@domain.com>' into ('email@domain.com', 'Name')."""
    if not raw_email:
        return "", ""
    raw_email = raw_email.strip()
    if "<" in raw_email and ">" in raw_email:
        parts = raw_email.split("<")
        name = parts[0].strip().strip('"').strip("'")
        email = parts[1].split(">")[0].strip()
        return email, name
    return raw_email, raw_email

def parse_list_unsubscribe(header_value: str) -> tuple[str | None, str | None]:
    """Parse mailto and url links from List-Unsubscribe header."""
    if not header_value:
        return None, None
    
    mailto_link = None
    url_link = None
    
    # Split by comma to check multiple links
    parts = header_value.split(",")
    for part in parts:
        part = part.strip()
        if part.startswith("<") and part.endswith(">"):
            link = part[1:-1].strip()
            if link.startswith("mailto:"):
                mailto_link = link
            elif link.startswith("http://") or link.startswith("https://"):
                url_link = link
                
    return mailto_link, url_link

class GmailClient:
    def get_authorization_url(self, client_id: str, redirect_uri: str) -> str:
        """Generate Google OAuth 2.0 authorization URL."""
        if not client_id:
            # Fallback to mock callback URL so user can complete a mock connection
            return f"{redirect_uri}?code=mock_authorization_code"
            
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.readonly",
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    def get_tokens_from_code(self, client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
        """Exchange auth code for tokens."""
        if code.startswith("mock_"):
            return {
                "access_token": "mock_access_token_" + str(int(time.time())),
                "refresh_token": "mock_refresh_token_" + str(int(time.time())),
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
                "expires_in": 3600
            }

        url = "https://oauth2.googleapis.com/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        data_encoded = urllib.parse.urlencode(data)
        return _make_request(url, headers=headers, data=data_encoded, method="POST")

    def refresh_access_token(self, client_id: str, client_secret: str, refresh_token: str) -> dict:
        """Refresh expired access token."""
        if refresh_token.startswith("mock_"):
            return {
                "access_token": "mock_access_token_refreshed_" + str(int(time.time())),
                "expires_in": 3600
            }

        url = "https://oauth2.googleapis.com/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        data_encoded = urllib.parse.urlencode(data)
        return _make_request(url, headers=headers, data=data_encoded, method="POST")

    def list_threads(self, access_token: str, max_results: int = 20) -> list[dict]:
        """Fetch threads from Gmail or return mocks if mock token."""
        if not access_token or access_token.startswith("mock_"):
            # Return copy of mocks to avoid modifying global state
            import copy
            return copy.deepcopy(MOCK_THREADS)

        # Real Google Gmail API call
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads?maxResults={max_results}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            res = _make_request(url, headers=headers)
        except Exception as e:
            logger.error(f"Failed to fetch Gmail threads: {e}")
            raise

        threads = res.get("threads", [])
        parsed_threads = []
        
        for t in threads:
            thread_id = t.get("id")
            thread_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
            try:
                t_detail = _make_request(thread_url, headers=headers)
                messages = t_detail.get("messages", [])
                if not messages:
                    continue
                
                # We analyze the thread history: first message gives subject, last message/messages give content
                first_msg = messages[0]
                last_msg = messages[-1]
                
                f_headers = first_msg.get("payload", {}).get("headers", [])
                subject = _extract_header(f_headers, "Subject") or "(No Subject)"
                
                l_headers = last_msg.get("payload", {}).get("headers", [])
                from_raw = _extract_header(l_headers, "From")
                to_raw = _extract_header(l_headers, "To")
                date_raw = _extract_header(l_headers, "Date")
                
                from_email, from_name = _parse_email_address(from_raw)
                to_email, to_name = _parse_email_address(to_raw)
                
                # Body content of the thread (all messages concatenated or just the last message)
                # Let's concatenate all message bodies to represent thread history
                history_list = []
                for m in messages:
                    body_part = _extract_body(m.get("payload", {}))
                    if body_part:
                        history_list.append(body_part)
                body = "\n---\n".join(history_list)
                
                # Classify the thread
                status = self.classify_thread(subject, body)
                
                # Timestamp
                msg_time_ms = last_msg.get("internalDate")
                if msg_time_ms:
                    timestamp = datetime.fromtimestamp(int(msg_time_ms) / 1000, tz=timezone.utc).isoformat()
                else:
                    timestamp = datetime.now(timezone.utc).isoformat()

                parsed_threads.append({
                    "id": thread_id,
                    "subject": subject,
                    "snippet": last_msg.get("snippet", ""),
                    "from_email": from_email,
                    "from_name": from_name,
                    "to_email": to_email,
                    "to_name": to_name,
                    "status": status,
                    "timestamp": timestamp,
                    "body": body,
                    "message_id": _extract_header(l_headers, "Message-ID")
                })
            except Exception as e:
                logger.error(f"Error parsing thread {thread_id}: {e}")
                continue
                
        return parsed_threads

    def classify_thread(self, subject: str, body: str) -> str:
        """Classify thread using LLM or rule-based heuristics."""
        try:
            system = (
                "You are an AI assistant for email triage. "
                "Classify the following email thread into one of these tags: 'applied', 'rejected', 'interview', 'follow-up'. "
                "Respond with a JSON object: {\"tag\": \"one_of_the_tags\"}."
            )
            prompt = f"Subject: {subject}\n\nBody:\n{body[:1500]}"
            res = generate_json(system, prompt, max_tokens=100)
            tag = res.get("tag")
            if tag in ["applied", "rejected", "interview", "follow-up"]:
                return tag
        except Exception:
            pass

        # Rule-based heuristics fallback
        text = f"{subject} {body}".lower()
        if any(w in text for w in ["decided to move forward with other", "not moving forward", "unfortunately, we cannot", "positions are filled", "reject", "unable to offer", "decided not to"]):
            return "rejected"
        if any(w in text for w in ["schedule a call", "interview", "phone screen", "availability to chat", "technical test", "calendly.com", "speak next week", "time to chat"]):
            return "interview"
        if any(w in text for w in ["application received", "successfully applied", "thank you for applying", "your application to"]):
            return "applied"
        return "follow-up"

    def generate_reply_draft(self, subject: str, thread_history: str) -> dict:
        """Use Gemini to generate a reply draft based on thread history."""
        try:
            system = (
                "You are a professional assistant helping a job seeker reply to recruiter/company emails. "
                "Draft a suitable reply. The tone should be polite, professional, concise, and eager. "
                "Do not include placeholders like [Your Name] if you can avoid it, or use the job seeker's name if known (or leave it clean). "
                "Respond with a JSON object: {\"subject\": \"...\", \"body\": \"...\"}"
            )
            prompt = f"Subject: {subject}\n\nEmail History:\n{thread_history[:3000]}\n\nDraft a reply."
            res = generate_json(system, prompt, max_tokens=1000)
            if "subject" in res and "body" in res:
                return res
        except Exception:
            pass

        # Fallback heuristic drafts
        text = thread_history.lower()
        if "interview" in text or "schedule" in text or "calendly" in text:
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            reply_body = (
                "Hi, thank you so much for the update! I would be thrilled to schedule an interview. "
                "I will check the link and schedule a time that works best. Looking forward to speaking with you!"
            )
            return {"subject": reply_subject, "body": reply_body}
        elif "reject" in text or "not moving forward" in text or "not to move forward" in text or "unfortunately" in text:
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            reply_body = (
                "Thank you for letting me know. While I'm disappointed, I really appreciate the feedback and "
                "taking the time to review my application. I wish the team all the best."
            )
            return {"subject": reply_subject, "body": reply_body}
        else:
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            reply_body = (
                "Hi, thank you for reaching out! I appreciate the follow-up. "
                "I would love to chat further and answer any questions you have. Let me know what times work best for you."
            )
            return {"subject": reply_subject, "body": reply_body}

    def _prepare_mime_message(self, thread_id: str, reply_subject: str, reply_body: str, to_email: str, message_id: str) -> str:
        """Create RFC 2822 base64url encoded message structure."""
        headers = [
            f"To: {to_email}",
            f"Subject: {reply_subject}",
            "Content-Type: text/html; charset=utf-8",
            "MIME-Version: 1.0",
        ]
        if message_id:
            headers.append(f"In-Reply-To: {message_id}")
            headers.append(f"References: {message_id}")
            
        mime_msg = "\r\n".join(headers) + "\r\n\r\n" + reply_body
        
        # Base64url encode
        raw = base64.urlsafe_b64encode(mime_msg.encode('utf-8')).decode('ascii')
        return raw

    def create_draft_reply(self, access_token: str, thread_id: str, reply_subject: str, reply_body: str, to_email: str, message_id: str) -> dict:
        """Create a draft reply on Gmail, or return a mock if access token is mock."""
        if not access_token or access_token.startswith("mock_"):
            return {
                "id": f"draft_mock_{int(time.time())}",
                "message": {
                    "threadId": thread_id,
                    "subject": reply_subject,
                    "body": reply_body,
                    "to": to_email
                }
            }

        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        raw_mime = self._prepare_mime_message(thread_id, reply_subject, reply_body, to_email, message_id)
        data = {
            "message": {
                "threadId": thread_id,
                "raw": raw_mime
            }
        }
        
        return _make_request(url, headers=headers, data=data, method="POST")

    def send_reply(self, access_token: str, thread_id: str, reply_subject: str, reply_body: str, to_email: str, message_id: str) -> str:
        """Send a reply email in a Gmail thread, or mock it if access token is mock."""
        if not access_token or access_token.startswith("mock_"):
            return f"msg_mock_{int(time.time())}"

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        raw_mime = self._prepare_mime_message(thread_id, reply_subject, reply_body, to_email, message_id)
        data = {
            "threadId": thread_id,
            "raw": raw_mime
        }
        
        res = _make_request(url, headers=headers, data=data, method="POST")
        return res.get("id", "")

    def get_user_profile(self, access_token: str) -> dict:
        """Get the user's Gmail profile containing their email address."""
        if not access_token or access_token.startswith("mock_"):
            return {"emailAddress": "birajdarushi@gmail.com"}
        url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return _make_request(url, headers=headers)

    def send_email(self, access_token: str, to_email: str, subject: str, body: str) -> str:
        """Send a simple text email (used for mailto unsubscription)."""
        if not access_token or access_token.startswith("mock_"):
            return f"msg_mock_unsub_{int(time.time())}"
            
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare simple MIME message
        mime_parts = [
            f"To: {to_email}",
            f"Subject: {subject}",
            "Content-Type: text/plain; charset=utf-8",
            "MIME-Version: 1.0",
        ]
        mime_msg = "\r\n".join(mime_parts) + "\r\n\r\n" + body
        raw = base64.urlsafe_b64encode(mime_msg.encode('utf-8')).decode('ascii')
        data = {"raw": raw}
        res = _make_request(url, headers=headers, data=data, method="POST")
        return res.get("id", "")

    def scan_unsubscribed_targets(self, access_token: str, max_results: int = 50) -> list[dict]:
        """Scan for threads that are unread, older than 30 days, not starred, and not labeled by user."""
        if not access_token or access_token.startswith("mock_"):
            import copy
            return copy.deepcopy(MOCK_UNSUBSCRIBE_THREADS)

        # Query to find unread threads older than 30 days and not starred
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads?q=is:unread+older_than:30d+-is:starred&maxResults={max_results}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            res = _make_request(url, headers=headers)
        except Exception as e:
            logger.error(f"Failed to scan Gmail threads for unsubscribe: {e}")
            raise

        threads = res.get("threads", [])
        parsed_candidates = []
        
        SYSTEM_LABELS = {
            "INBOX", "UNREAD", "STARRED", "SENT", "DRAFT", "IMPORTANT", 
            "SPAM", "TRASH", "CATEGORY_PERSONAL", "CATEGORY_SOCIAL", 
            "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_FORUMS",
            "CHAT", "VOICEMAIL", "UNSPAMED"
        }

        for t in threads:
            thread_id = t.get("id")
            thread_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
            try:
                t_detail = _make_request(thread_url, headers=headers)
                messages = t_detail.get("messages", [])
                if not messages:
                    continue
                
                # Check for user-defined labels on any message in the thread
                has_user_label = False
                for msg in messages:
                    label_ids = msg.get("labelIds", [])
                    for lid in label_ids:
                        if lid not in SYSTEM_LABELS:
                            has_user_label = True
                            break
                    if has_user_label:
                        break
                        
                if has_user_label:
                    # Skip thread because it has custom user labels
                    continue

                first_msg = messages[0]
                last_msg = messages[-1]
                
                f_headers = first_msg.get("payload", {}).get("headers", [])
                subject = _extract_header(f_headers, "Subject") or "(No Subject)"
                
                # Extract List-Unsubscribe header
                list_unsub_val = None
                for m in messages:
                    m_headers = m.get("payload", {}).get("headers", [])
                    list_unsub_val = _extract_header(m_headers, "List-Unsubscribe")
                    if list_unsub_val:
                        break
                
                l_headers = last_msg.get("payload", {}).get("headers", [])
                from_raw = _extract_header(l_headers, "From")
                from_email, from_name = _parse_email_address(from_raw)
                
                msg_time_ms = last_msg.get("internalDate")
                if msg_time_ms:
                    timestamp = datetime.fromtimestamp(int(msg_time_ms) / 1000, tz=timezone.utc).isoformat()
                else:
                    timestamp = datetime.now(timezone.utc).isoformat()

                # Check for other emails from same domain/sender that are read/opened
                domain = from_email.split("@")[-1] if "@" in from_email else None
                has_read_email = False
                if domain:
                    PUBLIC_DOMAINS = {
                        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", 
                        "icloud.com", "zoho.com", "proton.me", "protonmail.com", "mail.com",
                        "yandex.com", "gmx.com", "fastmail.com"
                    }
                    if domain.lower() in PUBLIC_DOMAINS:
                        q = f"from:{from_email} is:read"
                    else:
                        q = f"from:{domain} is:read"
                    
                    check_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={urllib.parse.quote(q)}&maxResults=1"
                    try:
                        check_res = _make_request(check_url, headers=headers)
                        if check_res.get("messages"):
                            has_read_email = True
                    except Exception as e:
                        logger.error(f"Error checking read status for domain {domain}: {e}")
                
                if has_read_email:
                    # Skip since we have read at least one email from this sender/domain
                    continue

                mailto_link, url_link = parse_list_unsubscribe(list_unsub_val)

                parsed_candidates.append({
                    "id": thread_id,
                    "subject": subject,
                    "snippet": last_msg.get("snippet", ""),
                    "from_email": from_email,
                    "from_name": from_name,
                    "timestamp": timestamp,
                    "list_unsubscribe": list_unsub_val,
                    "unsubscribe_mailto": mailto_link,
                    "unsubscribe_url": url_link,
                    "status": "pending"
                })
            except Exception as e:
                logger.error(f"Error scanning thread {thread_id} for unsubscribe candidate: {e}")
                continue
                
        return parsed_candidates

    def unsubscribe_thread(self, access_token: str, thread_id: str) -> dict:
        """Execute unsubscription on a thread by sending mailto, visiting unsubscribe URL, and archiving/muting the thread."""
        if not access_token or access_token.startswith("mock_"):
            return {"status": "unsubscribed", "methods": ["mock_success"], "list_unsubscribe": None, "mailto_link": None, "url_link": None}
            
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        thread_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        
        try:
            t_detail = _make_request(thread_url, headers=headers)
        except Exception as e:
            logger.error(f"Failed to fetch thread {thread_id} for unsubscribe: {e}")
            raise Exception(f"Failed to fetch thread: {e}")
            
        messages = t_detail.get("messages", [])
        if not messages:
            raise Exception("No messages in thread")
            
        list_unsub_val = None
        for m in messages:
            m_headers = m.get("payload", {}).get("headers", [])
            list_unsub_val = _extract_header(m_headers, "List-Unsubscribe")
            if list_unsub_val:
                break
                
        mailto_link, url_link = parse_list_unsubscribe(list_unsub_val)
        method_used = []
        
        # 1. Execute mailto unsubscribe
        if mailto_link:
            try:
                parsed_mailto = urllib.parse.urlparse(mailto_link)
                to_addr = parsed_mailto.path
                query_params = urllib.parse.parse_qs(parsed_mailto.query)
                sub = query_params.get("subject", ["Unsubscribe"])[0]
                body = query_params.get("body", ["Please unsubscribe me."])[0]
                
                self.send_email(access_token, to_addr, sub, body)
                method_used.append("mailto")
            except Exception as e:
                logger.error(f"Failed to send mailto unsubscribe for thread {thread_id}: {e}")
                
        # 2. Execute URL unsubscribe
        if url_link:
            try:
                req = urllib.request.Request(url_link, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    response.read()
                method_used.append("url_get")
            except Exception as e:
                logger.error(f"Failed to request unsubscribe URL {url_link}: {e}")
                
        # 3. Archive and Mute thread (always, as a fallback)
        try:
            modify_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/modify"
            modify_data = {
                "addLabelIds": ["MUTE"],
                "removeLabelIds": ["INBOX"]
            }
            _make_request(modify_url, headers=headers, data=modify_data, method="POST")
            method_used.append("archive_mute")
        except Exception as e:
            logger.error(f"Failed to archive/mute thread {thread_id}: {e}")
            
        return {
            "status": "unsubscribed",
            "methods": method_used,
            "list_unsubscribe": list_unsub_val,
            "mailto_link": mailto_link,
            "url_link": url_link
        }

    def list_threads_paginated(self, access_token: str, max_results: int = 20, page_token: str | None = None) -> dict:
        """Fetch threads from Gmail with pagination, or return mocks if mock token."""
        if not access_token or access_token.startswith("mock_"):
            import copy
            return {
                "threads": copy.deepcopy(MOCK_THREADS),
                "next_page_token": None
            }

        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads?maxResults={max_results}"
        if page_token:
            url += f"&pageToken={page_token}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            res = _make_request(url, headers=headers)
        except Exception as e:
            logger.error(f"Failed to fetch Gmail threads: {e}")
            raise

        threads = res.get("threads", [])
        parsed_threads = []
        
        for t in threads:
            thread_id = t.get("id")
            thread_url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
            try:
                t_detail = _make_request(thread_url, headers=headers)
                messages = t_detail.get("messages", [])
                if not messages:
                    continue
                
                first_msg = messages[0]
                last_msg = messages[-1]
                
                f_headers = first_msg.get("payload", {}).get("headers", [])
                subject = _extract_header(f_headers, "Subject") or "(No Subject)"
                
                l_headers = last_msg.get("payload", {}).get("headers", [])
                from_raw = _extract_header(l_headers, "From")
                to_raw = _extract_header(l_headers, "To")
                
                from_email, from_name = _parse_email_address(from_raw)
                to_email, to_name = _parse_email_address(to_raw)
                
                history_list = []
                for m in messages:
                    body_part = _extract_body(m.get("payload", {}))
                    if body_part:
                        history_list.append(body_part)
                body = "\n---\n".join(history_list)
                
                status = self.classify_thread(subject, body)
                
                msg_time_ms = last_msg.get("internalDate")
                if msg_time_ms:
                    timestamp = datetime.fromtimestamp(int(msg_time_ms) / 1000, tz=timezone.utc).isoformat()
                else:
                    timestamp = datetime.now(timezone.utc).isoformat()

                parsed_threads.append({
                    "id": thread_id,
                    "subject": subject,
                    "snippet": last_msg.get("snippet", ""),
                    "from_email": from_email,
                    "from_name": from_name,
                    "to_email": to_email,
                    "to_name": to_name,
                    "status": status,
                    "timestamp": timestamp,
                    "body": body,
                    "message_id": _extract_header(l_headers, "Message-ID")
                })
            except Exception as e:
                logger.error(f"Error parsing thread {thread_id}: {e}")
                continue
                
        return {
            "threads": parsed_threads,
            "next_page_token": res.get("nextPageToken")
        }

    def archive_thread(self, access_token: str, thread_id: str) -> dict:
        """Archive a thread by removing the INBOX label."""
        if not access_token or access_token.startswith("mock_"):
            return {"status": "archived", "thread_id": thread_id}
            
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/modify"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "removeLabelIds": ["INBOX"]
        }
        _make_request(url, headers=headers, data=data, method="POST")
        return {"status": "archived", "thread_id": thread_id}

    def trash_thread(self, access_token: str, thread_id: str) -> dict:
        """Trash a thread."""
        if not access_token or access_token.startswith("mock_"):
            return {"status": "trashed", "thread_id": thread_id}
            
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/trash"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        _make_request(url, headers=headers, method="POST")
        return {"status": "trashed", "thread_id": thread_id}

    def get_thread(self, access_token: str, thread_id: str) -> dict:
        """Fetch details of a specific thread by ID."""
        if not access_token or access_token.startswith("mock_"):
            import copy
            mock_t = next((t for t in MOCK_THREADS + MOCK_UNSUBSCRIBE_THREADS if t["id"] == thread_id), None)
            if mock_t:
                return copy.deepcopy(mock_t)
            raise Exception("Mock thread not found")
            
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return _make_request(url, headers=headers)

    def get_parsed_thread(self, access_token: str, thread_id: str) -> dict:
        """Fetch details of a specific thread and return it in parsed form."""
        if not access_token or access_token.startswith("mock_"):
            import copy
            mock_t = next((t for t in MOCK_THREADS + MOCK_UNSUBSCRIBE_THREADS if t["id"] == thread_id), None)
            if mock_t:
                return copy.deepcopy(mock_t)
            raise Exception("Mock thread not found")

        t_detail = self.get_thread(access_token, thread_id)
        messages = t_detail.get("messages", [])
        if not messages:
            raise Exception("Thread has no messages")

        first_msg = messages[0]
        last_msg = messages[-1]

        f_headers = first_msg.get("payload", {}).get("headers", [])
        subject = _extract_header(f_headers, "Subject") or "(No Subject)"

        l_headers = last_msg.get("payload", {}).get("headers", [])
        from_raw = _extract_header(l_headers, "From")
        to_raw = _extract_header(l_headers, "To")
        date_raw = _extract_header(l_headers, "Date")

        from_email, from_name = _parse_email_address(from_raw)
        to_email, to_name = _parse_email_address(to_raw)

        history_list = []
        for m in messages:
            body_part = _extract_body(m.get("payload", {}))
            if body_part:
                history_list.append(body_part)
        body = "\n---\n".join(history_list)

        status = self.classify_thread(subject, body)

        msg_time_ms = last_msg.get("internalDate")
        if msg_time_ms:
            timestamp = datetime.fromtimestamp(int(msg_time_ms) / 1000, tz=timezone.utc).isoformat()
        else:
            timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "id": thread_id,
            "subject": subject,
            "snippet": last_msg.get("snippet", ""),
            "from_email": from_email,
            "from_name": from_name,
            "to_email": to_email,
            "to_name": to_name,
            "status": status,
            "timestamp": timestamp,
            "body": body,
            "message_id": _extract_header(l_headers, "Message-ID")
        }


