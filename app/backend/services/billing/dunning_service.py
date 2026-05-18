"""Dunning service — manages failed payment retry and escalation logic.

When a payment fails and a tenant enters ``past_due`` status, this service
creates / updates a :class:`DunningRecord` and schedules automatic retries
according to the platform-wide dunning configuration stored in
``platform_configs`` under the key ``billing.dunning``.

Typical call flow::

    # 1. Payment failure webhook → webhook_processor sets past_due,
    #    then calls initiate_dunning()
    dunning_service.initiate_dunning(db, tenant_id, failure_reason="...")

    # 2. Periodic cron / scheduler calls:
    dunning_service.process_due_retries(db)

    # 3. Payment success webhook → webhook_processor calls:
    dunning_service.resolve_dunning(db, tenant_id)
"""
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import DunningRecord, PlatformConfig, Tenant
from app.backend.services.webhook_service import dispatch_event_background

log = logging.getLogger(__name__)

# Fallback defaults if platform config is missing
_DEFAULT_DUNNING_CONFIG = {
    "retry_schedule_days": [1, 3, 7, 14],
    "max_retries": 4,
    "suspend_after_max_retries": True,
    "notify_on_each_retry": True,
}


class DunningService:
    """Stateless service — all methods receive a ``db`` session explicitly."""

    # ── Configuration helpers ─────────────────────────────────────────────

    @staticmethod
    def _get_dunning_config(db: Session) -> dict:
        """Load dunning config from platform_configs, falling back to defaults."""
        row = (
            db.query(PlatformConfig)
            .filter(PlatformConfig.config_key == "billing.dunning")
            .first()
        )
        if row and row.config_value:
            try:
                return json.loads(row.config_value)
            except (json.JSONDecodeError, TypeError):
                log.warning("Invalid JSON in billing.dunning config, using defaults")
        return dict(_DEFAULT_DUNNING_CONFIG)

    # ── Core API ──────────────────────────────────────────────────────────

    def initiate_dunning(
        self,
        db: Session,
        tenant_id: int,
        failure_reason: Optional[str] = None,
    ) -> DunningRecord:
        """Create or update a dunning record when a payment fails.

        If an *active* dunning record already exists for the tenant, increment
        ``retry_count`` and recalculate ``next_retry_at``.  Otherwise create a
        fresh record.

        Returns the dunning record (caller is responsible for ``db.commit()``).
        """
        config = self._get_dunning_config(db)
        max_retries = config.get("max_retries", 4)
        schedule = config.get("retry_schedule_days", [1, 3, 7, 14])

        # Look for an existing active dunning record
        record = (
            db.query(DunningRecord)
            .filter(
                DunningRecord.tenant_id == tenant_id,
                DunningRecord.status == "active",
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if record is not None:
            # Existing active record — increment retry count
            record.retry_count += 1
            record.last_retry_at = now
            if failure_reason:
                record.failure_reason = failure_reason

            if record.retry_count >= max_retries:
                # Exhausted — will be handled by caller or process_due_retries
                record.status = "exhausted"
                record.next_retry_at = None
                log.warning(
                    "Dunning exhausted for tenant %s after %d retries",
                    tenant_id, record.retry_count,
                )
            else:
                record.next_retry_at = self._calculate_next_retry(
                    now, record.retry_count, schedule
                )
        else:
            # No active dunning — create a new record
            record = DunningRecord(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                status="active",
                retry_count=0,
                max_retries=max_retries,
                next_retry_at=self._calculate_next_retry(now, 0, schedule),
                last_retry_at=None,
                failure_reason=failure_reason,
                resolved_at=None,
            )
            db.add(record)
            log.info(
                "Dunning initiated for tenant %s, first retry at %s",
                tenant_id, record.next_retry_at,
            )

        # Flush so the caller can read auto-generated fields
        db.flush()

        # Fire notification if configured
        if config.get("notify_on_each_retry", True):
            self._fire_dunning_event(tenant_id, record)

        return record

    def process_due_retries(self, db: Session) -> List[Dict[str, Any]]:
        """Process all dunning records that are due for a retry.

        Designed to be called periodically (cron / Celery beat / scheduler).

        For each due record:
        1. Attempt a payment retry via the active provider.
        2. On success: resolve dunning, set tenant to ``active``.
        3. On failure: increment ``retry_count``, schedule next retry.
        4. If max retries reached: mark ``exhausted``, suspend tenant.

        Returns a list of result dicts for observability.
        """
        config = self._get_dunning_config(db)
        max_retries = config.get("max_retries", 4)
        schedule = config.get("retry_schedule_days", [1, 3, 7, 14])
        suspend_after = config.get("suspend_after_max_retries", True)

        now = datetime.now(timezone.utc)

        # Find all active records whose next_retry_at has passed
        due_records = (
            db.query(DunningRecord)
            .filter(
                DunningRecord.status == "active",
                DunningRecord.next_retry_at <= now,
            )
            .all()
        )

        results = []

        for record in due_records:
            tenant = (
                db.query(Tenant)
                .filter(Tenant.id == record.tenant_id)
                .first()
            )
            if tenant is None:
                log.warning(
                    "Dunning record %s references missing tenant %s, skipping",
                    record.id, record.tenant_id,
                )
                continue

            # Attempt payment retry via provider
            retry_ok, retry_detail = self._attempt_payment_retry(db, tenant)

            if retry_ok:
                # Payment succeeded — resolve dunning
                record.status = "resolved"
                record.resolved_at = now
                record.last_retry_at = now
                tenant.subscription_status = "active"
                tenant.subscription_updated_at = now
                log.info(
                    "Dunning resolved for tenant %s on retry %d",
                    tenant.id, record.retry_count + 1,
                )
                self._fire_subscription_changed(tenant.id, "active")
                results.append({
                    "tenant_id": tenant.id,
                    "action": "resolved",
                    "retry_count": record.retry_count + 1,
                })
            else:
                # Payment failed — increment retry count
                record.retry_count += 1
                record.last_retry_at = now
                record.failure_reason = retry_detail

                if record.retry_count >= max_retries:
                    record.status = "exhausted"
                    record.next_retry_at = None

                    if suspend_after:
                        tenant.subscription_status = "suspended"
                        tenant.suspended_at = now
                        tenant.suspended_reason = (
                            f"Payment failed after {max_retries} dunning retries"
                        )
                        tenant.subscription_updated_at = now
                        log.warning(
                            "Tenant %s suspended after %d dunning retries",
                            tenant.id, max_retries,
                        )
                        self._fire_subscription_changed(tenant.id, "suspended")

                    results.append({
                        "tenant_id": tenant.id,
                        "action": "exhausted",
                        "retry_count": record.retry_count,
                        "suspended": suspend_after,
                    })
                else:
                    record.next_retry_at = self._calculate_next_retry(
                        now, record.retry_count, schedule
                    )
                    log.info(
                        "Dunning retry %d failed for tenant %s, next retry at %s",
                        record.retry_count, tenant.id, record.next_retry_at,
                    )
                    results.append({
                        "tenant_id": tenant.id,
                        "action": "retry_failed",
                        "retry_count": record.retry_count,
                        "next_retry_at": record.next_retry_at.isoformat() if record.next_retry_at else None,
                    })

            # Fire notification if configured
            if config.get("notify_on_each_retry", True):
                self._fire_dunning_event(tenant.id, record)

            db.flush()

        if due_records:
            db.commit()

        return results

    def resolve_dunning(self, db: Session, tenant_id: int) -> Optional[DunningRecord]:
        """Resolve any active dunning record for a tenant (e.g. payment succeeded).

        Returns the resolved record, or ``None`` if no active dunning exists.
        The caller is responsible for ``db.commit()``.
        """
        record = (
            db.query(DunningRecord)
            .filter(
                DunningRecord.tenant_id == tenant_id,
                DunningRecord.status == "active",
            )
            .first()
        )
        if record is None:
            return None

        now = datetime.now(timezone.utc)
        record.status = "resolved"
        record.resolved_at = now
        db.flush()

        log.info(
            "Dunning resolved for tenant %s (was retry %d)",
            tenant_id, record.retry_count,
        )
        return record

    def get_dunning_status(self, db: Session, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Return current dunning state for a tenant, or None if no dunning exists."""
        record = (
            db.query(DunningRecord)
            .filter(DunningRecord.tenant_id == tenant_id)
            .order_by(DunningRecord.created_at.desc())
            .first()
        )
        if record is None:
            return None

        return {
            "id": record.id,
            "tenant_id": record.tenant_id,
            "status": record.status,
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
            "next_retry_at": record.next_retry_at.isoformat() if record.next_retry_at else None,
            "last_retry_at": record.last_retry_at.isoformat() if record.last_retry_at else None,
            "failure_reason": record.failure_reason,
            "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    def list_active_dunning(self, db: Session) -> List[Dict[str, Any]]:
        """List all tenants currently in active dunning (for admin dashboard)."""
        records = (
            db.query(DunningRecord)
            .filter(DunningRecord.status == "active")
            .order_by(DunningRecord.next_retry_at)
            .all()
        )
        results = []
        for r in records:
            tenant = db.query(Tenant).filter(Tenant.id == r.tenant_id).first()
            results.append({
                "id": r.id,
                "tenant_id": r.tenant_id,
                "tenant_name": tenant.name if tenant else "Unknown",
                "tenant_slug": tenant.slug if tenant else None,
                "status": r.status,
                "retry_count": r.retry_count,
                "max_retries": r.max_retries,
                "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
                "last_retry_at": r.last_retry_at.isoformat() if r.last_retry_at else None,
                "failure_reason": r.failure_reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return results

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _calculate_next_retry(
        from_time: datetime, retry_index: int, schedule: List[int]
    ) -> datetime:
        """Calculate the next retry timestamp based on the schedule.

        ``retry_index`` is 0-based.  If the index exceeds the schedule length,
        the last schedule entry is used (or 14 days as a safe fallback).
        """
        if retry_index < len(schedule):
            days = schedule[retry_index]
        else:
            days = schedule[-1] if schedule else 14
        return from_time + timedelta(days=days)

    @staticmethod
    def _attempt_payment_retry(db: Session, tenant: Tenant) -> tuple:
        """Attempt a payment retry through the active provider.

        Returns ``(success: bool, detail: str)``.
        """
        try:
            from app.backend.services.billing.factory import get_payment_provider
            provider = get_payment_provider(db)

            if not tenant.stripe_subscription_id:
                return False, "No subscription ID on tenant"

            result = provider.get_subscription_status(
                tenant.id, tenant.stripe_subscription_id
            )
            provider_status = result.get("status", "")

            # If the provider reports the subscription is now active,
            # the payment has gone through on their end
            if provider_status in ("active", "trialing"):
                return True, "Subscription active at provider"

            # Try to trigger a retry — most providers auto-retry on their
            # schedule, but we check status first.  For Stripe, invoice
            # retries are automatic.  For Razorpay/Manual we mark as
            # needing manual intervention.
            return False, f"Subscription still {provider_status} at provider"

        except Exception as exc:
            log.exception("Payment retry attempt failed for tenant %s: %s", tenant.id, exc)
            return False, f"Retry error: {exc}"

    @staticmethod
    def _fire_dunning_event(tenant_id: int, record: DunningRecord):
        """Fire a dunning notification webhook event."""
        try:
            dispatch_event_background(
                db_factory=None,
                tenant_id=tenant_id,
                event="dunning.retry",
                payload={
                    "dunning_id": record.id,
                    "status": record.status,
                    "retry_count": record.retry_count,
                    "max_retries": record.max_retries,
                    "next_retry_at": record.next_retry_at.isoformat() if record.next_retry_at else None,
                    "failure_reason": record.failure_reason,
                },
            )
        except Exception:
            log.exception("Failed to fire dunning webhook for tenant %s", tenant_id)

    @staticmethod
    def _fire_subscription_changed(tenant_id: int, new_status: str):
        """Fire subscription.changed webhook event."""
        try:
            dispatch_event_background(
                db_factory=None,
                tenant_id=tenant_id,
                event="subscription.changed",
                payload={
                    "subscription_status": new_status,
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            log.exception("Failed to fire subscription.changed webhook for tenant %s", tenant_id)


# Module-level singleton for convenience
dunning_service = DunningService()
