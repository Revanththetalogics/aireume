"""
Lightweight SAML 2.0 service for SSO authentication.

This is a simplified implementation using only Python stdlib + cryptography.
For production hardening, consider swapping to python3-saml or pysaml2.
"""
import base64
import uuid
import zlib
import secrets
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from sqlalchemy.orm import Session

from app.backend.models.db_models import SSOConfig, User, Tenant

# ─── SAML Namespaces ──────────────────────────────────────────────────────────

SAML_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
XMLDSIG_NS = "http://www.w3.org/2000/09/xmldsig#"

_NS_MAP = {
    "saml2p": SAML_PROTOCOL_NS,
    "saml2": SAML_ASSERTION_NS,
    "ds": XMLDSIG_NS,
}


def _ns_tag(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


# ─── Certificate helpers ──────────────────────────────────────────────────────

def _parse_x509_cert(pem_str: str) -> x509.Certificate:
    """Parse a PEM or bare-base64 X.509 certificate string."""
    pem = pem_str.strip()
    if not pem.startswith("-----BEGIN"):
        pem = f"-----BEGIN CERTIFICATE-----\n{pem}\n-----END CERTIFICATE-----"
    return x509.load_pem_x509_certificate(pem.encode())


def _verify_signature(signed_xml_bytes: bytes, cert_pem: str) -> bool:
    """
    Simplified SAML signature verification.

    This performs a best-effort RSA-SHA256 signature verification on the
    first <ds:Signature> element found in the XML.  It is sufficient for
    basic SAML IdP trust but does NOT implement full SAML spec canonical
    form (C14N).  Harden this when migrating to python3-saml.
    """
    try:
        root = ET.fromstring(signed_xml_bytes)
        sig_elem = root.find(f".//{_ns_tag(XMLDSIG_NS, 'Signature')}")
        if sig_elem is None:
            return False

        signed_info = sig_elem.find(_ns_tag(XMLDSIG_NS, "SignedInfo"))
        signature_value = sig_elem.find(_ns_tag(XMLDSIG_NS, "SignatureValue"))
        key_info = sig_elem.find(_ns_tag(XMLDSIG_NS, "KeyInfo"))

        if signed_info is None or signature_value is None:
            return False

        # Prefer certificate from SAML response itself, fallback to configured cert
        cert_text = None
        if key_info is not None:
            x509_data = key_info.find(_ns_tag(XMLDSIG_NS, "X509Data"))
            if x509_data is not None:
                x509_cert = x509_data.find(_ns_tag(XMLDSIG_NS, "X509Certificate"))
                if x509_cert is not None and x509_cert.text:
                    cert_text = x509_cert.text.strip()

        cert = _parse_x509_cert(cert_text or cert_pem)
        pubkey = cert.public_key()

        sig_b64 = signature_value.text.strip() if signature_value.text else ""
        signature = base64.b64decode(sig_b64)

        # Reconstruct SignedInfo bytes (naive — should use C14N in production)
        signed_info_bytes = ET.tostring(signed_info, encoding="utf-8")
        pubkey.verify(
            signature,
            signed_info_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


# ─── SAML Request / Response helpers ──────────────────────────────────────────

def _build_authn_request(
    sp_entity_id: str,
    acs_url: str,
    request_id: str,
) -> bytes:
    """Build a minimal SAML 2.0 AuthnRequest XML document."""
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="{SAML_PROTOCOL_NS}"
    xmlns:saml="{SAML_ASSERTION_NS}"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination=""
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    AssertionConsumerServiceURL="{acs_url}">
    <saml:Issuer>{sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true"/>
</samlp:AuthnRequest>'''
    return xml.encode("utf-8")


def _extract_assertion_attributes(assertion_elem: ET.Element) -> dict:
    """Extract attribute statement values from a SAML Assertion."""
    attrs = {}
    attr_statement = assertion_elem.find(f".//{_ns_tag(SAML_ASSERTION_NS, 'AttributeStatement')}")
    if attr_statement is not None:
        for attr in attr_statement.findall(_ns_tag(SAML_ASSERTION_NS, "Attribute")):
            name = attr.get("Name", "").strip()
            values = [
                v.text.strip()
                for v in attr.findall(_ns_tag(SAML_ASSERTION_NS, "AttributeValue"))
                if v.text
            ]
            if values:
                # Common SAML attribute names
                if "emailaddress" in name.lower() or name.lower() == "email":
                    attrs["email"] = values[0]
                elif "givenname" in name.lower() or name.lower() == "first_name":
                    attrs["first_name"] = values[0]
                elif "surname" in name.lower() or name.lower() == "last_name":
                    attrs["last_name"] = values[0]
                elif "displayname" in name.lower() or name.lower() == "name":
                    attrs["name"] = values[0]
                else:
                    attrs[name] = values[0]
    return attrs


def _extract_name_id(subject_elem: ET.Element) -> Optional[str]:
    """Extract NameID from Subject element."""
    name_id = subject_elem.find(_ns_tag(SAML_ASSERTION_NS, "NameID"))
    if name_id is not None and name_id.text:
        return name_id.text.strip()
    return None


# ─── Service Class ────────────────────────────────────────────────────────────

class SSOService:
    """Lightweight SAML 2.0 processor."""

    def generate_saml_request(self, sso_config: SSOConfig) -> tuple[str, str]:
        """
        Generate SAML AuthnRequest, return (redirect_url, request_id).

        The request is deflate + base64 encoded and appended to the IdP SSO URL
        as a SAMLRequest query parameter.
        """
        request_id = f"ARIA{uuid.uuid4().hex[:24].upper()}"
        authn_xml = _build_authn_request(
            sp_entity_id=sso_config.sp_entity_id,
            acs_url=sso_config.sp_acs_url,
            request_id=request_id,
        )
        # Deflate + Base64 encode (SAML Redirect binding)
        compressed = zlib.compress(authn_xml)[2:-4]  # strip zlib header/footer
        saml_request_b64 = base64.b64encode(compressed).decode()

        sep = "&" if "?" in sso_config.idp_sso_url else "?"
        redirect_url = f"{sso_config.idp_sso_url}{sep}SAMLRequest={saml_request_b64}"
        return redirect_url, request_id

    def process_saml_response(
        self,
        saml_response_b64: str,
        sso_config: SSOConfig,
        verify_signature: bool = True,
    ) -> dict:
        """
        Validate and parse SAML Response, return user attributes dict.

        Returns:
            {
                "email": str,
                "name": str | None,
                "name_id": str,
                "first_name": str | None,
                "last_name": str | None,
            }
        Raises:
            ValueError: if response is invalid, expired, or signature fails.
        """
        try:
            response_xml = base64.b64decode(saml_response_b64)
        except Exception:
            raise ValueError("Invalid SAMLResponse base64 encoding")

        # Best-effort signature verification
        if verify_signature and sso_config.idp_certificate:
            sig_ok = _verify_signature(response_xml, sso_config.idp_certificate)
            if not sig_ok:
                raise ValueError("SAML Response signature verification failed")

        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid SAML Response XML: {exc}")

        # Check for error status
        status_elem = root.find(_ns_tag(SAML_PROTOCOL_NS, "Status"))
        if status_elem is not None:
            status_code = status_elem.find(f".//{_ns_tag(SAML_PROTOCOL_NS, 'StatusCode')}")
            if status_code is not None:
                code = status_code.get("Value", "")
                if "Success" not in code:
                    raise ValueError(f"SAML error status: {code}")

        # Find Assertion
        assertion = root.find(_ns_tag(SAML_ASSERTION_NS, "Assertion"))
        if assertion is None:
            # Some IdPs nest assertion inside EncryptedAssertion — not supported yet
            raise ValueError("No SAML Assertion found in response")

        # Check Conditions (Audience & NotOnOrAfter)
        conditions = assertion.find(_ns_tag(SAML_ASSERTION_NS, "Conditions"))
        if conditions is not None:
            not_before = conditions.get("NotBefore")
            not_on_or_after = conditions.get("NotOnOrAfter")
            now = datetime.now(timezone.utc)

            if not_on_or_after:
                expiry = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
                if now >= expiry:
                    raise ValueError("SAML Assertion has expired")

            if not_before:
                start = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
                if now < start:
                    raise ValueError("SAML Assertion not yet valid")

            # Audience check
            audience_restriction = conditions.find(_ns_tag(SAML_ASSERTION_NS, "AudienceRestriction"))
            if audience_restriction is not None:
                audiences = [
                    a.text.strip()
                    for a in audience_restriction.findall(_ns_tag(SAML_ASSERTION_NS, "Audience"))
                    if a.text
                ]
                if sso_config.sp_entity_id and sso_config.sp_entity_id not in audiences:
                    raise ValueError("SAML Audience mismatch")

        # Extract NameID
        subject = assertion.find(_ns_tag(SAML_ASSERTION_NS, "Subject"))
        name_id = _extract_name_id(subject) if subject is not None else None
        if not name_id:
            raise ValueError("SAML Assertion missing NameID")

        # Extract attributes
        attrs = _extract_assertion_attributes(assertion)

        # Build result
        email = attrs.get("email", name_id)  # fallback to NameID if no email attr
        name = attrs.get("name")
        if not name:
            first = attrs.get("first_name", "")
            last = attrs.get("last_name", "")
            name = f"{first} {last}".strip() or None

        return {
            "email": email.lower().strip(),
            "name": name,
            "name_id": name_id,
            "first_name": attrs.get("first_name"),
            "last_name": attrs.get("last_name"),
        }

    def get_or_create_user(
        self,
        db: Session,
        tenant_id: int,
        sso_config: SSOConfig,
        user_attrs: dict,
    ) -> User:
        """
        Find existing user by email or auto-provision.

        For auto-provisioned users a cryptographically random unusable password
        is generated because the column is non-nullable.
        """
        email = user_attrs["email"]
        user = db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()

        if user:
            return user

        if not sso_config.auto_provision:
            raise ValueError("User not found and auto-provisioning is disabled")

        # Auto-provision user with random unusable password
        random_password = secrets.token_urlsafe(32)
        # Import hash function from auth module
        from app.backend.routes.auth import _hash_password

        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=_hash_password(random_password),
            role=sso_config.default_role or "viewer",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# ─── Singleton instance ───────────────────────────────────────────────────────

sso_service = SSOService()
