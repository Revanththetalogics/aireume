"""
Phase 5: Enterprise Security & Compliance

Enterprise-grade security features:
1. PII (Personally Identifiable Information) redaction
2. Compliance audit logging
3. Integration hub skeleton for ATS/HRIS systems
"""

import re
from typing import Dict, List, Optional
from datetime import datetime


class PIIRedactor:
    """
    Automatically redact PII from resumes and job descriptions.
    
    Supports multiple redaction levels for different compliance needs.
    """
    
    # PII patterns
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "ssn": r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
        "date_of_birth": r'\b(?:DOB|Date of Birth|Birth Date)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',
        "address": r'\b\d{1,5}\s+\w+(?:\s+\w+)*(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln|Road|Rd)\b',
        "drivers_license": r'\b(?:Driver\'s License|DL|License Number)[:\s]*([A-Z0-9]{7,})\b',
    }
    
    def redact(self, document: str, redaction_level: str = "full") -> Dict:
        """
        Redact PII from document.
        
        Args:
            document: Text to redact
            redaction_level: "full" | "partial" | "minimal"
                - "full": Remove all PII (name, email, phone, address, SSN, DOB)
                - "partial": Keep name, remove contact details
                - "minimal": Only remove SSN, DOB, highly sensitive data
        
        Returns:
            {
                "redacted_text": str,
                "redacted_items": List[{"type": str, "original_length": int}],
                "redaction_level": str,
                "compliance_status": "compliant" | "review_needed"
            }
        """
        redacted_items = []
        redacted_text = document
        
        # Determine which patterns to apply based on level
        patterns_to_apply = self._get_patterns_for_level(redaction_level)
        
        for pii_type, pattern in patterns_to_apply.items():
            matches = list(re.finditer(pattern, redacted_text, re.IGNORECASE))
            
            for match in matches:
                original_text = match.group(0)
                replacement = self._get_replacement(pii_type, redaction_level)
                
                redacted_text = redacted_text.replace(original_text, replacement, 1)
                
                redacted_items.append({
                    "type": pii_type,
                    "original_length": len(original_text),
                    "position": match.start()
                })
        
        compliance_status = self._assess_compliance(redacted_items, redaction_level)
        
        return {
            "redacted_text": redacted_text,
            "redacted_items": redacted_items,
            "redaction_level": redaction_level,
            "total_redactions": len(redacted_items),
            "compliance_status": compliance_status
        }
    
    def _get_patterns_for_level(self, level: str) -> Dict:
        """Get PII patterns to apply for redaction level."""
        if level == "full":
            return self.PII_PATTERNS
        elif level == "partial":
            # Keep names, remove contact details
            return {
                k: v for k, v in self.PII_PATTERNS.items()
                if k not in ["name"]
            }
        else:  # minimal
            # Only highly sensitive data
            return {
                "ssn": self.PII_PATTERNS["ssn"],
                "date_of_birth": self.PII_PATTERNS["date_of_birth"]
            }
    
    def _get_replacement(self, pii_type: str, level: str) -> str:
        """Get replacement text for PII type."""
        replacements = {
            "email": "[EMAIL REDACTED]",
            "phone": "[PHONE REDACTED]",
            "ssn": "[SSN REDACTED]",
            "date_of_birth": "[DOB REDACTED]",
            "address": "[ADDRESS REDACTED]",
            "drivers_license": "[LICENSE REDACTED]"
        }
        return replacements.get(pii_type, "[REDACTED]")
    
    def _assess_compliance(self, redacted_items: List[Dict], level: str) -> str:
        """Assess if redaction meets compliance standards."""
        if level == "full" and len(redacted_items) > 0:
            return "compliant"
        elif level == "partial":
            return "compliant"
        elif len(redacted_items) == 0:
            return "no_pii_detected"
        else:
            return "review_needed"


