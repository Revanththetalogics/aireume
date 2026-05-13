"""
Phase 5 Tests: Enterprise Security & Compliance

Tests for:
1. PII redaction
2. Compliance audit logging
3. Integration hub
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from services.enterprise_security import PIIRedactor, ComplianceAuditLogger, IntegrationHub


class TestPIIRedactor:
    """Test PII redaction."""

    def test_redact_email(self):
        """Test email redaction."""
        redactor = PIIRedactor()
        text = "Contact me at john.doe@example.com for more info."
        
        result = redactor.redact(text, redaction_level="full")
        
        assert "john.doe@example.com" not in result["redacted_text"]
        assert "[EMAIL REDACTED]" in result["redacted_text"]
        assert result["total_redactions"] >= 1

    def test_redact_phone(self):
        """Test phone number redaction."""
        redactor = PIIRedactor()
        text = "Call me at 555-123-4567 or +1 (555) 123-4567."
        
        result = redactor.redact(text, redaction_level="full")
        
        assert "555-123-4567" not in result["redacted_text"]
        assert "[PHONE REDACTED]" in result["redacted_text"]

    def test_redact_ssn(self):
        """Test SSN redaction."""
        redactor = PIIRedactor()
        text = "SSN: 123-45-6789"
        
        result = redactor.redact(text, redaction_level="full")
        
        assert "123-45-6789" not in result["redacted_text"]
        assert "[SSN REDACTED]" in result["redacted_text"]

    def test_full_redaction(self):
        """Test full redaction level."""
        redactor = PIIRedactor()
        text = """
        John Doe
        Email: john@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        """
        
        result = redactor.redact(text, redaction_level="full")
        
        assert result["total_redactions"] >= 3
        assert result["compliance_status"] == "compliant"

    def test_minimal_redaction(self):
        """Test minimal redaction level (only highly sensitive)."""
        redactor = PIIRedactor()
        text = """
        Email: john@example.com
        SSN: 123-45-6789
        """
        
        result = redactor.redact(text, redaction_level="minimal")
        
        # Should redact SSN but may keep email
        assert "[SSN REDACTED]" in result["redacted_text"]


class TestComplianceAuditLogger:
    """Test compliance audit logging."""

    def test_log_event(self):
        """Test logging an audit event."""
        logger = ComplianceAuditLogger()
        
        audit_id = logger.log_event(
            event_type="data_access",
            user_id="user_001",
            action="viewed_resume",
            resource_type="candidate",
            resource_id="cand_123"
        )
        
        assert "audit_" in audit_id
        assert len(logger.audit_log) == 1

    def test_get_audit_trail(self):
        """Test retrieving audit trail."""
        logger = ComplianceAuditLogger()
        
        logger.log_event("data_access", "user_001", "view", "candidate", "cand_1")
        logger.log_event("data_access", "user_002", "view", "candidate", "cand_2")
        logger.log_event("data_modification", "user_001", "update", "candidate", "cand_1")
        
        # Filter by user
        user1_events = logger.get_audit_trail(user_id="user_001")
        assert len(user1_events) == 2
        
        # Filter by resource
        cand1_events = logger.get_audit_trail(resource_id="cand_1")
        assert len(cand1_events) == 2

    def test_generate_compliance_report(self):
        """Test generating compliance report."""
        logger = ComplianceAuditLogger()
        
        for i in range(5):
            logger.log_event(
                "data_access",
                f"user_{i}",
                "view",
                "candidate",
                f"cand_{i}"
            )
        
        report = logger.generate_compliance_report("GDPR")
        
        assert report["framework"] == "GDPR"
        assert report["total_events"] == 5
        assert report["compliance_status"] == "compliant"


class TestIntegrationHub:
    """Test integration hub."""

    def test_register_integration(self):
        """Test registering an integration."""
        hub = IntegrationHub()
        
        integration_id = hub.register_integration(
            integration_type="greenhouse",
            config={"api_key": "test_key", "subdomain": "company"}
        )
        
        assert "greenhouse_" in integration_id
        assert len(hub.integrations) == 1

    def test_get_integration_status(self):
        """Test getting integration status."""
        hub = IntegrationHub()
        
        hub.register_integration("workday", {"tenant": "test"})
        hub.register_integration("greenhouse", {"api_key": "key"})
        
        status = hub.get_integration_status()
        
        assert len(status) == 2

    @pytest.mark.asyncio
    async def test_sync_job_requisition(self):
        """Test syncing job requisition."""
        hub = IntegrationHub()
        
        integration_id = hub.register_integration("workday", {"tenant": "test"})
        
        result = await hub.sync_job_requisition(integration_id, "REQ-001")
        
        assert result["status"] == "synced"
        assert result["requisition_id"] == "REQ-001"

    @pytest.mark.asyncio
    async def test_push_candidate(self):
        """Test pushing candidate to ATS."""
        hub = IntegrationHub()
        
        integration_id = hub.register_integration("greenhouse", {"api_key": "key"})
        
        result = await hub.push_candidate(
            integration_id,
            {"id": "cand_123", "name": "John Doe"}
        )
        
        assert result["status"] == "pushed"
        assert result["candidate_id"] == "cand_123"

    @pytest.mark.asyncio
    async def test_disabled_integration(self):
        """Test that disabled integrations raise error."""
        hub = IntegrationHub()
        
        integration_id = hub.register_integration(
            "workday",
            {"tenant": "test"},
            enabled=False
        )
        
        with pytest.raises(ValueError):
            await hub.sync_job_requisition(integration_id, "REQ-001")


class TestIntegration:
    """Test integration between security components."""

    def test_full_compliance_workflow(self):
        """Test complete compliance workflow."""
        redactor = PIIRedactor()
        auditor = ComplianceAuditLogger()
        
        # Redact PII from resume
        resume_text = "John Doe, john@example.com, 555-123-4567"
        redaction_result = redactor.redact(resume_text, "full")
        
        assert redaction_result["compliance_status"] == "compliant"
        
        # Log the access
        auditor.log_event(
            "data_access",
            "recruiter_001",
            "viewed_redacted_resume",
            "candidate",
            "cand_123",
            details={"redactions": redaction_result["total_redactions"]}
        )
        
        # Generate report
        report = auditor.generate_compliance_report("GDPR")
        
        assert report["total_events"] >= 1
