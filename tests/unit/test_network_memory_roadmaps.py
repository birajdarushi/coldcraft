import os
import tempfile
import unittest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from coldcraft.db import session as db_session
from coldcraft.api.app import app
from coldcraft.infrastructure.persistence.repositories import SQLAlchemyCampaignRepository


def _fresh_db_env():
    os.environ["GTM_SMTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    db_file = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file

    db_session._engine = None
    db_session._SessionLocal = None
    db_session.init_db()
    return db_file


class NetworkMemoryRoadmapsTests(unittest.TestCase):
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

    def test_contacts_crud(self):
        # 1. Create a contact
        payload = {
            "name": "Jane Doe",
            "current_company": "Acme Corp",
            "role": "Recruiter",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "x_handle": "@janedoe",
            "relationship": "warm",
            "notes": "Met at career fair",
        }
        res = self.client.post("/api/v1/network/contacts", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["relationship"], "warm")
        self.assertIsNotNone(data["id"])
        contact_id = data["id"]

        # 2. List contacts
        res = self.client.get("/api/v1/network/contacts")
        self.assertEqual(res.status_code, 200)
        contacts = res.json()
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["id"], contact_id)

        # 3. Search contacts by company
        res = self.client.get("/api/v1/network/search?company=Acme")
        self.assertEqual(res.status_code, 200)
        searched = res.json()
        self.assertEqual(len(searched), 1)
        self.assertEqual(searched[0]["name"], "Jane Doe")

        # 4. Update contact
        update_payload = {"relationship": "hot", "notes": "Had a great call"}
        res = self.client.put(f"/api/v1/network/contacts/{contact_id}", json=update_payload)
        self.assertEqual(res.status_code, 200)
        updated = res.json()
        self.assertEqual(updated["relationship"], "hot")
        self.assertEqual(updated["notes"], "Had a great call")

        # 5. Delete contact
        res = self.client.delete(f"/api/v1/network/contacts/{contact_id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

        # 6. Verify deleted
        res = self.client.get("/api/v1/network/contacts")
        self.assertEqual(len(res.json()), 0)

    def test_memory_bank(self):
        # 1. Save memory entry
        payload = {
            "type": "resume_highlight",
            "key": "projects",
            "value": "Built a scalable microservices architecture",
            "source": "user_input",
        }
        res = self.client.put("/api/v1/memory", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["type"], "resume_highlight")
        self.assertEqual(data["key"], "projects")
        self.assertEqual(data["value"], "Built a scalable microservices architecture")

        # 2. List memory entries
        res = self.client.get("/api/v1/memory")
        self.assertEqual(res.status_code, 200)
        entries = res.json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["key"], "projects")

        # 3. GitHub summary integration (trigger sync/summary)
        res = self.client.post("/api/v1/memory/github-summary")
        self.assertEqual(res.status_code, 200)
        summary = res.json()
        self.assertEqual(summary["type"], "github_summary")
        self.assertEqual(summary["key"], "repos_summary")
        self.assertIsNotNone(summary["value"])

    def test_learning_roadmaps(self):
        # 1. Generate roadmap
        payload = {
            "title": "System Design",
            "syllabus": "Load balancers, caching, database replication",
        }
        res = self.client.post("/api/v1/roadmaps", json=payload)
        self.assertEqual(res.status_code, 200)
        roadmap = res.json()
        self.assertEqual(roadmap["title"], "System Design")
        self.assertIsNotNone(roadmap["id"])
        roadmap_id = roadmap["id"]
        self.assertTrue("nodes" in roadmap["nodes"])
        self.assertTrue("edges" in roadmap["nodes"])

        # 2. Get roadmap by ID
        res = self.client.get(f"/api/v1/roadmaps/{roadmap_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["title"], "System Design")

        # 3. Toggle node status completion
        first_node_id = roadmap["nodes"]["nodes"][0]["id"]
        res = self.client.put(
            f"/api/v1/roadmaps/{roadmap_id}/nodes/{first_node_id}",
            json={"completed": True},
        )
        self.assertEqual(res.status_code, 200)
        updated = res.json()
        node_status = next(
            n["status"] for n in updated["nodes"]["nodes"] if n["id"] == first_node_id
        )
        self.assertEqual(node_status, "completed")

    def test_job_status_and_stats(self):
        # Insert a job directly into the DB first
        from coldcraft.db.models import Job
        from datetime import datetime, timezone
        import uuid

        job_id = str(uuid.uuid4())
        with db_session.get_session() as db:
            db.add(
                Job(
                    id=job_id,
                    company="Google",
                    title="Software Engineer",
                    url="https://google.com/jobs",
                    status="scraped",
                    scraped_at=datetime.now(timezone.utc),
                )
            )
            db.commit()

        # 1. Fetch stats
        res = self.client.get("/api/v1/jobs/stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertEqual(stats["scraped"], 1)
        self.assertEqual(stats["applied"], 0)

        # 2. Update status to 'applied'
        res = self.client.put(f"/api/v1/jobs/{job_id}/status", json={"status": "applied"})
        self.assertEqual(res.status_code, 200)
        job = res.json()
        self.assertEqual(job["status"], "applied")
        self.assertIsNotNone(job["applied_at"])

        # 3. Verify stats updated
        res = self.client.get("/api/v1/jobs/stats")
        stats = res.json()
        self.assertEqual(stats["scraped"], 0)
        self.assertEqual(stats["applied"], 1)
