from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...application.use_cases import ScrapeJobsUseCase
from ...domain.errors import ScraperError
from ...infrastructure.scraper import CareersPageScraper
from ..schemas import JobResponse, ScrapeRequest, ScrapeResponse


class JobDeleteRequest(BaseModel):
    ids: list[str]


from typing import Literal

class JobStatusUpdateRequest(BaseModel):
    status: Literal['scraped', 'cold_emailed', 'applied', 'rejected', 'in_process', 'offer']


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

    @router.get("/stats")
    def get_jobs_stats():
        return campaigns_repo.get_jobs_stats()

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

    @router.put("/{job_id}/status", response_model=JobResponse)
    def update_job_status(job_id: str, body: JobStatusUpdateRequest):
        job = campaigns_repo.update_job_status(job_id, body.status)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @router.delete("/{job_id}")
    def delete_job(job_id: str):
        deleted = campaigns_repo.delete_jobs([job_id])
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"deleted": deleted}

    @router.get("/{job_id}", response_model=JobResponse)
    def get_job(job_id: str):
        from ...db.session import get_session
        from ...db.models import Job
        with get_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobResponse(
                id=job.id,
                title=job.title,
                company=job.company,
                url=job.url,
                location=job.location,
                description=job.description,
                source=job.source,
                match_score=job.match_score,
                scraped_at=job.scraped_at.isoformat() if job.scraped_at else None,
                status=job.status,
                applied_at=job.applied_at.isoformat() if job.applied_at else None,
            )

    class JobStatusUpdate(BaseModel):
        status: str

    @router.put("/{job_id}/status", response_model=JobResponse)
    def update_job_status(job_id: str, body: JobStatusUpdate):
        from ...db.session import get_session
        from ...db.models import Job
        from datetime import datetime, timezone
        with get_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            job.status = body.status
            if body.status == "applied":
                job.applied_at = datetime.now(timezone.utc)
            db.commit()
            return JobResponse(
                id=job.id,
                title=job.title,
                company=job.company,
                url=job.url,
                location=job.location,
                description=job.description,
                source=job.source,
                match_score=job.match_score,
                scraped_at=job.scraped_at.isoformat() if job.scraped_at else None,
                status=job.status,
                applied_at=job.applied_at.isoformat() if job.applied_at else None,
            )

    return router