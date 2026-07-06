"""
Queue Manager - Scalable job queue system for resume analysis

This module provides a robust, scalable queue system with:
- Priority-based job scheduling
- Automatic retry with exponential backoff
- Worker health monitoring
- Deduplication
- Graceful shutdown
- Metrics collection
"""

import asyncio
import hashlib
import json
import logging
import os
import signal
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.backend.db.database import SessionLocal, Base
from app.backend.models.db_models import Tenant, Candidate

logger = logging.getLogger(__name__)


# ============================================================================
# Job Models (SQLAlchemy models for queue tables)
# ============================================================================
# The ORM table definitions now live in app.backend.models.db_models so that
# all schema is colocated and discoverable by Alembic/tooling. They are
# re-exported here for backward compatibility with existing imports.

from app.backend.models.db_models import (  # noqa: F401
    AnalysisJob,
    AnalysisResult,
    DeadLetterJob,
    AnalysisArtifact,
    JobMetrics,
)


# ============================================================================
# Queue Manager
# ============================================================================

class QueueManager:
    """
    Manages the analysis job queue with priority scheduling, retries, and monitoring.
    """
    
    def __init__(self):
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.worker_version = "2.0.0"
        self.is_running = False
        self.current_job_id: Optional[uuid.UUID] = None
        
        # Configuration
        self.max_concurrent_jobs = int(os.getenv("QUEUE_MAX_CONCURRENT", "10"))
        self.poll_interval_seconds = int(os.getenv("QUEUE_POLL_INTERVAL", "2"))
        self.heartbeat_interval_seconds = int(os.getenv("QUEUE_HEARTBEAT_INTERVAL", "30"))
        self.stale_job_timeout_seconds = int(os.getenv("QUEUE_STALE_TIMEOUT", "600"))  # 10 min
        
        # Retry configuration
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min
        
        # Metrics
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.jobs_retried = 0
        
        logger.info(f"QueueManager initialized: worker_id={self.worker_id}, max_concurrent={self.max_concurrent_jobs}")
    
    def compute_hash(self, *inputs: str) -> str:
        """Compute SHA-256 hash of inputs for deduplication."""
        combined = "|".join(str(i) for i in inputs)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def enqueue_job(
        self,
        tenant_id: int,
        resume_text: str,
        resume_filename: str,
        jd_text: str,
        candidate_id: Optional[int] = None,
        user_id: Optional[int] = None,
        priority: int = 5,
        job_config: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Add a new analysis job to the queue.
        
        Returns:
            job_id: UUID of the created job
        
        Raises:
            IntegrityError: If duplicate job already exists
        """
        db = SessionLocal()
        try:
            # Compute hashes for deduplication
            resume_hash = self.compute_hash(resume_text)
            jd_hash = self.compute_hash(jd_text)
            input_hash = self.compute_hash(resume_hash, jd_hash, str(tenant_id))
            
            # Check if identical job already exists and is not failed
            existing = db.query(AnalysisJob).filter(
                AnalysisJob.input_hash == input_hash,
                AnalysisJob.status.in_(['queued', 'processing', 'completed', 'retrying'])
            ).first()
            
            if existing:
                if existing.status == 'completed':
                    logger.info(f"Duplicate job found (completed): {existing.id}")
                    return existing.id
                else:
                    logger.info(f"Duplicate job found (in progress): {existing.id}, status={existing.status}")
                    return existing.id
            
            # Create artifact
            artifact = AnalysisArtifact(
                tenant_id=tenant_id,
                resume_filename=resume_filename,
                resume_size_bytes=len(resume_text.encode()),
                resume_hash=resume_hash,
                resume_text=resume_text,
                resume_text_length=len(resume_text),
                jd_hash=jd_hash,
                jd_text=jd_text,
                jd_size_bytes=len(jd_text.encode()),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),  # Keep for 30 days
            )
            db.add(artifact)
            db.flush()
            
            # Create job
            job = AnalysisJob(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                user_id=user_id,
                resume_hash=resume_hash,
                jd_hash=jd_hash,
                input_hash=input_hash,
                priority=priority,
                artifact_id=artifact.id,
                job_config=job_config,
            )
            db.add(job)
            db.commit()
            
            logger.info(f"Job enqueued: {job.id}, priority={priority}, tenant={tenant_id}")
            return job.id
            
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Duplicate job detected: {e}")
            # Return existing job ID
            existing = db.query(AnalysisJob).filter(AnalysisJob.input_hash == input_hash).first()
            return existing.id if existing else None
        finally:
            db.close()
    
    async def get_next_job(self, db: Session) -> Optional[AnalysisJob]:
        """
        Get the next job to process based on priority and queue time.
        
        Uses SELECT FOR UPDATE SKIP LOCKED for concurrent worker safety.
        """
        # Query for next available job
        job = db.execute(
            select(AnalysisJob)
            .where(
                and_(
                    AnalysisJob.status.in_(['queued', 'retrying']),
                    or_(
                        AnalysisJob.next_retry_at.is_(None),
                        AnalysisJob.next_retry_at <= datetime.now(timezone.utc)
                    )
                )
            )
            .order_by(AnalysisJob.priority.asc(), AnalysisJob.queued_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        
        if job:
            # Claim the job and issue a 10-minute lease
            job.status = 'processing'
            job.worker_id = self.worker_id
            job.started_at = datetime.now(timezone.utc)
            job.worker_heartbeat = datetime.now(timezone.utc)
            job.leased_until = datetime.now(timezone.utc) + timedelta(minutes=10)
            db.commit()
            
            logger.info(f"Claimed job: {job.id}, priority={job.priority}, retry_count={job.retry_count}")
        
        return job
    
    async def update_heartbeat(self, job_id: uuid.UUID, db: Session):
        """Update worker heartbeat to show job is still being processed."""
        db.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .values(worker_heartbeat=datetime.now(timezone.utc))
        )
        db.commit()
    
    async def process_job(self, job: AnalysisJob, db: Session) -> bool:
        """
        Process a single analysis job.
        
        Returns:
            True if successful, False if failed
        """
        start_time = time.time()
        stage_timings = {}
        
        try:
            # Load artifact
            artifact = db.query(AnalysisArtifact).filter(AnalysisArtifact.id == job.artifact_id).first()
            if not artifact:
                raise ValueError(f"Artifact not found: {job.artifact_id}")
            
            logger.info(f"Processing job {job.id}: {artifact.resume_filename}")
            
            # Update progress
            job.processing_stage = 'parsing'
            job.progress_percent = 10
            db.commit()
            
            # Run analysis - TODO: Integrate with existing analyze routes
            # For now, this is a placeholder that will be replaced with actual integration
            parse_start = time.time()
            
            # Import here to avoid circular dependency
            from app.backend.routes.analyze import _process_single_resume
            
            result = await _process_single_resume(
                content=artifact.resume_text.encode('utf-8'),
                filename=artifact.resume_filename,
                job_description=artifact.jd_text,
                tenant_id=job.tenant_id,
                user_id=job.user_id,
                db=db,
            )
            
            stage_timings['total_analysis'] = int((time.time() - parse_start) * 1000)
            
            # Validate result has required fields
            required_fields = ['fit_score', 'final_recommendation', 'strengths', 'weaknesses', 'matched_skills']
            missing = [f for f in required_fields if f not in result or result[f] is None]
            
            if missing:
                raise ValueError(f"Analysis result missing required fields: {missing}")
            
            # Update progress
            job.processing_stage = 'saving'
            job.progress_percent = 90
            db.commit()
            
            # Save result
            analysis_result = AnalysisResult(
                job_id=job.id,
                tenant_id=job.tenant_id,
                candidate_id=job.candidate_id,
                fit_score=result['fit_score'],
                final_recommendation=result['final_recommendation'],
                risk_level=result.get('risk_level'),
                analysis_data=result,
                parsed_resume=result.get('parsed_resume', {}),
                parsed_jd=result.get('parsed_jd', {}),
                analysis_quality=result.get('analysis_quality', 'medium'),
                confidence_score=result.get('confidence_score'),
                model_used=result.get('model_used'),
                processing_time_ms=int((time.time() - start_time) * 1000),
                artifact_id=artifact.id,
            )
            db.add(analysis_result)
            db.flush()
            
            # Update job status
            job.status = 'completed'
            job.completed_at = datetime.now(timezone.utc)
            job.result_id = analysis_result.id
            job.progress_percent = 100
            db.commit()
            
            # Save metrics
            total_time_ms = int((time.time() - start_time) * 1000)
            queue_wait_ms = int((job.started_at - job.queued_at).total_seconds() * 1000)
            
            metrics = JobMetrics(
                job_id=job.id,
                tenant_id=job.tenant_id,
                queue_wait_time_ms=queue_wait_ms,
                total_time_ms=total_time_ms,
                stage_timings=stage_timings,
                worker_id=self.worker_id,
                worker_version=self.worker_version,
                retry_attempts=job.retry_count,
            )
            db.add(metrics)
            db.commit()
            
            self.jobs_processed += 1
            logger.info(f"Job completed: {job.id}, time={total_time_ms}ms, score={result['fit_score']}")
            return True
            
        except Exception as e:
            logger.error(f"Job failed: {job.id}, error={str(e)}", exc_info=True)
            
            # Determine if we should retry
            should_retry = job.retry_count < job.max_retries
            
            if should_retry:
                # Calculate next retry time with exponential backoff
                retry_delay = self.retry_delays[min(job.retry_count, len(self.retry_delays) - 1)]
                next_retry = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
                
                job.status = 'retrying'
                job.retry_count += 1
                job.next_retry_at = next_retry
                job.error_message = str(e)
                job.error_type = type(e).__name__
                
                self.jobs_retried += 1
                logger.info(f"Job will retry: {job.id}, attempt={job.retry_count}/{job.max_retries}, next_retry={next_retry}")
            else:
                # Max retries exceeded
                job.status = 'failed'
                job.failed_at = datetime.now(timezone.utc)
                job.error_message = str(e)
                job.error_type = type(e).__name__
                
                self.jobs_failed += 1
                logger.error(f"Job permanently failed: {job.id}, retries exhausted")
            
            db.commit()
            
            # Save failure metrics
            total_time_ms = int((time.time() - start_time) * 1000)
            metrics = JobMetrics(
                job_id=job.id,
                tenant_id=job.tenant_id,
                total_time_ms=total_time_ms,
                error_stage=job.processing_stage,
                retry_attempts=job.retry_count,
                worker_id=self.worker_id,
                worker_version=self.worker_version,
            )
            db.add(metrics)
            db.commit()
            
            return False
    
    async def recover_stale_jobs(self, db: Session):
        """
        Recover jobs that have been processing for too long (worker died).
        """
        stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=self.stale_job_timeout_seconds)
        
        stale_jobs = db.query(AnalysisJob).filter(
            AnalysisJob.status == 'processing',
            AnalysisJob.worker_heartbeat < stale_threshold
        ).all()
        
        for job in stale_jobs:
            logger.warning(f"Recovering stale job: {job.id}, worker={job.worker_id}, last_heartbeat={job.worker_heartbeat}")
            
            if job.retry_count < job.max_retries:
                job.status = 'retrying'
                job.retry_count += 1
                job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=60)
                job.worker_id = None
            else:
                job.status = 'failed'
                job.failed_at = datetime.now(timezone.utc)
                job.error_message = "Worker timeout - job abandoned"
                job.error_type = "WorkerTimeout"
        
        if stale_jobs:
            db.commit()
            logger.info(f"Recovered {len(stale_jobs)} stale jobs")

    # ─── Dead Letter Queue Operations ───────────────────────────────────────────

    async def move_to_dead_letter(
        self,
        db: Session,
        job: AnalysisJob,
        failure_reason: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_trace: Optional[str] = None,
    ) -> DeadLetterJob:
        """
        Move a failed job to the dead letter queue after all retries exhausted.
        """
        dlq_job = DeadLetterJob(
            original_job_id=job.id,
            tenant_id=job.tenant_id,
            candidate_id=job.candidate_id,
            user_id=job.user_id,
            job_type=job.job_type,
            resume_hash=job.resume_hash,
            jd_hash=job.jd_hash,
            input_hash=job.input_hash,
            job_config=job.job_config,
            failure_reason=failure_reason,
            failure_type=error_type,
            last_error_message=error_message,
            last_error_trace=error_trace,
            retry_count=job.retry_count,
            original_created_at=job.created_at,
            status='pending',
        )
        
        db.add(dlq_job)
        
        # Mark original job as dead-lettered
        job.status = 'dead_letter'
        job.failed_at = datetime.now(timezone.utc)
        
        db.commit()
        logger.warning(f"Moved job {job.id} to dead letter queue: {failure_reason}")
        
        return dlq_job

    async def get_dead_letter_jobs(
        self,
        db: Session,
        tenant_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[DeadLetterJob]:
        """Get dead letter jobs with optional filters."""
        query = db.query(DeadLetterJob)
        
        if tenant_id:
            query = query.filter(DeadLetterJob.tenant_id == tenant_id)
        if status:
            query = query.filter(DeadLetterJob.status == status)
        
        return query.order_by(DeadLetterJob.failed_at.desc()).limit(limit).all()

    async def retry_dead_letter_job(self, db: Session, dlq_job_id: uuid.UUID) -> Optional[AnalysisJob]:
        """Retry a dead letter job by creating a new analysis job."""
        dlq_job = db.query(DeadLetterJob).filter(DeadLetterJob.id == dlq_job_id).first()
        
        if not dlq_job:
            return None
        
        if dlq_job.status != 'pending':
            raise ValueError(f"Cannot retry dead letter job with status: {dlq_job.status}")
        
        # Create new job from dead letter job
        new_job = AnalysisJob(
            tenant_id=dlq_job.tenant_id,
            candidate_id=dlq_job.candidate_id,
            user_id=dlq_job.user_id,
            job_type=dlq_job.job_type,
            resume_hash=dlq_job.resume_hash,
            jd_hash=dlq_job.jd_hash,
            input_hash=dlq_job.input_hash,
            job_config=dlq_job.job_config,
            priority=5,
            status='queued',
        )
        
        db.add(new_job)
        
        # Update dead letter job status
        dlq_job.status = 'reprocessed'
        dlq_job.reprocessed_at = datetime.now(timezone.utc)
        dlq_job.reprocessed_job_id = new_job.id
        
        db.commit()
        logger.info(f"Retried dead letter job {dlq_job_id} as new job {new_job.id}")
        
        return new_job

    async def worker_loop(self):
        """Main worker loop - processes jobs from the queue."""
        logger.info(f"Worker loop started: {self.worker_id}")
        self.is_running = True
        
        last_heartbeat = time.time()
        last_recovery = time.time()
        
        while self.is_running:
            db = SessionLocal()
            try:
                # Periodic stale job recovery (every 5 minutes)
                if time.time() - last_recovery > 300:
                    await self.recover_stale_jobs(db)
                    last_recovery = time.time()
                
                # Get next job
                job = await self.get_next_job(db)
                
                if job:
                    self.current_job_id = job.id
                    
                    # Process with periodic heartbeats
                    success = await self.process_job(job, db)
                    
                    self.current_job_id = None
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(self.poll_interval_seconds)
                
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error
            finally:
                db.close()
        
        logger.info(f"Worker loop stopped: {self.worker_id}")
    
    def start(self):
        """Start the queue worker."""
        asyncio.create_task(self.worker_loop())
    
    def stop(self):
        """Stop the queue worker gracefully."""
        logger.info(f"Stopping worker: {self.worker_id}")
        self.is_running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "current_job_id": str(self.current_job_id) if self.current_job_id else None,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "jobs_retried": self.jobs_retried,
        }


# ============================================================================
# Global queue manager instance
# ============================================================================

_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """Get or create the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager


async def start_queue_worker():
    """Start the background queue worker."""
    manager = get_queue_manager()
    manager.start()
    logger.info("Queue worker started")


async def stop_queue_worker():
    """Stop the background queue worker."""
    manager = get_queue_manager()
    manager.stop()
    logger.info("Queue worker stopped")
