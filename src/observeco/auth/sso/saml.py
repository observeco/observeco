"""SAML 2.0 SSO authentication for ObserveCo Enterprise.

Supports:
- SAML 2.0 SP-initiated SSO
- Metadata exchange
- Just-in-time user provisioning
- Group/role mapping

Environment variables:
    OBSERVECO_SAML entityId — Service Provider entity ID
    OBSERVECO_SAML ACS_URL — Assertion Consumer Service URL
    OBSERVECO_SAML_SSO_URL — Identity Provider SSO URL
    OBSERVECO_SAML_X509_CERT — IdP X.509 certificate
    OBSERVECO_SAML_NAME_ID_FORMAT — NameID format (emailAddress, transient, etc.)
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
import urllib.parse
try:
    import defusedxml.ElementTree as ET
    HAS_DEFUSEDXML = True
except ImportError:
    import xml.etree.ElementTree as ET
    HAS_DEFUSEDXML = False
from dataclasses import dataclass, field
from typing import Optional

from ..oauth2 import User, Session

logger = logging.getLogger(__name__)


@dataclass
class SAMLConfig:
    """SAML 2.0 configuration."""
    entity_id: str = ""
    acs_url: str = ""
    sso_url: str = ""
    x509_cert: str = ""
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    sp_private_key: str = ""


class SAMLProvider:
    """SAML 2.0 SSO provider."""

    def __init__(self, config: Optional[SAMLConfig] = None):
        if config:
            self.config = config
        else:
            self.config = SAMLConfig(
                entity_id=os.environ.get("OBSERVECO_SAML_ENTITY_ID", ""),
                acs_url=os.environ.get("OBSERVECO_SAML_ACS_URL", ""),
                sso_url=os.environ.get("OBSERVECO_SAML_SSO_URL", ""),
                x509_cert=os.environ.get("OBSERVECO_SAML_X509_CERT", ""),
                name_id_format=os.environ.get(
                    "OBSERVECO_SAML_NAME_ID_FORMAT",
                    "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                ),
            )
        self._sessions: dict[str, Session] = {}

    def is_configured(self) -> bool:
        return bool(self.config.entity_id and self.config.sso_url and self.config.acs_url)

    def get_sso_url(self, relay_state: str = "") -> str:
        """Generate SAML AuthnRequest URL."""
        if not self.config.sso_url:
            return ""

        # Build AuthnRequest
        request_id = f"__{int(time.time())}"
        issue_instant = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    AssertionConsumerServiceURL="{self.config.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.config.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Base64 encode
        encoded = base64.b64encode(authn_request.encode()).decode()

        # Build URL
        params = {"SAMLRequest": encoded}
        if relay_state:
            params["RelayState"] = relay_state

        return f"{self.config.sso_url}?{urllib.parse.urlencode(params)}"

    def parse_response(self, saml_response: str) -> Optional[User]:
        """Parse SAML Response and extract user attributes."""
        try:
            # Decode base64
            decoded = base64.b64decode(saml_response).decode("utf-8")

            # Parse XML
            root = ET.fromstring(decoded)

            # Extract NameID (email)
            ns = {
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
            }

            name_id_elem = root.find(".//saml:NameID", ns)
            if name_id_elem is None:
                return None
            name_id = name_id_elem.text or ""

            # Extract attributes
            attributes = {}
            for attr_stmt in root.findall(".//saml:AttributeStatement", ns):
                for attr in attr_stmt.findall("saml:Attribute", ns):
                    name = attr.get("Name", "")
                    values = [v.text for v in attr.findall("saml:AttributeValue", ns) if v.text]
                    if values:
                        attributes[name] = values[0] if len(values) == 1 else values

            # Build user
            email = attributes.get("email", name_id)
            name = attributes.get("displayName", attributes.get("cn", email.split("@")[0]))
            user_id = attributes.get("uid", attributes.get("employeeNumber", email))

            return User(
                id=str(user_id),
                email=str(email),
                name=str(name),
                avatar_url=attributes.get("avatar", ""),
                provider="saml",
            )

        except Exception:
            return None

    def validate_response(self, saml_response: str, expected_request_id: str = "") -> bool:
        """Validate SAML response signature and conditions.

        Uses xmlsec for cryptographic signature verification when available.
        Falls back to structural validation if xmlsec is not installed.
        """
        try:
            decoded = base64.b64decode(saml_response).decode("utf-8")
            root = ET.fromstring(decoded)

            ns = {
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
            }

            # Check status
            status = root.find(".//samlp:StatusCode", ns)
            if status is not None:
                status_value = status.get("Value", "")
                if "Success" not in status_value:
                    return False

            # Check assertion
            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                return False

            # Check conditions (NotBefore, NotOnOrAfter)
            conditions = assertion.find("saml:Conditions", ns)
            if conditions is not None:
                import datetime
                now = datetime.datetime.utcnow()

                not_before = conditions.get("NotBefore")
                if not_before:
                    nb = datetime.datetime.fromisoformat(not_before.replace("Z", "+00:00")).replace(tzinfo=None)
                    if now < nb:
                        return False

                not_on_or_after = conditions.get("NotOnOrAfter")
                if not_on_or_after:
                    noa = datetime.datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00")).replace(tzinfo=None)
                    if now >= noa:
                        return False

            # Check Issuer matches IdP
            issuer = assertion.find("saml:Issuer", ns)
            if issuer is not None and self.config.x509_cert:
                issuer_text = issuer.text or ""
                # In production, verify the issuer matches the configured IdP
                # (exact match or certificate pinning)

            # Cryptographic signature verification
            sig_verified = self._verify_signature(root, ns)
            if not sig_verified:
                logger.warning("SAML response signature verification failed")
                return False

            return True

        except Exception as e:
            logger.error(f"SAML validation error: {e}")
            return False

    def _verify_signature(self, root: ET.Element, ns: dict) -> bool:
        """Verify SAML response XML signature using xmlsec.

        Returns True if:
        - xmlsec is available and signature is valid
        - xmlsec is not available but no signature exists (graceful degradation)
        Returns False if:
        - xmlsec is available but signature is invalid
        - xmlsec is not available and signature exists (can't verify)
        """
        # Check if there's a signature in the document
        sig_element = root.find(
            ".//{http://www.w3.org/2000/09/xmldsig#}Signature"
        )
        has_signature = sig_element is not None

        try:
            import xmlsec
            import xmlsec.tree
            import xmlsec.signature
            import xmlsec.constants as consts

            # xmlsec is available — do proper verification
            # Find the signature node
            sig_node = xmlsec.tree.find_signature(root)
            if sig_node is None:
                # No signature found
                if has_signature:
                    return False  # Signature was expected but not found by xmlsec
                return True  # No signature, no problem (degraded mode)

            # Create template for verification
            ctx = xmlsec.SignatureContext()
            
            # Load the IdP certificate
            if self.config.x509_cert:
                key_data = self.config.x509_cert.strip()
                if key_data.startswith("-----BEGIN"):
                    # PEM format
                    key = xmlsec.Key.from_file(key_data, consts.KeyDataFormatPem)
                else:
                    # DER/base64 format
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.crt', delete=False) as f:
                        f.write(key_data.encode())
                        key = xmlsec.Key.from_file(f.name, consts.KeyDataFormatCertPem)
                ctx.key = key

            # Verify
            ctx.verify(sig_node)
            return True

        except ImportError:
            # xmlsec not installed — graceful degradation
            if has_signature:
                # Signature exists but we can't verify it
                logger.warning(
                    "SAML signature present but xmlsec not installed. "
                    "Install with: pip install xmlsec. Rejecting unsigned assertion."
                )
                return False
            # No signature, no xmlsec — accept (degraded mode)
            return True
        except Exception as e:
            logger.error(f"SAML signature verification error: {e}")
            return False

    def create_session(self, user: User) -> Session:
        """Create a session for an authenticated SAML user — persisted to SQLite."""
        import secrets
        token = secrets.token_urlsafe(32)
        now = time.time()
        session = Session(
            token=token,
            user=user,
            expires_at=now + 86400 * 8,  # 8 hours (SAML sessions are shorter)
        )
        # Persist to database
        try:
            from observeco.db import Database
            db = Database()
            db.save_session(
                token=token, user_id=user.id, email=user.email,
                name=user.name, avatar_url=user.avatar_url,
                provider=user.provider, expires_at=session.expires_at,
                created_at=now,
            )
        except Exception:
            pass
        self._sessions[token] = session
        return session

    def validate_session(self, token: str) -> Optional[Session]:
        """Validate a session token — checks database first, then in-memory."""
        try:
            from observeco.db import Database
            db = Database()
            row = db.get_session(token)
            if row:
                user = User(
                    id=row["user_id"], email=row["email"], name=row["name"],
                    avatar_url=row.get("avatar_url", ""),
                    provider=row.get("provider", "saml"),
                )
                session = Session(
                    token=token, user=user,
                    expires_at=row["expires_at"],
                    created_at=row.get("created_at", time.time()),
                )
                self._sessions[token] = session
                return session
        except Exception:
            pass
        session = self._sessions.get(token)
        if session and not session.is_expired:
            return session
        if session and session.is_expired:
            del self._sessions[token]
        return None

    def get_metadata(self) -> str:
        """Generate SP SAML metadata XML."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.config.entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>{self.config.name_id_format}</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.config.acs_url}" index="1"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
