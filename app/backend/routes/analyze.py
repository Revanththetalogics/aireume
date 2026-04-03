import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.models.db_models import ScreeningResult
from app.backend.models.schemas import AnalysisResponse
from app.backend.services.parser_service import parse_resume
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.analysis_service import analyze_resume

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Validate file type
    allowed_extensions = ('.pdf', '.docx', '.doc')
    if not resume.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Only {allowed_extensions} files are allowed"
        )

    # Validate JD input (either text or file required)
    if not job_description and not job_file:
        raise HTTPException(status_code=400, detail="Job description (text or file) is required")

    # Validate file size (10MB max)
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    # Extract JD from file if provided
    if job_file:
        try:
            jd_content = await job_file.read()
            if len(jd_content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Job description file too large (max 5MB)")
            jd_parsed = parse_resume(jd_content, job_file.filename)
            job_description = jd_parsed["raw_text"]
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to parse job description file: {str(e)}")

    # Step 1: Parse resume
    try:
        parsed_data = parse_resume(content, resume.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse resume: {str(e)}")

    # Step 2: Detect gaps and patterns
    work_exp = parsed_data.get("work_experience", [])
    gap_analysis = analyze_gaps(work_exp)

    # Step 3: Full analysis (calls LLM once)
    try:
        analysis_result = await analyze_resume(
            resume_text=parsed_data["raw_text"],
            job_description=job_description,
            parsed_data=parsed_data,
            gap_analysis=gap_analysis
        )
    except Exception as e:
        # Return fallback response if LLM fails completely
        analysis_result = {
            "fit_score": 50,
            "strengths": ["Analysis service temporarily unavailable"],
            "weaknesses": ["Unable to complete full analysis"],
            "employment_gaps": gap_analysis.get("employment_gaps", []),
            "education_analysis": "Analysis unavailable at this time.",
            "risk_signals": [{"type": "llm_error", "description": str(e)}],
            "final_recommendation": "Consider"
        }

    # Step 4: Save to database
    db_result = ScreeningResult(
        resume_text=parsed_data["raw_text"],
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data),
        analysis_result=json.dumps(analysis_result)
    )
    db.add(db_result)
    db.commit()

    return analysis_result


@router.get("/history")
def get_analysis_history(db: Session = Depends(get_db)):
    results = db.query(ScreeningResult).order_by(ScreeningResult.timestamp.desc()).limit(50).all()

    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "fit_score": json.loads(r.analysis_result).get("fit_score"),
            "final_recommendation": json.loads(r.analysis_result).get("final_recommendation")
        }
        for r in results
    ]
