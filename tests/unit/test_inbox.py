import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from coldcraft.db import session as db_session
from coldcraft.infrastructure.gmail_client import GmailClient
from coldcraft.api.app import app
from coldcraft.infrastructure.persistence.repositories import SQLAlchemyCampaignRepository

def _fresh_db_env():
    """Point the app at a throwaway SQLite DB and a fresh signing key, and
    rebuild the cached engine so it binds to that DB."""
    os.environ["GTM_SMTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    db_file = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file

    db_session._engine = None
    db_session._SessionLocal = None
    db_session.init_db()
    return db_file


class GmailClientUnitTests(unittest.TestCase):
    def setUp(self):
        self.client = GmailClient()

    def test_get_authorization_url_with_client_id(self):
        url = self.client.get_authorization_url("client123", "http://localhost/callback")
        self.assertIn("client_id=client123", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%2Fcallback", url)
        self.assertIn("response_type=code", url)
        self.assertTrue(url.startswith("https://accounts.google.com/o/oauth2/v2/auth"))

    def test_get_authorization_url_mock_fallback(self):
        url = self.client.get_authorization_url("", "http://localhost/callback")
        self.assertEqual(url, "http://localhost/callback?code=mock_authorization_code")

    def test_classify_thread_rejected_heuristic(self):
        body = "Thank you for applying. Unfortunately, we decided to move forward with other candidates at this time."
        tag = self.client.classify_thread("Application Update", body)
        self.assertEqual(tag, "rejected")

    def test_classify_thread_interview_heuristic(self):
        body = "We loved your profile. Can we schedule a phone interview call? Please choose a time on my calendly."
        tag = self.client.classify_thread("Scheduling screen", body)
        self.assertEqual(tag, "interview")

    def test_classify_thread_applied_heuristic(self):
        body = "Thank you! Your application has been successfully received. We will review it shortly."
        tag = self.client.classify_thread("Application Received", body)
        self.assertEqual(tag, "applied")

    def test_classify_thread_follow_up_default(self):
        body = "Just checking if you received my previous email about the contract details."
        tag = self.client.classify_thread("Checking in", body)
        self.assertEqual(tag, "follow-up")

    @patch("coldcraft.infrastructure.gmail_client.generate_json")
    def test_classify_thread_llm_success(self, mock_generate_json):
        mock_generate_json.return_value = {"tag": "interview"}
        tag = self.client.classify_thread("Hello", "Some content")
        self.assertEqual(tag, "interview")
        mock_generate_json.assert_called_once()

    @patch("coldcraft.infrastructure.gmail_client.generate_json", side_effect=Exception("No LLM key"))
    def test_generate_reply_draft_interview_fallback(self, mock_generate_json):
        history = "Let's schedule a call to interview next week."
        draft = self.client.generate_reply_draft("Interview Scheduling", history)
        self.assertIn("thrilled to schedule an interview", draft["body"])
        self.assertEqual(draft["subject"], "Re: Interview Scheduling")

    @patch("coldcraft.infrastructure.gmail_client.generate_json", side_effect=Exception("No LLM key"))
    def test_generate_reply_draft_rejection_fallback(self, mock_generate_json):
        history = "We have decided not to move forward with your application."
        draft = self.client.generate_reply_draft("Job Update", history)
        self.assertIn("appreciate the feedback", draft["body"])
        self.assertEqual(draft["subject"], "Re: Job Update")


    @patch("coldcraft.infrastructure.gmail_client.generate_json")
    def test_generate_reply_draft_llm_success(self, mock_generate_json):
        mock_generate_json.return_value = {
            "subject": "Custom Subject",
            "body": "Custom Body content"
        }
        draft = self.client.generate_reply_draft("Update", "Email text here")
        self.assertEqual(draft["subject"], "Custom Subject")
        self.assertEqual(draft["body"], "Custom Body content")


class InboxApiTests(unittest.TestCase):
    def setUp(self):
        self.db_file = _fresh_db_env()
        self.client_cm = TestClient(app)
        self.client = self.client_cm.__enter__()
        self.repo = SQLAlchemyCampaignRepository()

    def tearDown(self):
        self.client_cm.__exit__(None, None, None)
        try:
            os.remove(self.db_file)
        except OSError:
            pass

    def test_connect_endpoint_mock(self):
        response = self.client.get("/api/v1/inbox/connect")
        self.assertEqual(response.status_code, 200)
        self.assertIn("redirect_url", response.json())
        self.assertIn("mock_authorization_code", response.json()["redirect_url"])

    def test_connect_endpoint_configured(self):
        # Set Google credentials in env
        os.environ["GOOGLE_CLIENT_ID"] = "real_client_id"
        try:
            response = self.client.get("/api/v1/inbox/connect")
            self.assertEqual(response.status_code, 200)
            self.assertIn("accounts.google.com", response.json()["redirect_url"])
            self.assertIn("client_id=real_client_id", response.json()["redirect_url"])
        finally:
            del os.environ["GOOGLE_CLIENT_ID"]

    def test_callback_endpoint_stores_credentials(self):
        response = self.client.get("/api/v1/inbox/callback?code=mock_code")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "connected")
        
        # Verify stored credentials
        creds = self.repo.get_decrypted_gmail_credentials()
        self.assertIsNotNone(creds)
        self.assertEqual(creds["client_id"], "mock_client_id")
        self.assertTrue(creds["access_token"].startswith("mock_access_token"))

    def test_threads_endpoint_mock_fallback(self):
        # With no stored credentials, it returns mock threads
        response = self.client.get("/api/v1/inbox/threads")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        threads = data["threads"]
        self.assertEqual(len(threads), 4)
        self.assertEqual(threads[0]["id"], "thread_mock_1")
        self.assertEqual(threads[0]["status"], "rejected")

    def test_reply_endpoint_mock_thread(self):
        # Fetching draft for mock thread should succeed using fallback draft logic
        response = self.client.post("/api/v1/inbox/threads/thread_mock_2/reply")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["thread_id"], "thread_mock_2")
        self.assertEqual(data["to_email"], "hr@37signals.com")
        self.assertIn("schedule", data["body"].lower())

    def test_reply_endpoint_not_found(self):
        # Thread that does not exist should fail
        response = self.client.post("/api/v1/inbox/threads/nonexistent/reply")
        self.assertEqual(response.status_code, 404)

    def test_send_reply_endpoint_mock_thread(self):
        payload = {
            "subject": "Re: Interview scheduling: Coldcraft developer role",
            "body": "Hi, I'd love to schedule a call.",
            "to_email": "hr@37signals.com"
        }
        response = self.client.post("/api/v1/inbox/threads/thread_mock_2/send", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
        self.assertEqual(response.json()["status"], "sent")
        self.assertTrue(response.json()["message_id"].startswith("msg_mock_"))

    def test_send_reply_endpoint_not_found(self):
        payload = {
            "subject": "Re: None",
            "body": "Hi",
            "to_email": "hr@37signals.com"
        }
        response = self.client.post("/api/v1/inbox/threads/nonexistent/send", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_callback_stores_email_address(self):
        # Callback with mock code should connect and save email to DB
        response = self.client.get("/api/v1/inbox/callback?code=mock_code")
        self.assertEqual(response.status_code, 200)
        self.assertIn("birajdarushi@gmail.com", response.json()["message"])
        
        # Verify the saved credentials have the email column populated
        creds = self.repo.get_decrypted_gmail_credentials("birajdarushi@gmail.com")
        self.assertIsNotNone(creds)
        self.assertEqual(creds["email"], "birajdarushi@gmail.com")

    def test_list_threads_multi_account(self):
        # Save two credentials for different emails
        from cryptography.fernet import Fernet
        from coldcraft.config.secrets import encrypt_secret
        
        # Generate some credentials
        self.repo.save_gmail_credentials(
            email="account1@gmail.com",
            client_id_enc=encrypt_secret("client1"),
            client_secret_enc=encrypt_secret("secret1"),
            access_token_enc=encrypt_secret("mock_access_token_1"),
            refresh_token_enc=encrypt_secret("refresh1"),
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["scope1"]
        )
        self.repo.save_gmail_credentials(
            email="account2@gmail.com",
            client_id_enc=encrypt_secret("client2"),
            client_secret_enc=encrypt_secret("secret2"),
            access_token_enc=encrypt_secret("mock_access_token_2"),
            refresh_token_enc=encrypt_secret("refresh2"),
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["scope2"]
        )
        
        # Call list threads
        response = self.client.get("/api/v1/inbox/threads")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        threads = data["threads"]
        
        # Since we used mock access tokens, they both fetch from the mock data,
        # but because they are tagged with their respective connected_emails and deduped by ID,
        # we should get a list of unique threads (4 of them, but with account1@gmail.com or account2@gmail.com depending on which processed first).
        self.assertEqual(len(threads), 4)
        for t in threads:
            self.assertIn(t["connected_email"], ["account1@gmail.com", "account2@gmail.com"])

    def test_archive_thread_endpoint(self):
        response = self.client.post("/api/v1/inbox/threads/thread_mock_1/archive")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "archived")
        self.assertEqual(data["thread_id"], "thread_mock_1")

    def test_trash_thread_endpoint(self):
        response = self.client.post("/api/v1/inbox/threads/thread_mock_1/trash")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "trashed")
        self.assertEqual(data["thread_id"], "thread_mock_1")

    def test_parse_list_unsubscribe(self):
        from coldcraft.infrastructure.gmail_client import parse_list_unsubscribe
        m, u = parse_list_unsubscribe("<mailto:unsub@test.com?subject=unsub>, <https://test.com/unsub>")
        self.assertEqual(m, "mailto:unsub@test.com?subject=unsub")
        self.assertEqual(u, "https://test.com/unsub")
        
        m, u = parse_list_unsubscribe("<https://test.com/unsub>")
        self.assertIsNone(m)
        self.assertEqual(u, "https://test.com/unsub")
        
        m, u = parse_list_unsubscribe("<mailto:unsub@test.com>")
        self.assertEqual(m, "mailto:unsub@test.com")
        self.assertIsNone(u)

    def test_scan_unsubscribe_endpoint(self):
        response = self.client.post("/api/v1/inbox/unsubscribe/scan")
        self.assertEqual(response.status_code, 200)
        candidates = response.json()
        self.assertEqual(len(candidates), 4)
        self.assertEqual(candidates[0]["id"], "thread_unsub_mock_1")
        self.assertIn("newsletter@aitrends.com", [c["from_email"] for c in candidates])

    def test_unsubscribe_thread_endpoint(self):
        response = self.client.post("/api/v1/inbox/threads/thread_unsub_mock_1/unsubscribe")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "unsubscribed")
        self.assertIn("mock_success", data["methods"])

    def test_bulk_unsubscribe_endpoint(self):
        payload = {"thread_ids": ["thread_unsub_mock_1", "thread_unsub_mock_2"]}
        response = self.client.post("/api/v1/inbox/unsubscribe/bulk", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["thread_id"], "thread_unsub_mock_1")
        self.assertEqual(data["results"][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
