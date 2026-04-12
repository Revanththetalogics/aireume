"""
Queue API - REST endpoints for job queue management and monitoring

Provides endpoints for:
- Submitting analysis jobs
- Checking job status
- Retrieving results
- Queue statistics and monitoring
- Admin operations (retry, cancel, etc.)
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.models.db_models import User, Tenant
from app.backend.routes.auth import get_current_user
from app.backend.services.queue_manager import (
    get_queue_manager,
    AnalysisJob,
    AnalysisResult,
    AnalysisArtifact,
    JobMetrics,
)

router = APIRouter(prefix="/queue", tags=["Queue Management"])


# ============================================================================
# Job Submission
# ============================================================================

@router.post("/submit")
async def submit_analysis_job(
    resume_text: str,
    resume_filename: str,
    job_description: str,
    candidate_id: Optional[int] = None,
    priority: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a new resume analysis job to the queue.
    
    Priority levels:
    - 1-2: High priority (premium users, urgent)
    - 3-5: Normal priority (default)
    - 6-10: Low priority (batch jobs, background)
    """
    queue_manager = get_queue_manager()
    
    try:
        job_id = await queue_manager.enqueue_job(
            tenant_id=current_user.tenant_id,
            resume_text=resume_text,
            resume_filename=resume_filename,
            jd_text=job_description,
            candidate_id=candidate_id,
            user_id=current_user.id,
            priority=priority,
        )
        
        return {
            "job_id": str(job_id),
            "status": "queued",
            "message": "Analysis job submitted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


# ============================================================================
# Job Status and Results
# ============================================================================

@router.get("/status/{job_id}")
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current status of a job.
    
    Returns:
        - status: queued, processing, completed, failed, retrying
        - progress_percent: 0-100
        - estimated_completion: ISO timestamp (if available)
        - error_message: If failed
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        "job_id": str(job.id),
        "status": job.status,
        "progress_percent": job.progress_percent,
        "processing_stage": job.processing_stage,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
    }
    
    # Add timing estimates
    if job.status == 'queued':
        # Estimate based on queue position
        queue_position = db.query(func.count(AnalysisJob.id)).filter(
            AnalysisJob.tenant_id == current_user.tenant_id,
            AnalysisJob.status == 'queued',
            AnalysisJob.priority <= job.priority,
            AnalysisJob.queued_at < job.queued_at
        ).scalar()
        
        response["queue_position"] = queue_position
        response["estimated_wait_seconds"] = queue_position * 30  # Rough estimate
    
    # Add error details if failed
    if job.status in ['failed', 'retrying']:
        response["error_message"] = job.error_message
        response["error_type"] = job.error_type
        if job.status == 'retrying':
            response["next_retry_at"] = job.next_retry_at.isoformat() if job.next_retry_at else None
    
    # Add result reference if completed
    if job.status == 'completed' and job.result_id:
        response["result_id"] = str(job.result_id)
    
    return response