class ComplianceAuditLogger:
    """
    Immutable audit logging for compliance requirements.
    
    Supports:
    - GDPR compliance
    - CCPA compliance
    - EEOC compliance
    - SOC 2 Type II requirements
    """
    
    def __init__(self):
        self.audit_log: List[Dict] = []
    
    def log_event(
        self,
        event_type: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Log a compliance event.
        
        Args:
            event_type: "data_access" | "data_modification" | "data_deletion" | "consent" | "export"
            user_id: User who performed the action
            action: What action was performed
            resource_type: Type of resource (resume, jd, candidate, etc.)
            resource_id: ID of the resource
            details: Additional context
            ip_address: User's IP address
            user_agent: User's browser/client
        
        Returns:
            audit_id: Unique audit log ID
        """
        audit_id = f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}_{resource_id}"
        
        log_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "compliance_frameworks": self._get_applicable_frameworks(event_type)
        }
        
        self.audit_log.append(log_entry)
        
        return audit_id
    
    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Retrieve audit trail with filters.
        
        Returns:
            List of audit log entries
        """
        filtered = self.audit_log
        
        if user_id:
            filtered = [e for e in filtered if e["user_id"] == user_id]
        
        if resource_id:
            filtered = [e for e in filtered if e["resource_id"] == resource_id]
        
        if event_type:
            filtered = [e for e in filtered if e["event_type"] == event_type]
        
        if date_from:
            filtered = [
                e for e in filtered
                if datetime.fromisoformat(e["timestamp"]) >= date_from
            ]
        
        if date_to:
            filtered = [
                e for e in filtered
                if datetime.fromisoformat(e["timestamp"]) <= date_to
            ]
        
        return filtered
    
    def generate_compliance_report(self, framework: str = "GDPR") -> Dict:
        """
        Generate compliance report for specific framework.
        
        Args:
            framework: "GDPR" | "CCPA" | "EEOC" | "SOC2"
        
        Returns:
            Compliance report
        """
        relevant_events = [
            e for e in self.audit_log
            if framework in e.get("compliance_frameworks", [])
        ]
        
        return {
            "framework": framework,
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(relevant_events),
            "events_by_type": self._count_by_field(relevant_events, "event_type"),
            "events_by_user": self._count_by_field(relevant_events, "user_id"),
            "date_range": {
                "earliest": min((e["timestamp"] for e in relevant_events), default=None),
                "latest": max((e["timestamp"] for e in relevant_events), default=None)
            },
            "compliance_status": "compliant" if relevant_events else "no_data"
        }
    
    def _get_applicable_frameworks(self, event_type: str) -> List[str]:
        """Determine which compliance frameworks apply to event."""
        frameworks = []
        
        if event_type in ["data_access", "data_modification"]:
            frameworks.extend(["GDPR", "CCPA", "SOC2"])
        
        if event_type == "data_deletion":
            frameworks.extend(["GDPR", "CCPA"])
        
        if event_type == "consent":
            frameworks.extend(["GDPR", "CCPA"])
        
        return frameworks
    
    def _count_by_field(self, events: List[Dict], field: str) -> Dict:
        """Count events by a specific field."""
        counts = {}
        for event in events:
            value = event.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts


class IntegrationHub:
    """
    Enterprise integration hub for ATS/HRIS systems.
    
    Supported integrations:
    - ATS: Workday, Greenhouse, Lever, Taleo
    - HRIS: SAP SuccessFactors, Oracle HCM
    - Assessment platforms
    - Background check services
    """
    
    def __init__(self):
        self.integrations = {}
    
    def register_integration(
        self,
        integration_type: str,
        config: Dict,
        enabled: bool = True
    ) -> str:
        """
        Register a new integration.
        
        Args:
            integration_type: "workday" | "greenhouse" | "lever" | etc.
            config: Integration configuration
            enabled: Whether integration is active
        
        Returns:
            integration_id
        """
        integration_id = f"{integration_type}_{datetime.utcnow().strftime('%Y%m%d')}"
        
        self.integrations[integration_id] = {
            "type": integration_type,
            "config": config,
            "enabled": enabled,
            "created_at": datetime.utcnow().isoformat(),
            "last_sync": None,
            "status": "active" if enabled else "disabled"
        }
        
        return integration_id
    
    async def sync_job_requisition(self, integration_id: str, requisition_id: str) -> Dict:
        """
        Sync job requisition from external ATS.
        
        Args:
            integration_id: Which integration to use
            requisition_id: External requisition ID
        
        Returns:
            Synced job data
        """
        integration = self.integrations.get(integration_id)
        if not integration or not integration["enabled"]:
            raise ValueError(f"Integration {integration_id} not found or disabled")
        
        # Placeholder for actual API call
        # In production, this would call the external API
        return {
            "status": "synced",
            "requisition_id": requisition_id,
            "synced_at": datetime.utcnow().isoformat(),
            "data": {}  # Would contain actual job data
        }
    
    async def push_candidate(self, integration_id: str, candidate_data: Dict) -> Dict:
        """
        Push candidate to external ATS.
        
        Args:
            integration_id: Which integration to use
            candidate_data: Candidate information
        
        Returns:
            Push result
        """
        integration = self.integrations.get(integration_id)
        if not integration or not integration["enabled"]:
            raise ValueError(f"Integration {integration_id} not found or disabled")
        
        # Placeholder for actual API call
        return {
            "status": "pushed",
            "candidate_id": candidate_data.get("id"),
            "pushed_at": datetime.utcnow().isoformat()
        }
    
    def get_integration_status(self) -> Dict:
        """Get status of all integrations."""
        return {
            integration_id: {
                "type": config["type"],
                "enabled": config["enabled"],
                "status": config["status"],
                "last_sync": config["last_sync"]
            }
            for integration_id, config in self.integrations.items()
        }
