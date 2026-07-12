"""Background scheduler for periodic tasks (APScheduler)."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.backend.db.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def process_dunning_retries():
    """Process all due dunning retries."""
    from app.backend.services.billing.dunning_service import dunning_service

    db = SessionLocal()
    try:
        result = dunning_service.process_due_retries(db)
        logger.info("Dunning retry processing complete: %s", result)
    except Exception as exc:
        logger.error("Dunning retry processing failed: %s", exc, exc_info=True)
    finally:
        db.close()


def recover_stale_jobs():
    """Reset stale jobs (processing but lease expired) back to queued.

    A job is considered stale when its status is 'processing' but
    leased_until has already passed, meaning the worker died or timed out.
    Jobs that have reached max_retries are marked failed instead.
    """
    from app.backend.services.queue_manager import AnalysisJob

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stale_jobs = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.status == "processing",
                AnalysisJob.leased_until < now,
            )
            .all()
        )
        for job in stale_jobs:
            if job.retry_count < job.max_retries:
                job.status = "queued"
                job.leased_until = None
                job.retry_count += 1
                logger.warning(
                    "Recovered stale job %s (retry %d/%d)",
                    job.id,
                    job.retry_count,
                    job.max_retries,
                )
            else:
                job.status = "failed"
                job.error_message = "Job exceeded max retries after lease expiry."
                logger.error(
                    "Job %s exceeded max retries (%d), marking failed",
                    job.id,
                    job.max_retries,
                )
        db.commit()
        if stale_jobs:
            logger.info("Recovered %d stale jobs", len(stale_jobs))
    except Exception as exc:
        logger.error("Stale job recovery failed: %s", exc, exc_info=True)
        db.rollback()
    finally:
        db.close()


def expire_trials_job():
    """Mark expired self-serve trials as past_due."""
    from app.backend.services.trial_service import expire_trials
    db = SessionLocal()
    try:
        count = expire_trials(db)
        if count:
            logger.info("Expired %d trials", count)
    except Exception as exc:
        logger.error("Trial expiry job failed: %s", exc, exc_info=True)
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler with all periodic jobs."""
    if scheduler.running:
        return

    scheduler.add_job(
        process_dunning_retries,
        trigger=IntervalTrigger(hours=1),
        id="dunning_retries",
        replace_existing=True,
        misfire_grace_time=300,  # 5-minute grace window for misfires
    )

    scheduler.add_job(
        recover_stale_jobs,
        trigger=IntervalTrigger(minutes=5),
        id="stale_job_recovery",
        replace_existing=True,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        expire_trials_job,
        trigger=IntervalTrigger(hours=1),
        id="trial_expiry",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info(
        "Background scheduler started "
        "(dunning retries: every 1 h, stale job recovery: every 5 min, trial expiry: every 1 h)"
    )


def stop_scheduler():
    """Gracefully stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
