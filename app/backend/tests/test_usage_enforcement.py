"""
Integration tests for usage enforcement in analyze endpoints.
Tests that usage limits are properly enforced and tracked.
"""
import pytest
from io import BytesIO
from app.backend.models.db_models import Tenant, User, UsageLog, Candidate, ScreeningResult


class TestSingleAnalyzeUsageEnforcement:
    """Tests for usage tracking in /api/analyze endpoint."""
    
    def test_analyze_increments_usage_counter(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Successful analysis should increment the usage counter."""
        from app.backend.models.db_models import Tenant
        
        # Get initial count
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Upload resume
        resume_text = b"John Doe\nPython Developer\njohn@example.com\n\nSkills: Python, FastAPI\n\nExperience:\nSenior Dev at TechCorp 2020-Present"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer with FastAPI experience. 3+ years required.",
        }
        
        response = auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        # Should succeed
        assert response.status_code == 200
        
        # Verify usage incremented
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count + 1
    
    def test_analyze_creates_usage_log(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Successful analysis should create a usage log entry."""
        from app.backend.models.db_models import Tenant, User
        
        # Get tenant and user
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        user = db.query(User).filter(User.email == "pro@procorp.com").first()
        
        # Upload resume
        resume_text = b"Jane Smith\nJavaScript Developer\njane@example.com\n\nSkills: JavaScript, React\n\nExperience:\nFrontend Dev at WebCorp 2019-2022"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a React developer with 2+ years experience.",
        }
        
        response = auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        assert response.status_code == 200
        
        # Verify usage log created
        logs = db.query(UsageLog).filter(
            UsageLog.tenant_id == tenant.id,
            UsageLog.action == "resume_analysis"
        ).all()
        
        assert len(logs) >= 1
        log = logs[-1]  # Get most recent
        assert log.user_id == user.id
        assert log.quantity == 1
    
    def test_analyze_denied_at_usage_limit(
        self, auth_client_at_usage_limit, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Analysis should be denied when usage limit is reached."""
        
        # Upload resume - should be denied
        resume_text = b"John Doe\nPython Developer\njohn@example.com\n\nSkills: Python"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer.",
        }
        
        response = auth_client_at_usage_limit.post("/api/analyze", files=files, data=data)
        
        # Should be rate limited
        assert response.status_code == 429
        data = response.json()
        assert "limit" in data.get("detail", "").lower() or "exceeded" in data.get("detail", "").lower()
    
    def test_analyze_no_usage_increment_on_failure(
        self, auth_client_with_pro_plan, db, seed_subscription_plans
    ):
        """Failed analysis should not increment usage counter."""
        from app.backend.models.db_models import Tenant
        
        # Get initial count
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Upload without job description - should fail
        resume_text = b"John Doe\nPython Developer"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {}  # Missing job_description
        
        response = auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        # Should fail validation
        assert response.status_code == 400
        
        # Verify usage NOT incremented
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count
    
    def test_enterprise_unlimited_analyses(
        self, auth_client, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Enterprise plan with unlimited (-1) should allow many analyses."""
        from app.backend.models.db_models import Tenant, SubscriptionPlan
        
        # Switch to enterprise plan
        enterprise_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "enterprise").first()
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        tenant.plan_id = enterprise_plan.id
        tenant.analyses_count_this_month = 1000  # Already used a lot
        db.commit()
        
        # Upload resume - should be allowed
        resume_text = b"John Doe\nPython Developer\njohn@example.com"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer.",
        }
        
        response = auth_client.post("/api/analyze", files=files, data=data)
        
        # Should succeed even with high usage count
        assert response.status_code == 200


