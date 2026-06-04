import unittest

from coldcraft.application.use_cases import CreateDraftUseCase
from coldcraft.domain.models import CampaignRequest, DraftResult
from coldcraft.domain.errors import DoNotContactError


class DummyDrafter:
    def generate_hooks(self, company_intel, sender_profile, count=3):
        return [{"text": "Hook", "specificity": 5, "surprise_factor": 4, "relevance": 5}]

    def draft(self, hook, company_intel, sender_profile, recipient_name):
        return DraftResult(
            campaign_id="",
            subject="Solid subject",
            body_html="<p>Team shipped X recently. I built Y for similar constraints. Would a short call be useful?</p>",
            body_text="Team shipped X recently. I built Y for similar constraints. Would a short call be useful?",
            word_count=18,
            personalization_signals=["x", "y"],
            hook_candidates=[],
            selected_hook=hook,
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
