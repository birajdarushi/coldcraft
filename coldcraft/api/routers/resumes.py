from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ...latex import LatexError, compile_latex
from ... import resume_ai
from ...llm import LLMError


class ResumeCreate(BaseModel):
    name: str = "Untitled"
    latex_source: str = ""
    kind: str = "resume"  # 'resume' | 'cover_letter'


class ResumeUpdate(BaseModel):
    name: str | None = None
    latex_source: str | None = None


class CompileRequest(BaseModel):
    latex_source: str


class GenerateRequest(BaseModel):
    job_description: str
    name: str | None = None


class FixRequest(BaseModel):
    latex_source: str


def get_resumes_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/resumes", tags=["resumes"])

    @router.get("")
    def list_resumes(kind: str | None = None):
        return campaigns_repo.list_resumes(kind=kind)

    @router.post("")
    def create_resume(body: ResumeCreate):
        return campaigns_repo.create_resume(name=body.name, latex_source=body.latex_source, kind=body.kind)

    @router.get("/{resume_id}")
    def get_resume(resume_id: str):
        r = campaigns_repo.get_resume(resume_id)
        if not r:
            raise HTTPException(status_code=404, detail="Resume not found")
        return r

    @router.put("/{resume_id}")
    def update_resume(resume_id: str, body: ResumeUpdate):
        r = campaigns_repo.update_resume(resume_id, name=body.name, latex_source=body.latex_source)
        if not r:
            raise HTTPException(status_code=404, detail="Resume not found")
        return r

    @router.delete("/{resume_id}")
    def delete_resume(resume_id: str):
        if not campaigns_repo.delete_resume(resume_id):
            raise HTTPException(status_code=404, detail="Resume not found")
        return {"deleted": True}

    @router.post("/{resume_id}/compile")
    def compile_resume(resume_id: str):
        r = campaigns_repo.get_resume(resume_id)
        if not r:
            raise HTTPException(status_code=404, detail="Resume not found")
        try:
            pdf = compile_latex(r["latex_source"])
        except LatexError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "log": getattr(exc, "log", "")}) from exc
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{r["name"] or "resume"}.pdf"'})

    @router.post("/compile")
    def compile_adhoc(body: CompileRequest):
        """Compile arbitrary source without saving (live preview)."""
        try:
            pdf = compile_latex(body.latex_source)
        except LatexError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "log": getattr(exc, "log", "")}) from exc
        return Response(content=pdf, media_type="application/pdf")

    @router.post("/generate")
    def generate_resume(body: GenerateRequest):
        """Generate a tailored resume from a job description, grounded on the
        user's existing resumes, then auto-fix until it compiles. Saves the .tex."""
        if not body.job_description.strip():
            raise HTTPException(status_code=422, detail="job_description is required")
        context = [r["latex_source"] for r in campaigns_repo.list_resumes(kind="resume") if r.get("latex_source")]
        try:
            source = resume_ai.generate_latex(body.job_description, context)
        except LLMError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc

        compiled, error = True, None
        try:
            source, _pdf, _fixes = resume_ai.compile_with_autofix(source, attempts=2)
        except LatexError as exc:
            compiled = False
            error = str(exc)
            source = getattr(exc, "last_source", source)  # keep best attempt
        except LLMError as exc:
            compiled = False
            error = str(exc)

        name = body.name or "AI resume"
        resume = campaigns_repo.create_resume(name=name, latex_source=source, kind="resume")
        return {"resume": resume, "compiled": compiled, "error": error}

    @router.post("/fix")
    def fix_resume(body: FixRequest):
        """Compile; if it fails, ask Gemini to fix it. Returns corrected source."""
        try:
            compile_latex(body.latex_source)
            return {"latex_source": body.latex_source, "compiled": True, "changed": False}
        except LatexError as exc:
            log = getattr(exc, "log", "") or str(exc)
        try:
            fixed = resume_ai.fix_latex(body.latex_source, log)
        except LLMError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc

        compiled, error = True, None
        try:
            compile_latex(fixed)
        except LatexError as exc:
            compiled, error = False, getattr(exc, "log", "") or str(exc)
        return {"latex_source": fixed, "compiled": compiled, "changed": True, "error": error}

    return router
