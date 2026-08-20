"""
Verification tests for the Aug 2026 full-app bug audit.

Each test encodes the *correct* product behavior. A failure means the
corresponding audit finding is a real bug. These tests must not be "fixed"
by weakening assertions — only by fixing production code.
"""
from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.backend.main import app
from app.backend.models.db_models import (
    Candidate,
    HandoffShareLink,
    Invoice,
    PasswordResetToken,
    RecruiterInterviewSession,
    RequisitionCandidate,
    RoleTemplate,
    ScreeningResult,
    Tenant,
    User,
)
from app.backend.routes.auth import _hash_password
from app.backend.services.impersonation_service import create_impersonation_session
from app.backend.services.requisition_service import create_requisition
from app.backend.tests.test_helpers import (
    _verify_user_via_api,
    access_token_from,
    allow_ad_hoc_screening,
    assign_tenant_plan,
)

DOCX_HEADER = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00"
RESUME_CONTENT = b"John Doe\nSoftware Developer\n" + b"experience " * 40
LONG_JD = (
    "We are looking for an experienced software developer to join our growing team. "
    "The ideal candidate will have strong skills in Python programming, web development, "
    "and database design. Requirements include 3+ years of professional experience with "
    "Python frameworks such as FastAPI or Django, familiarity with SQL and NoSQL databases, "
    "experience with cloud platforms like AWS or Azure, strong understanding of software "
    "design patterns, excellent problem-solving skills, and the ability to work collaboratively "
    "in an agile environment. The role involves building scalable web applications."
)
SECRET_MARKER = "CROSS_TENANT_SECRET_SKILL_ZYX"


def _set_auth(client, token: str) -> None:
    client.headers.update({"Authorization": f"Bearer {token}"})


def _register_and_login(client, db, company: str, email: str, password: str = "TestPass123!") -> tuple[str, User]:
    resp = client.post(
        "/api/auth/register",
        json={"company_name": company, "email": email, "password": password, "full_name": "Tester"},
    )
    assert resp.status_code in (200, 201), resp.text
    _verify_user_via_api(email)
    assign_tenant_plan(db, "growth", "pro", email=email)
    allow_ad_hoc_screening(db, email=email)
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    user = db.query(User).filter(User.email == email).first()
    db.refresh(user)
    return access_token_from(login), user


