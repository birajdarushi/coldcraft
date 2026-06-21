import unittest

from coldcraft.application.use_cases import CreateDraftUseCase
from coldcraft.domain.models import CampaignRequest, DraftResult
from coldcraft.domain.errors import DoNotContactError


class DummyDrafter:
    def generate_hooks(self, company_intel, sender_profile, count=3):
        return [{"text": "Hook", "specificity": 5, "surprise_factor": 4, "relevance": 5}]

    def draft(self, hook, company_intel, sender_profile, recipient_name):
        return self.draft_oneshot(company_intel, sender_profile, recipient_name)

    def draft_oneshot(self, company_intel, sender_profile, recipient_name):
        return DraftResult(
            campaign_id="",
            subject="Solid subject",
            body_html="<p>Team shipped X recently. I built Y for similar constraints. Would a short call be useful?</p>",
            body_text="Team shipped X recently. I built Y for similar constraints. Would a short call be useful?",
            word_count=18,
            personalization_signals=["x", "y"],
            hook_candidates=[],
            selected_hook={"text": "Hook", "signal_used": None},
        )

    def revise(self, draft, violations):
        return draft


class DummyValidator:
    def check_self_review(self, draft):
        return []


class DummyQAGateway:
    def validate_email(self, payload):
        return {"status": "PASS", "violations": []}


class DummyCampaignRepo:
    def is_do_not_contact(self, email):
        return True

    def in_ats_pipeline(self, email, job_id):
        return False

    def sent_today_count(self):
        return 0

    def sent_to_company_30d(self, company):
        return 0

    def get_match_score(self, job_id):
        return 80

    def already_sent(self, email, job_id):
        return False

    def create_draft_campaign(self, draft, request):
        return "cid"

    def get_user_config(self):
        return None

    def save_user_config(self, smtp_host, smtp_port, smtp_user, smtp_pass_enc, from_email, from_name, tracking_domain=None):
        pass

    def get_sender_profile(self):
        return None

    def save_sender_profile(self, name, email, skills, proof_points, tone=None):
        pass

    def get_policies(self):
        return None

    def save_policies(self, daily_send_limit=None, max_company_emails_30d=None, subject_max_chars=None, followup_days=None):
        pass

    def get_features(self):
        return {"tracking_enabled": True, "auto_followups": True}

    def save_features(self, tracking_enabled=None, auto_followups=None):
        pass

    def get_integrations(self):
        return {"apify_token": None, "scraper_sources": []}

    def save_integrations(self, apify_token_enc=None, scraper_sources=None):
        pass

    def get_job_by_url(self, url):
        return None

    def save_job(self, job):
        return job.id, True

    def list_jobs(self, company=None, limit=100, offset=0):
        return []

    def get_intel_report(self, company):
        return None

    def save_intel_report(self, company, sections, generated_at):
        pass

    def get_gmail_credentials(self, email=None):
        return None

    def save_gmail_credentials(self, email=None, client_id_enc=None, client_secret_enc=None, access_token_enc=None, refresh_token_enc=None, token_uri=None, scopes=None):
        pass

    def get_decrypted_gmail_credentials(self, email=None):
        return None

    def get_all_decrypted_gmail_credentials(self):
        return []



class CreateDraftUseCaseTests(unittest.TestCase):
    def test_blocks_do_not_contact(self):
        use_case = CreateDraftUseCase(
            drafter=DummyDrafter(),
            validator=DummyValidator(),
            qa_gateway=DummyQAGateway(),
            campaigns=DummyCampaignRepo(),
        )
        request = CampaignRequest(
            job_id="job1",
            recipient_email="x@example.com",
            recipient_name="X",
            company_intel={
                "product_description": "prod",
                "recent_signal": {"type": "launch", "description": "x", "date": "2026-01-01"},
                "recipient_role": "CTO",
                "recipient_public_work": "post",
                "company_name": "Acme",
            },
            sender_profile={"name": "A", "email": "a@b.com", "skills": ["python"], "proof_points": [{"k": "v"}]},
        )
        with self.assertRaises(DoNotContactError):
            use_case.execute(request)


if __name__ == "__main__":
    unittest.main()
