from datetime import datetime
from typing import Optional

from kybra_simple_db import Entity, ManyToOne, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

from ..system.constants import STATUS_MAX_LENGTH

logger = get_logger("entity.license")


class LicenseType:
    COURT = "court"
    CHURCH = "church"
    JUSTICE_PROVIDER = "justice_provider"
    BUSINESS = "business"
    PROFESSIONAL = "professional"
    OTHER = "other"


class License(Entity, TimestampedMixin):
    """
    State-issued permission to act as a Court, Church, JusticeProvider, or other entity.
    
    Licenses authorize Organizations or Courts to operate within the Realm's
    legal framework. They have validity periods and can be revoked.
    """
    
    __alias__ = "name"
    name = String(max_length=256)
    license_type = String(max_length=32)  # court, church, justice_provider, etc.
    description = String(max_length=1024)
    status = String(max_length=STATUS_MAX_LENGTH)  # active, suspended, revoked, expired
    issued_date = String(max_length=64)  # ISO format
    expiry_date = String(max_length=64)  # ISO format
    issuing_authority = String(max_length=256)
    organization = OneToOne("Organization", "license")
    court = OneToOne("Court", "license")
    justice_system = OneToOne("JusticeSystem", "license")
    metadata = String(max_length=1024)

    def __repr__(self):
        return f"License(name={self.name!r}, type={self.license_type!r}, status={self.status!r})"

    def is_valid(self) -> bool:
        """Check if this License is currently valid."""
        if self.status != "active":
            return False
        if self.expiry_date:
            from datetime import datetime
            try:
                # Handle various ISO formats
                expiry_str = self.expiry_date.replace('Z', '+00:00')
                # Remove timezone info for comparison with utcnow()
                if '+' in expiry_str:
                    expiry_str = expiry_str.split('+')[0]
                expiry = datetime.fromisoformat(expiry_str)
                if expiry < datetime.utcnow():
                    return False
            except (ValueError, AttributeError):
                pass
        return True

    @staticmethod
    def license_issued_posthook(license: "License") -> None:
        """Hook called after License issued. Override for registry updates."""
        logger.info(f"License {license.name} issued")

    @staticmethod
    def license_revoked_posthook(license: "License") -> None:
        """Hook called after License revoked. Override for court deactivation."""
        logger.info(f"License {license.name} revoked")


def license_issue(
    name: str,
    license_type: str,
    organization: Optional["Organization"] = None,
    description: str = "",
    validity_days: int = 365,
    issuing_authority: str = "",
    metadata: str = ""
) -> "License":
    """
    Issue a new License.
    
    Args:
        name: License name
        license_type: Type of license (court, church, etc.)
        organization: Optional Organization to license
        description: License description
        validity_days: Number of days until expiry
        issuing_authority: Authority issuing the license
        metadata: Optional JSON metadata
        
    Returns:
        The created License
    """
    from datetime import timedelta
    
    now = datetime.utcnow()
    expiry = now + timedelta(days=validity_days)
    
    kwargs = {
        "name": name,
        "license_type": license_type,
        "description": description,
        "status": "active",
        "issued_date": now.isoformat(),
        "expiry_date": expiry.isoformat(),
        "issuing_authority": issuing_authority,
        "metadata": metadata
    }
    
    # Only add organization if not None
    if organization is not None:
        kwargs["organization"] = organization
    
    license = License(**kwargs)
    
    License.license_issued_posthook(license)
    return license


def license_revoke(license: "License", reason: str = "") -> "License":
    """
    Revoke a License.
    
    Args:
        license: The License to revoke
        reason: Reason for revocation
        
    Returns:
        The updated License
    """
    if license.status == "revoked":
        raise ValueError(f"License {license.name} is already revoked")
    
    license.status = "revoked"
    if reason:
        license.metadata = f'{{"revoke_reason": "{reason}"}}'
    
    License.license_revoked_posthook(license)
    return license