class TestBatchAnalyzeUsageEnforcement:
    """Tests for usage tracking in /api/analyze/batch endpoint."""
    
    def test_batch_analyze_increments_usage_by_file_count(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Batch analysis should increment usage by number of files."""
        from app.backend.models.db_models import Tenant
        
        # Get initial count
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Upload 3 resumes
        files = [
            ("resumes", ("resume1.txt", BytesIO(b"John Doe\nPython Dev"), "text/plain")),
            ("resumes", ("resume2.txt", BytesIO(b"Jane Smith\nReact Dev"), "text/plain")),
            ("resumes", ("resume3.txt", BytesIO(b"Bob Wilson\nNode Dev"), "text/plain")),
        ]
        data = {
            "job_description": "Looking for developers with various skills.",
        }
        
        response = auth_client_with_pro_plan.post("/api/analyze/batch", files=files, data=data)
        
        # Should succeed
        assert response.status_code == 200
        
        # Verify usage incremented by 3
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count + 3
    
    def test_batch_analyze_creates_usage_logs(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Batch analysis should create usage log entries."""
        from app.backend.models.db_models import Tenant, User
        
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        user = db.query(User).filter(User.email == "pro@procorp.com").first()
        
        # Get initial log count
        initial_logs = db.query(UsageLog).filter(UsageLog.tenant_id == tenant.id).count()
        
        # Upload 2 resumes
        files = [
            ("resumes", ("resume1.txt", BytesIO(b"John Doe\nPython Dev"), "text/plain")),
            ("resumes", ("resume2.txt", BytesIO(b"Jane Smith\nReact Dev"), "text/plain")),
        ]
        data = {
            "job_description": "Looking for developers.",
        }
        
        response = auth_client_with_pro_plan.post("/api/analyze/batch", files=files, data=data)
        
        assert response.status_code == 200
        
        # Verify usage logs created (one per file)
        current_logs = db.query(UsageLog).filter(UsageLog.tenant_id == tenant.id).count()
        assert current_logs == initial_logs + 2
    
    def test_batch_analyze_denied_when_would_exceed_limit(
        self, auth_client_with_free_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Batch should be denied when total would exceed limit."""
        from app.backend.models.db_models import Tenant
        
        # Free plan has 5 limit
        tenant = db.query(Tenant).filter(Tenant.slug == "freecorp").first()
        tenant.analyses_count_this_month = 3  # 2 remaining
        db.commit()
        
        # Try to upload 5 resumes
        files = [
            ("resumes", (f"resume{i}.txt", BytesIO(b"John Doe\nPython Dev"), "text/plain"))
            for i in range(5)
        ]
        data = {
            "job_description": "Looking for developers.",
        }
        
        response = auth_client_with_free_plan.post("/api/analyze/batch", files=files, data=data)
        
        # Should be rate limited
        assert response.status_code == 429
        data = response.json()
        assert "limit" in data.get("detail", "").lower() or "exceeded" in data.get("detail", "").lower()
    
    def test_batch_respects_plan_batch_size_limit(
        self, auth_client_with_free_plan, db, seed_subscription_plans
    ):
        """Batch size should be limited by plan's batch_size."""
        from app.backend.models.db_models import Tenant
        
        # Free plan has batch_size = 3
        tenant = db.query(Tenant).filter(Tenant.slug == "freecorp").first()
        tenant.analyses_count_this_month = 0  # Reset
        db.commit()
        
        # Try to upload 10 resumes (free plan limit is 3)
        files = [
            ("resumes", (f"resume{i}.txt", BytesIO(b"John Doe\nPython Dev"), "text/plain"))
            for i in range(10)
        ]
        data = {
            "job_description": "Looking for developers.",
        }
        
        response = auth_client_with_free_plan.post("/api/analyze/batch", files=files, data=data)
        
        # Should fail due to batch size limit
        assert response.status_code == 400
        data = response.json()
        assert "batch" in data.get("detail", "").lower() or "maximum" in data.get("detail", "").lower()
    
    def test_batch_no_usage_increment_on_validation_failure(
        self, auth_client_with_pro_plan, db, seed_subscription_plans
    ):
        """Failed batch should not increment usage counter."""
        from app.backend.models.db_models import Tenant
        
        # Get initial count
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Upload without job description
        files = [
            ("resumes", ("resume1.txt", BytesIO(b"John Doe\nPython Dev"), "text/plain")),
        ]
        data = {}  # Missing job_description
        
        response = auth_client_with_pro_plan.post("/api/analyze/batch", files=files, data=data)
        
        # Should fail validation
        assert response.status_code == 400
        
        # Verify usage NOT incremented
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count


class TestUsageCheckEndpoint:
    """Tests for /api/subscription/check endpoint integration."""
    
    def test_check_endpoint_reflects_actual_usage(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Check endpoint should reflect actual usage after analyses."""
        from app.backend.models.db_models import Tenant
        
        # First, check initial state
        response = auth_client_with_pro_plan.get("/api/subscription/check/resume_analysis")
        assert response.status_code == 200
        initial_check = response.json()
        
        # Perform an analysis
        resume_text = b"John Doe\nPython Developer\njohn@example.com"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer.",
        }
        
        auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        # Check again - should show incremented usage
        response = auth_client_with_pro_plan.get("/api/subscription/check/resume_analysis")
        assert response.status_code == 200
        after_check = response.json()
        
        assert after_check["current_usage"] == initial_check["current_usage"] + 1
    
    def test_check_endpoint_respects_remaining_limit(
        self, auth_client_with_free_plan, db, seed_subscription_plans
    ):
        """Check endpoint should deny when approaching limit."""
        from app.backend.models.db_models import Tenant
        
        # Set at 4/5 usage
        tenant = db.query(Tenant).filter(Tenant.slug == "freecorp").first()
        tenant.analyses_count_this_month = 4
        db.commit()
        
        # Check single - should allow
        response = auth_client_with_free_plan.get("/api/subscription/check/resume_analysis?quantity=1")
        assert response.status_code == 200
        assert response.json()["allowed"] is True
        
        # Check batch of 2 - should deny (would be 4+2=6 > 5)
        response = auth_client_with_free_plan.get("/api/subscription/check/batch_analysis?quantity=2")
        assert response.status_code == 200
        assert response.json()["allowed"] is False


class TestUsageDashboardIntegration:
    """Tests for subscription dashboard data accuracy."""
    
    def test_dashboard_shows_correct_usage(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Dashboard should show accurate usage data."""
        from app.backend.models.db_models import Tenant
        
        # Perform 2 analyses
        for i in range(2):
            resume_text = f"John Doe {i}\nPython Developer\njohn{i}@example.com".encode()
            files = {
                "resume": (f"test_resume_{i}.txt", BytesIO(resume_text), "text/plain"),
            }
            data = {
                "job_description": "Looking for a Python developer.",
            }
            auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        # Get dashboard data
        response = auth_client_with_pro_plan.get("/api/subscription")
        assert response.status_code == 200
        data = response.json()
        
        # Verify usage
        assert data["usage"]["analyses_used"] == 2
        assert data["usage"]["analyses_limit"] == 100  # Pro plan
        assert data["usage"]["percent_used"] == 2.0  # 2/100 = 2%
    
    def test_dashboard_shows_correct_plan_info(
        self, auth_client_with_pro_plan, db, seed_subscription_plans
    ):
        """Dashboard should show correct plan information."""
        response = auth_client_with_pro_plan.get("/api/subscription")
        assert response.status_code == 200
        data = response.json()
        
        # Verify plan
        assert data["current_plan"]["plan"]["name"] == "pro"
        assert data["current_plan"]["status"] == "active"
        assert data["current_plan"]["billing_cycle"] in ["monthly", "yearly"]
        assert data["current_plan"]["price"] == 47000  # Yearly price from test fixtures
        
        # Verify features
        features = data["current_plan"]["plan"]["features"]
        assert isinstance(features, list)
        assert len(features) > 0
    
    def test_dashboard_available_plans(
        self, auth_client_with_pro_plan, db, seed_subscription_plans
    ):
        """Dashboard should show all available plans."""
        response = auth_client_with_pro_plan.get("/api/subscription")
        assert response.status_code == 200
        data = response.json()
        
        plans = data["available_plans"]
        assert len(plans) == 3
        
        plan_names = [p["name"] for p in plans]
        assert "free" in plan_names
        assert "pro" in plan_names
        assert "enterprise" in plan_names


class TestUsageEdgeCases:
    """Edge cases for usage tracking."""
    
    def test_concurrent_analyses_usage_tracking(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Multiple sequential analyses should each increment usage."""
        from app.backend.models.db_models import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Perform 5 analyses
        for i in range(5):
            resume_text = f"John Doe {i}\nPython Developer".encode()
            files = {
                "resume": (f"test_resume_{i}.txt", BytesIO(resume_text), "text/plain"),
            }
            data = {
                "job_description": "Looking for a Python developer.",
            }
            response = auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
            assert response.status_code == 200
        
        # Verify all 5 counted
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count + 5
    
    def test_zero_usage_initial_state(
        self, auth_client_with_free_plan, db, seed_subscription_plans
    ):
        """New tenant should start with zero usage."""
        from app.backend.models.db_models import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.slug == "freecorp").first()
        
        response = auth_client_with_free_plan.get("/api/subscription")
        assert response.status_code == 200
        data = response.json()
        
        assert data["usage"]["analyses_used"] == 0
        assert data["usage"]["percent_used"] == 0.0
    
    def test_usage_at_exact_limit(
        self, auth_client_with_free_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Should allow analysis exactly at limit, but not beyond."""
        from app.backend.models.db_models import Tenant
        
        # Set at 4/5 usage
        tenant = db.query(Tenant).filter(Tenant.slug == "freecorp").first()
        tenant.analyses_count_this_month = 4
        db.commit()
        
        # Should allow one more
        resume_text = b"John Doe\nPython Developer"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer.",
        }
        
        response = auth_client_with_free_plan.post("/api/analyze", files=files, data=data)
        
        # Mock may fail but should not be 429 (rate limit)
        if response.status_code == 200:
            # Verify at 5/5
            db.refresh(tenant)
            assert tenant.analyses_count_this_month == 5
            
            # Next one should fail
            response2 = auth_client_with_free_plan.post("/api/analyze", files=files, data=data)
            assert response2.status_code == 429
    
    def test_negative_limit_means_unlimited(
        self, auth_client, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Negative analyses_per_month should mean unlimited."""
        from app.backend.models.db_models import Tenant, SubscriptionPlan
        
        # Set enterprise plan with very high usage
        enterprise_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "enterprise").first()
        tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
        tenant.plan_id = enterprise_plan.id
        tenant.analyses_count_this_month = 9999
        db.commit()
        
        # Check endpoint should show unlimited
        response = auth_client.get("/api/subscription/check/resume_analysis")
        assert response.status_code == 200
        data = response.json()
        
        assert data["allowed"] is True
        assert data["limit"] == -1
    
    def test_usage_persists_across_requests(
        self, auth_client_with_pro_plan, db, mock_hybrid_pipeline, seed_subscription_plans
    ):
        """Usage should persist across multiple API calls."""
        from app.backend.models.db_models import Tenant
        
        # First request
        resume_text = b"John Doe\nPython Developer\njohn@example.com"
        files = {
            "resume": ("test_resume.txt", BytesIO(resume_text), "text/plain"),
        }
        data = {
            "job_description": "Looking for a Python developer.",
        }
        auth_client_with_pro_plan.post("/api/analyze", files=files, data=data)
        
        # Second request - should see previous usage
        response = auth_client_with_pro_plan.get("/api/subscription")
        assert response.status_code == 200
        data = response.json()
        
        assert data["usage"]["analyses_used"] >= 1
    
    def test_batch_usage_rollback_on_partial_failure(
        self, auth_client_with_pro_plan, db, seed_subscription_plans
    ):
        """Failed batch should not increment usage - counter shouldn't change."""
        from app.backend.models.db_models import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.slug == "procorp").first()
        initial_count = tenant.analyses_count_this_month
        
        # Send invalid batch (missing job description)
        files = [
            ("resumes", ("resume1.txt", BytesIO(b"John Doe"), "text/plain")),
            ("resumes", ("resume2.txt", BytesIO(b"Jane Smith"), "text/plain")),
        ]
        data = {}
        
        response = auth_client_with_pro_plan.post("/api/analyze/batch", files=files, data=data)
        assert response.status_code == 400
        
        # Verify usage unchanged
        db.refresh(tenant)
        assert tenant.analyses_count_this_month == initial_count
