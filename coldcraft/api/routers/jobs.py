from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...application.use_cases import ScrapeJobsUseCase
from ...domain.errors import ScraperError
from ...infrastructure.scraper import CareersPageScraper
from ..schemas import JobResponse, ScrapeRequest, ScrapeResponse


class JobDeleteRequest(BaseModel):
    ids: list[str]


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

    @router.get("", response_model=list[JobResponse])
    def list_jobs(
        company: str | None = Query(None, description="Filter by company name"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return campaigns_repo.list_jobs(company=company, limit=limit, offset=offset)

    @router.post("/delete")
    def delete_jobs(body: JobDeleteRequest):
        if not body.ids:
            raise HTTPException(status_code=422, detail="ids must not be empty")
        deleted = campaigns_repo.delete_jobs(body.ids)
        return {"deleted": deleted}

    @router.delete("/{job_id}")
    def delete_job(job_id: str):
        deleted = campaigns_repo.delete_jobs([job_id])
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"deleted": deleted}

    return router