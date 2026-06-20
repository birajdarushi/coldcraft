import unittest
from datetime import datetime, timedelta, timezone

from coldcraft.application.use_cases import GenerateIntelReportUseCase
from coldcraft.infrastructure.intel.sample_provider import INTEL_SECTION_KEYS, SampleIntelProvider


class FakeIntelRepo:
    def __init__(self) -> None:
        self._reports: dict[str, dict] = {}

    def get_intel_report(self, company: str):
        return self._reports.get(company)

    def save_intel_report(self, company: str, sections: dict, generated_at) -> None:
        self._reports[company] = {
            "company": company,
            "sections": sections,
            "generated_at": generated_at.isoformat(),
        }


class SampleIntelProviderTests(unittest.TestCase):
    def test_37signals_has_seven_sections(self):
        sections = SampleIntelProvider().generate("37signals")
        self.assertEqual(set(sections.keys()), set(INTEL_SECTION_KEYS))
        for key in INTEL_SECTION_KEYS:
            self.assertIn("content", sections[key])
            self.assertTrue(sections[key]["content"])

    def test_generic_company_has_caveat(self):
        sections = SampleIntelProvider().generate("acme-corp")
        self.assertIn("caveat", sections["sources_and_limitations"])


class GenerateIntelReportUseCaseTests(unittest.TestCase):
    def test_generates_and_caches(self):
        repo = FakeIntelRepo()
        use_case = GenerateIntelReportUseCase(research=SampleIntelProvider(), campaigns=repo)
        first = use_case.execute("37signals")
        self.assertFalse(first["cached"])
        self.assertEqual(len(first["sections"]), 7)

        second = use_case.execute("37signals")
        self.assertTrue(second["cached"])

    def test_force_refresh_bypasses_cache(self):
        repo = FakeIntelRepo()
        use_case = GenerateIntelReportUseCase(research=SampleIntelProvider(), campaigns=repo)
        use_case.execute("37signals")
        refreshed = use_case.execute("37signals", force_refresh=True)
        self.assertFalse(refreshed["cached"])

    def test_get_cached_missing_returns_none(self):
        repo = FakeIntelRepo()
        use_case = GenerateIntelReportUseCase(research=SampleIntelProvider(), campaigns=repo)
        self.assertIsNone(use_case.get_cached("missing-co"))

    def test_stale_cache_regenerates(self):
        repo = FakeIntelRepo()
        stale = datetime.now(timezone.utc) - timedelta(days=30)
        repo.save_intel_report("37signals", {"x": {}}, stale)
        use_case = GenerateIntelReportUseCase(research=SampleIntelProvider(), campaigns=repo)
        result = use_case.execute("37signals", cache_days=14)
        self.assertFalse(result["cached"])
        self.assertEqual(len(result["sections"]), 7)


if __name__ == "__main__":
    unittest.main()