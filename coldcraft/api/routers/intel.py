from fastapi import APIRouter, HTTPException

from ...application.use_cases import GenerateIntelReportUseCase
from ...infrastructure.intel import GeminiIntelProvider
from ..schemas import IntelReportRequest, IntelReportResponse


def get_intel_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/intel", tags=["intel"])
    provider = GeminiIntelProvider()  # falls back to sample data when no Gemini key
    use_case = GenerateIntelReportUseCase(research=provider, campaigns=campaigns_repo)

    @router.post("/reports", response_model=IntelReportResponse)
    def create_intel_report(body: IntelReportRequest):
        try:
            return use_case.execute(body.company, force_refresh=body.force_refresh)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/reports/{company}", response_model=IntelReportResponse)
    def get_intel_report(company: str):
        report = use_case.get_cached(company)
        if not report:
            raise HTTPException(status_code=404, detail="Intel report not found")
        return report

    return router