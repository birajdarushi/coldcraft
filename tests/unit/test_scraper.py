import unittest
from unittest.mock import patch

from coldcraft.application.use_cases import ScrapeJobsUseCase
from coldcraft.domain.models import NormalizedJob
from coldcraft.infrastructure.scraper.careers_page import (
    CareersPageScraper,
    stable_job_id,
    _collect_job_postings,
    _normalize_json_ld,
)


class StableJobIdTests(unittest.TestCase):
    def test_same_url_same_id(self):
        url = "https://boards.greenhouse.io/acme/jobs/123"
        self.assertEqual(stable_job_id(url), stable_job_id(url.upper()))

    def test_different_urls_different_ids(self):
        self.assertNotEqual(
            stable_job_id("https://example.com/jobs/1"),
            stable_job_id("https://example.com/jobs/2"),
        )


class JsonLdParserTests(unittest.TestCase):
    def test_collects_job_posting(self):
        payload = {
            "@graph": [
                {"@type": "Organization", "name": "Acme"},
                {
                    "@type": "JobPosting",
                    "title": "Backend Engineer",
                    "url": "https://careers.acme.com/jobs/backend",
                    "hiringOrganization": {"name": "Acme Corp"},
                },
            ]
        }
        postings = _collect_job_postings(payload)
        self.assertEqual(len(postings), 1)
        job = _normalize_json_ld(postings[0], "https://careers.acme.com", "careers_page")
        assert job is not None
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "Acme Corp")


class ScrapeJobsUseCaseTests(unittest.TestCase):
    def test_skips_duplicate_urls(self):
        class FakeScraper:
            def scrape(self, url, source="careers_page"):
                return [
                    NormalizedJob(
                        id=stable_job_id("https://example.com/jobs/1"),
                        title="Engineer",
                        company="Acme",
                        url="https://example.com/jobs/1",
                        location="Remote",
                        description="Build things",
                        source=source,
                    )
                ]

        class FakeRepo:
            def __init__(self):
                self.saved = set()

            def get_integrations(self):
                return {"scraper_sources": ["careers_page"]}

            def save_job(self, job):
                if job.url in self.saved:
                    return job.id, False
                self.saved.add(job.url)
                return job.id, True

        use_case = ScrapeJobsUseCase(scraper=FakeScraper(), campaigns=FakeRepo())
        first = use_case.execute("https://example.com/careers")
        second = use_case.execute("https://example.com/careers")
        self.assertEqual(first["scraped"], 1)
        self.assertEqual(first["skipped"], 0)
        self.assertEqual(second["scraped"], 0)
        self.assertEqual(second["skipped"], 1)


class GreenhouseScraperTests(unittest.TestCase):
    def test_parses_greenhouse_payload(self):
        payload = {
            "jobs": [
                {
                    "title": "Platform Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/99",
                    "location": {"name": "Remote"},
                    "content": "<p>Build platform</p>",
                }
            ]
        }
        scraper = CareersPageScraper()
        with patch(
            "coldcraft.infrastructure.scraper.careers_page._fetch_json",
            return_value=payload,
        ):
            jobs = scraper.scrape("https://boards.greenhouse.io/acme", source="careers_page")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Platform Engineer")
        self.assertEqual(jobs[0].url, "https://boards.greenhouse.io/acme/jobs/99")


if __name__ == "__main__":
    unittest.main()