@router.get("/result/{job_id}")
async def get_job_result(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the analysis result for a completed job.
    
    Returns the full analysis data including:
    - fit_score, final_recommendation
    - strengths, weaknesses, matched_skills
    - parsed resume and JD
    - AI enhancement status
    """
    # Verify job belongs to user's tenant
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet. Current status: {job.status}"
        )
    
    # Get result
    result = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return {
        "job_id": str(job_id),
        "result_id": str(result.id),
        "candidate_id": result.candidate_id,
        "fit_score": result.fit_score,
        "final_recommendation": result.final_recommendation,
        "risk_level": result.risk_level,
        "analysis_quality": result.analysis_quality,
        "confidence_score": result.confidence_score,
        "processing_time_ms": result.processing_time_ms,
        "created_at": result.created_at.isoformat(),
        
        # Full analysis data
        "analysis": result.analysis_data,
        "parsed_resume": result.parsed_resume,
        "parsed_jd": result.parsed_jd,
        
        # AI enhancement
        "narrative_status": result.narrative_status,
        "narrative_data": result.narrative_data,
        "ai_enhanced": result.ai_enhanced,
        
        # Metadata
        "model_used": result.model_used,
        "analysis_version": result.analysis_version,
    }


# ============================================================================
# Queue Monitoring
# ============================================================================

@router.get("/stats")
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get queue statistics for the current tenant.
    
    Returns:
        - Total jobs by status
        - Average processing time
        - Success rate
        - Current queue depth
    """
    tenant_id = current_user.tenant_id
    
    # Count jobs by status
    status_counts = db.query(
        AnalysisJob.status,
        func.count(AnalysisJob.id).label('count')
    ).filter(
        AnalysisJob.tenant_id == tenant_id
    ).group_by(AnalysisJob.status).all()
    
    status_dict = {status: count for status, count in status_counts}
    
    # Get average processing time for completed jobs (last 100)
    avg_time = db.query(
        func.avg(JobMetrics.total_time_ms)
    ).join(
        AnalysisJob, JobMetrics.job_id == AnalysisJob.id
    ).filter(
        AnalysisJob.tenant_id == tenant_id,
        AnalysisJob.status == 'completed'
    ).scalar()
    
    # Calculate success rate
    total_finished = status_dict.get('completed', 0) + status_dict.get('failed', 0)
    success_rate = (status_dict.get('completed', 0) / total_finished * 100) if total_finished > 0 else 0
    
    # Current queue depth
    queue_depth = status_dict.get('queued', 0) + status_dict.get('retrying', 0)
    
    # Jobs in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_jobs = db.query(func.count(AnalysisJob.id)).filter(
        AnalysisJob.tenant_id == tenant_id,
        AnalysisJob.created_at >= yesterday
    ).scalar()
    
    return {
        "tenant_id": tenant_id,
        "status_counts": status_dict,
        "queue_depth": queue_depth,
        "avg_processing_time_ms": int(avg_time) if avg_time else None,
        "success_rate_percent": round(success_rate, 2),
        "jobs_last_24h": recent_jobs,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List jobs for the current tenant with pagination.
    """
    query = db.query(AnalysisJob).filter(
        AnalysisJob.tenant_id == current_user.tenant_id
    )
    
    if status:
        query = query.filter(AnalysisJob.status == status)
    
    total = query.count()
    
    jobs = query.order_by(
        AnalysisJob.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "job_id": str(job.id),
                "status": job.status,
                "priority": job.priority,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "retry_count": job.retry_count,
                "candidate_id": job.candidate_id,
                "result_id": str(job.result_id) if job.result_id else None,
            }
            for job in jobs
        ]
    }


# ============================================================================
# Admin Operations
# ============================================================================

@router.post("/retry/{job_id}")
async def retry_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually retry a failed job.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in ['failed', 'cancelled']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job with status: {job.status}"
        )
    
    # Reset job for retry
    job.status = 'queued'
    job.retry_count = 0
    job.queued_at = datetime.utcnow()
    job.started_at = None
    job.completed_at = None
    job.failed_at = None
    job.next_retry_at = None
    job.worker_id = None
    job.error_message = None
    job.error_type = None
    
    db.commit()
    
    return {
        "job_id": str(job_id),
        "status": "queued",
        "message": "Job requeued for retry"
    }


@router.delete("/cancel/{job_id}")
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a queued or processing job.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ['completed', 'failed']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    job.status = 'cancelled'
    job.completed_at = datetime.utcnow()
    db.commit()
    
    return {
        "job_id": str(job_id),
        "status": "cancelled",
        "message": "Job cancelled successfully"
    }


@router.get("/worker/stats")
async def get_worker_stats(
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about the queue worker.
    
    Requires admin privileges.
    """
    # TODO: Add admin check
    
    queue_manager = get_queue_manager()
    return queue_manager.get_stats()


@router.get("/metrics/performance")
async def get_performance_metrics(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get performance metrics over time.
    
    Returns:
        - Average processing time by day
        - Success rate trends
        - Queue depth over time
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Daily aggregates
    daily_stats = db.query(
        func.date(AnalysisJob.created_at).label('date'),
        func.count(AnalysisJob.id).label('total_jobs'),
        func.count(AnalysisJob.id).filter(AnalysisJob.status == 'completed').label('completed'),
        func.count(AnalysisJob.id).filter(AnalysisJob.status == 'failed').label('failed'),
        func.avg(JobMetrics.total_time_ms).label('avg_time_ms'),
    ).outerjoin(
        JobMetrics, AnalysisJob.id == JobMetrics.job_id
    ).filter(
        AnalysisJob.tenant_id == current_user.tenant_id,
        AnalysisJob.created_at >= since
    ).group_by(
        func.date(AnalysisJob.created_at)
    ).order_by(
        func.date(AnalysisJob.created_at)
    ).all()
    
    return {
        "period_days": days,
        "daily_metrics": [
            {
                "date": stat.date.isoformat(),
                "total_jobs": stat.total_jobs,
                "completed": stat.completed,
                "failed": stat.failed,
                "success_rate": (stat.completed / stat.total_jobs * 100) if stat.total_jobs > 0 else 0,
                "avg_processing_time_ms": int(stat.avg_time_ms) if stat.avg_time_ms else None,
            }
            for stat in daily_stats
        ]
    }
