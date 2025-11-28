"""
Admin Dashboard Models

This module contains database models specific to the admin dashboard extension.
"""

import secrets
import string
from datetime import datetime, timedelta

from kybra_simple_db import Entity, TimestampedMixin
from kybra_simple_db.properties import Integer, String


class RegistrationCode(Entity, TimestampedMixin):
    """
    Model for storing registration codes used for user signup.

    Attributes:
        code (str): Unique registration code (indexed)
        user_id (str): ID of the user this code is for (indexed)
        email (str): Email address of the user (if known)
        expires_at (datetime): When this code expires
        used (bool): Whether this code has been used
        used_at (datetime): When this code was used (if used)
        created_by (str): Admin user ID who created this code
        frontend_url (str): Base URL for the frontend (for building full URL)
    """

    # Use __alias__ to enable lookup by code
    __alias__ = "code"

    # Define fields with proper types
    code = String(max_length=64)  # Will be indexed due to __alias__
    user_id = String(max_length=64)
    email = String(max_length=255)
    expires_at = Integer()  # Store as timestamp
    used = Integer(default=0)  # 0 = False, 1 = True
    used_at = Integer()  # Store as timestamp, 0 = None
    created_by = String(max_length=64)
    frontend_url = String(max_length=512)

    @classmethod
    def create(
        cls,
        user_id: str,
        created_by: str,
        frontend_url: str,
        email: str = None,
        expires_in_hours: int = 24,
    ) -> "RegistrationCode":
        """Create a new registration code."""
        # Generate a random 16-character alphanumeric code
        alphabet = string.ascii_letters + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(16))

        expires_timestamp = int(
            (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp()
        )

        return cls(
            code=code,
            user_id=user_id,
            email=email or "",
            expires_at=expires_timestamp,
            used=0,
            used_at=0,
            created_by=created_by,
            frontend_url=frontend_url.rstrip("/"),
        )

    @property
    def registration_url(self) -> str:
        """Get the full registration URL for this code."""
        return f"{self.frontend_url}/extensions/admin_dashboard/user_registration?code={self.code}"

    def mark_used(self):
        """Mark this code as used."""
        self.used = 1
        self.used_at = int(datetime.utcnow().timestamp())
        self.save()

    def is_valid(self) -> bool:
        """Check if this code is valid (not used and not expired)."""
        current_timestamp = int(datetime.utcnow().timestamp())
        return self.used == 0 and current_timestamp < self.expires_at

    @classmethod
    def find_by_code(cls, code: str) -> "RegistrationCode":
        """Find a registration code by its code value."""
        return cls[code]

    @classmethod
    def find_by_user_id(cls, user_id: str) -> list["RegistrationCode"]:
        """Find all registration codes for a specific user."""
        return [code for code in cls.instances() if code.user_id == user_id]
