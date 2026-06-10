from fastapi import APIRouter, HTTPException, Query

from ...application.use_cases import ScrapeJobsUseCase
from ...domain.errors import ScraperError
from ...infrastructure.scraper import CareersPageScraper
from ..schemas import ScrapeRequest, ScrapeResponse


def get_jobs_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/jobs", tags=["jobs"])
    scraper = CareersPageScraper()
    scrape_use_case = ScrapeJobsUseCase(scraper=scraper, campaigns=campaigns_repo)

    @router.post("/scrape", response_model=ScrapeResponse)
    def scrape_jobs(body: ScrapeRequest):
        try:
            return scrape_use_case.execute(url=body.url, source=body.source)
        except ScraperError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("", response_model=list)
    def list_jobs(
        company: str | None = Query(None, description="Filter by company name"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return campaigns_repo.list_jobs(company=company, limit=limit, offset=offset)

    return router