def _screening_result(db, tenant_id: int, candidate_id: int, secret: str = SECRET_MARKER) -> ScreeningResult:
    result = ScreeningResult(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        resume_text="resume",
        jd_text="jd text for screening",
        parsed_data="{}",
        analysis_result=json.dumps({"fit_score": 91, "strengths": [secret], "final_recommendation": "advance"}),
        status="shortlisted",
        is_active=True,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


class TestBug001RequisitionScreeningResultIdor:
    def test_cannot_attach_foreign_tenant_screening_result(self, auth_client, db, seed_subscription_plans):
        admin_a = db.query(User).filter(User.email == "admin@testcorp.com").first()
        cand_a = Candidate(tenant_id=admin_a.tenant_id, name="Alice A", email="alice-a@testcorp.com")
        db.add(cand_a)
        db.commit()
        db.refresh(cand_a)

        token_b, user_b = _register_and_login(auth_client, db, "OtherCorpAudit", "admin@othercorp-audit.com")
        cand_b = Candidate(tenant_id=user_b.tenant_id, name="Bob B", email="bob-b@othercorp.com")
        db.add(cand_b)
        db.commit()
        db.refresh(cand_b)
        foreign_sr = _screening_result(db, user_b.tenant_id, cand_b.id)

        req = create_requisition(
            db,
            tenant_id=admin_a.tenant_id,
            created_by=admin_a.id,
            title="Backend Engineer",
            jd_text=LONG_JD,
        )
        db.commit()

        token_a = access_token_from(
            auth_client.post("/api/auth/login", json={"email": "admin@testcorp.com", "password": "TestPass123!"})
        )
        _set_auth(auth_client, token_a)
        resp = auth_client.post(
            f"/api/requisitions/{req.id}/candidates",
            json={
                "candidate_ids": [cand_a.id],
                "screening_result_ids": {str(cand_a.id): foreign_sr.id},
            },
        )
        db.expire_all()
        rc = (
            db.query(RequisitionCandidate)
            .filter(
                RequisitionCandidate.requisition_id == req.id,
                RequisitionCandidate.candidate_id == cand_a.id,
            )
            .first()
        )
        attached_foreign = rc is not None and rc.screening_result_id == foreign_sr.id
        assert not attached_foreign, (
            "BUG-001: stored another tenant's screening_result_id on requisition candidate"
        )
        if resp.status_code == 200:
            assert rc is None or rc.screening_result_id in (None, )
        else:
            assert resp.status_code in (400, 403, 404, 422)

    def test_handoff_does_not_include_foreign_screening_result(self, auth_client, db, seed_subscription_plans):
        admin_a = db.query(User).filter(User.email == "admin@testcorp.com").first()
        cand_a = Candidate(tenant_id=admin_a.tenant_id, name="Alice Handoff", email="alice-h@testcorp.com")
        db.add(cand_a)
        db.commit()
        db.refresh(cand_a)

        token_b, user_b = _register_and_login(auth_client, db, "HandoffLeakCorp", "admin@handoff-leak.com")
        cand_b = Candidate(tenant_id=user_b.tenant_id, name="Secret Bob", email="secret-bob@x.com")
        db.add(cand_b)
        db.commit()
        db.refresh(cand_b)
        foreign_sr = _screening_result(db, user_b.tenant_id, cand_b.id)

        req = create_requisition(
            db, tenant_id=admin_a.tenant_id, created_by=admin_a.id, title="Leak Role", jd_text=LONG_JD,
        )
        db.add(
            RequisitionCandidate(
                requisition_id=req.id,
                candidate_id=cand_a.id,
                screening_result_id=foreign_sr.id,
                pipeline_status="shortlisted",
                submission_status="submitted",
                added_by=admin_a.id,
            )
        )
        token = secrets.token_urlsafe(16)
        db.add(
            HandoffShareLink(
                token=token,
                tenant_id=admin_a.tenant_id,
                requisition_id=req.id,
                created_by=admin_a.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        db.commit()

        public = TestClient(app)
        resp = public.get(f"/api/public/handoff/{token}")
        assert resp.status_code == 200, resp.text
        assert SECRET_MARKER not in json.dumps(resp.json()), (
            "BUG-001: public handoff leaked another tenant's screening analysis"
        )


class TestBug002InterviewScreeningResultIdor:
    @patch(
        "app.backend.services.recruiter.orchestrator.load_kit_strategy_for_screening",
        return_value={"questions": [], "depth": "standard", "kit_question_count": 0},
    )
    @patch("app.backend.services.voice_call_scheduler.schedule_voice_call")
    def test_rejects_foreign_screening_result_id(self, _mock_sched, _mock_kit, auth_client, db, seed_subscription_plans):
        admin_a = db.query(User).filter(User.email == "admin@testcorp.com").first()
        cand_a = Candidate(
            tenant_id=admin_a.tenant_id,
            name="Interview Alice",
            email="int-alice@testcorp.com",
            phone="+14155550001",
        )
        db.add(cand_a)
        db.commit()
        db.refresh(cand_a)
        own_jd = RoleTemplate(tenant_id=admin_a.tenant_id, name="Own JD", jd_text=LONG_JD, created_by=admin_a.id)
        db.add(own_jd)
        db.commit()
        db.refresh(own_jd)
        own_sr = _screening_result(db, admin_a.tenant_id, cand_a.id, secret="OWN_OK")

        _token_b, user_b = _register_and_login(auth_client, db, "InterviewLeakCorp", "admin@interview-leak.com")
        cand_b = Candidate(tenant_id=user_b.tenant_id, name="Foreign Cand", email="fc@x.com", phone="+14155550002")
        db.add(cand_b)
        db.commit()
        db.refresh(cand_b)
        foreign_sr = _screening_result(db, user_b.tenant_id, cand_b.id)

        assign_tenant_plan(db, "enterprise", slug="testcorp")
        token_a = access_token_from(
            auth_client.post("/api/auth/login", json={"email": "admin@testcorp.com", "password": "TestPass123!"})
        )
        _set_auth(auth_client, token_a)
        payload = {
            "candidate_id": cand_a.id,
            "jd_id": own_jd.id,
            "trigger_type": "manual",
        }
        own_resp = auth_client.post("/api/recruiter/sessions", json={**payload, "screening_result_id": own_sr.id})
        assert own_resp.status_code in (200, 201), f"BUG-002 setup: own screening_result_id rejected ({own_resp.status_code} {own_resp.text})"
        own_session = db.get(RecruiterInterviewSession, own_resp.json()["id"])
        own_session.status = "completed"
        db.commit()

        resp = auth_client.post(
            "/api/recruiter/sessions",
            json={**payload, "screening_result_id": foreign_sr.id},
        )
        db.expire_all()
        stored = (
            db.query(RecruiterInterviewSession)
            .filter(RecruiterInterviewSession.screening_result_id == foreign_sr.id)
            .first()
        )
        assert stored is None and resp.status_code in (400, 403, 404, 422), (
            f"BUG-002: accepted foreign screening_result_id (status={resp.status_code} body={resp.text} stored={stored is not None})"
        )


class TestBug003ImpersonationNotBoundToAdmin:
    def test_foreign_user_cannot_use_impersonation_token(self, auth_client, db, seed_subscription_plans):
        target = db.query(User).filter(User.email == "admin@testcorp.com").first()
        token_b, attacker = _register_and_login(auth_client, db, "AttackerCorp", "attacker@impersonate.com")
        raw = create_impersonation_session(db, admin_user_id=target.id, target_user_id=target.id)

        _set_auth(auth_client, token_b)
        resp = auth_client.get("/api/auth/me", headers={"X-Impersonation-Token": raw})
        assert resp.status_code in (401, 403), (
            f"BUG-003: non-admin JWT used impersonation token (status={resp.status_code} body={resp.text})"
        )
        if resp.status_code == 200:
            assert resp.json().get("user", {}).get("email") != target.email


class TestBug004HiringManagerCandidateIdor:
    def test_hm_cannot_read_unassigned_candidate(self, auth_client, db, seed_subscription_plans):
        admin = db.query(User).filter(User.email == "admin@testcorp.com").first()
        assigned = Candidate(tenant_id=admin.tenant_id, name="Assigned", email="assigned-hm@testcorp.com")
        other = Candidate(tenant_id=admin.tenant_id, name="Other Secret", email="other-hm@testcorp.com")
        hm = User(
            tenant_id=admin.tenant_id,
            email="hm-audit@testcorp.com",
            hashed_password=_hash_password("TestPass123!"),
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add_all([assigned, other, hm])
        db.commit()
        db.refresh(assigned)
        db.refresh(other)
        db.refresh(hm)

        req = create_requisition(
            db, tenant_id=admin.tenant_id, created_by=admin.id, title="HM Opening", jd_text=LONG_JD,
        )
        req.primary_hiring_manager_id = hm.id
        db.add(RequisitionCandidate(requisition_id=req.id, candidate_id=assigned.id, added_by=admin.id))
        db.commit()

        login = auth_client.post("/api/auth/login", json={"email": hm.email, "password": "TestPass123!"})
        assert login.status_code == 200, login.text
        _set_auth(auth_client, access_token_from(login))
        resp = auth_client.get(f"/api/candidates/{other.id}")
        assert resp.status_code in (403, 404), (
            f"BUG-004: hiring manager read unassigned candidate (status={resp.status_code})"
        )


class TestBug005StreamChargesBeforeParse:
    def test_parse_failure_does_not_increment_usage(self, auth_client, db, seed_subscription_plans):
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        initial = tenant.analyses_count_this_month or 0

        files = {
            "resume": ("resume.docx", BytesIO(DOCX_HEADER + RESUME_CONTENT),
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        }
        with patch(
            "app.backend.routes.analyze._parse_resume_with_doc_conversion",
            new=AsyncMock(side_effect=ValueError("unreadable scanned pdf")),
        ):
            resp = auth_client.post(
                "/api/analyze/stream",
                files=files,
                data={"job_description": LONG_JD},
            )
        db.expire_all()
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        assert tenant.analyses_count_this_month == initial, (
            f"BUG-005: parse failure charged usage ({initial} -> {tenant.analyses_count_this_month}); "
            f"http={resp.status_code}"
        )


class TestBug006Bug013BatchChargesFailures:
    def test_parse_failures_are_not_billed_as_successes(self, auth_client, db, seed_subscription_plans):
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        initial = tenant.analyses_count_this_month or 0

        async def fake_process(*_args, **_kwargs):
            return {
                "fit_score": 0,
                "pipeline_errors": ["unreadable"],
                "analysis_quality": "low",
            }

        files = [
            ("resumes", (f"r{i}.docx", BytesIO(DOCX_HEADER + RESUME_CONTENT),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
            for i in range(2)
        ]
        with patch("app.backend.routes.analyze._process_single_resume", new=fake_process):
            resp = auth_client.post(
                "/api/analyze/batch",
                files=files,
                data={"job_description": LONG_JD},
            )
        db.expire_all()
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        charged = (tenant.analyses_count_this_month or 0) - initial
        body = resp.json() if resp.content else {}
        results = body.get("results") or body.get("items") or []
        failed = body.get("failed") or body.get("failed_items") or []
        problems = []
        if charged != 0:
            problems.append(f"BUG-006: charged {charged} for parse-failed batch files")
        if results and not failed:
            problems.append(f"BUG-013: parse failures returned as successes (results={results!r} failed={failed!r})")
        assert not problems, "; ".join(problems)


class TestBug007RazorpayWebhookIdempotency:
    def test_duplicate_razorpay_charge_does_not_create_two_invoices(self, db):
        tenant = Tenant(
            name="Razorpay Dup",
            slug=f"rzp-dup-{uuid.uuid4().hex[:8]}",
            subscription_status="past_due",
            stripe_subscription_id="sub_rzp_dup_1",
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        data = {
            "subscription": {"id": "sub_rzp_dup_1", "current_start": now_ts - 1000, "current_end": now_ts},
            "amount": 9900,
        }
        from app.backend.services.billing.webhook_processor import process_webhook_event

        first = process_webhook_event(
            db, provider="razorpay", event_type="subscription.charged",
            data=data, raw_payload=json.dumps(data), event_id=None,
        )
        second = process_webhook_event(
            db, provider="razorpay", event_type="subscription.charged",
            data=data, raw_payload=json.dumps(data), event_id=None,
        )
        invoices = db.query(Invoice).filter(Invoice.tenant_id == tenant.id).count()
        assert invoices <= 1, f"BUG-007: Razorpay replay created {invoices} invoices"
        assert second.get("reason") == "duplicate" or not second.get("processed"), (
            f"BUG-007: second Razorpay event without event_id was processed ({first}, {second})"
        )


class TestBug010DualQuotaCounters:
    def test_subscription_and_check_endpoint_agree_on_usage(self, auth_client, db, seed_subscription_plans):
        from app.backend.services.billing.quota import check_quota

        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        tenant.analyses_count_this_month = 7
        db.commit()

        dash = auth_client.get("/api/subscription")
        assert dash.status_code == 200, dash.text
        dash_used = dash.json()["usage"]["analyses_used"]
        gate_used = check_quota(tenant.id, db)["used"]
        assert dash_used == gate_used, (
            f"BUG-010: dashboard analyses_used={dash_used} check_quota used={gate_used}"
        )


class TestBug011PasswordResetKeepsRefresh:
    def test_refresh_token_invalid_after_password_reset(self, auth_client, db, seed_subscription_plans):
        login = auth_client.post(
            "/api/auth/login", json={"email": "admin@testcorp.com", "password": "TestPass123!"}
        )
        assert login.status_code == 200
        refresh = login.cookies.get("refresh_token")
        assert refresh

        auth_client.post("/api/auth/forgot-password", json={"email": "admin@testcorp.com"})
        db.expire_all()
        user = db.query(User).filter(User.email == "admin@testcorp.com").first()
        token_row = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        assert token_row is not None
        reset = auth_client.post(
            "/api/auth/reset-password",
            json={"token": token_row.token, "new_password": "NewPass1234!"},
        )
        assert reset.status_code == 200, reset.text

        naked = TestClient(app)
        resp = naked.post("/api/auth/refresh", cookies={"refresh_token": refresh})
        assert resp.status_code == 401, (
            f"BUG-011: old refresh token still valid after password reset (status={resp.status_code})"
        )


class TestBug012SkillOverridesNoneJd:
    def test_apply_skill_overrides_with_none_jd_does_not_crash(self):
        from app.backend.routes.analyze_helpers import _apply_skill_overrides

        try:
            result = _apply_skill_overrides(None, {"required_skills": ["python"]})
        except AttributeError as exc:
            raise AssertionError(f"BUG-012: _apply_skill_overrides crashed on None JD ({exc})") from exc
        assert isinstance(result, dict)


class TestBug017GdprExportAuthorization:
    def test_viewer_cannot_gdpr_export_candidate(self, auth_client, db, seed_subscription_plans):
        admin = db.query(User).filter(User.email == "admin@testcorp.com").first()
        cand = Candidate(tenant_id=admin.tenant_id, name="PII Person", email="pii@testcorp.com", phone="555")
        viewer = User(
            tenant_id=admin.tenant_id,
            email="viewer-audit@testcorp.com",
            hashed_password=_hash_password("TestPass123!"),
            role="viewer",
            is_active=True,
            email_verified=True,
        )
        db.add_all([cand, viewer])
        db.commit()
        db.refresh(cand)

        login = auth_client.post(
            "/api/auth/login", json={"email": "viewer-audit@testcorp.com", "password": "TestPass123!"}
        )
        assert login.status_code == 200, login.text
        _set_auth(auth_client, access_token_from(login))
        try:
            resp = auth_client.get(f"/api/candidates/{cand.id}/gdpr-export")
        except AttributeError as exc:
            raise AssertionError(f"BUG-017: viewer reached GDPR export (crashed: {exc})") from exc
        assert resp.status_code in (401, 403), (
            f"BUG-017: viewer GDPR-exported candidate PII (status={resp.status_code})"
        )


class TestBug018ChunkZeroRequired:
    def test_first_non_zero_chunk_is_accepted(self, auth_client, db, seed_subscription_plans):
        upload_id = str(uuid.uuid4())
        chunk = BytesIO(b"x" * 1024)
        resp = auth_client.post(
            "/api/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 1,
                "total_chunks": 3,
                "filename": "big.pdf",
            },
            files={"chunk": ("chunk.bin", chunk, "application/octet-stream")},
        )
        assert resp.status_code != 404, (
            "BUG-018: non-zero first chunk rejected with Upload not found (chunk-0 race)"
        )
        assert resp.status_code in (200, 201)


class TestBug020HandoffForwardedFor:
    def test_spoofed_forwarded_for_does_not_bypass_rate_limit(self, auth_client, db, seed_subscription_plans):
        from app.backend.services import shared_cache

        shared_cache._memory.clear()
        admin = db.query(User).filter(User.email == "admin@testcorp.com").first()
        req = create_requisition(
            db, tenant_id=admin.tenant_id, created_by=admin.id, title="RL Role", jd_text=LONG_JD,
        )
        token = secrets.token_urlsafe(16)
        db.add(
            HandoffShareLink(
                token=token,
                tenant_id=admin.tenant_id,
                requisition_id=req.id,
                created_by=admin.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        db.commit()

        public = TestClient(app)
        last = None
        for i in range(61):
            last = public.get(
                f"/api/public/handoff/{token}",
                headers={"X-Forwarded-For": f"203.0.113.{i % 250}"},
            )
        assert last is not None
        assert last.status_code == 429, (
            f"BUG-020: X-Forwarded-For spoof bypassed public handoff rate limit (status={last.status_code})"
        )


class TestBug021PasscodeQueryString:
    def test_passcode_in_query_string_is_rejected(self, auth_client, db, seed_subscription_plans):
        import hashlib
        from app.backend.services import shared_cache

        shared_cache._memory.clear()
        admin = db.query(User).filter(User.email == "admin@testcorp.com").first()
        req = create_requisition(
            db, tenant_id=admin.tenant_id, created_by=admin.id, title="PC Role", jd_text=LONG_JD,
        )
        token = secrets.token_urlsafe(16)
        db.add(
            HandoffShareLink(
                token=token,
                tenant_id=admin.tenant_id,
                requisition_id=req.id,
                created_by=admin.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                passcode_hash=hashlib.sha256(b"s3cret").hexdigest(),
            )
        )
        db.commit()
        public = TestClient(app)
        via_query = public.get(f"/api/public/handoff/{token}?passcode=s3cret")
        assert via_query.status_code in (401, 403), (
            f"BUG-021: passcode accepted from query string (status={via_query.status_code})"
        )
        via_header = public.get(
            f"/api/public/handoff/{token}",
            headers={"X-Handoff-Passcode": "s3cret"},
        )
        assert via_header.status_code == 200, via_header.text
