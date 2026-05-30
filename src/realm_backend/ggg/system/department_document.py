from ic_python_db import Entity, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.department_document")


class DepartmentDocument(Entity, TimestampedMixin):
    """An encrypted document shared with a department.

    Demonstrates the generic, reusable encrypted-sharing layer for a payload
    other than personal data. The ``ciphertext`` is opaque to the canister
    (AES-GCM under a per-document Data Encryption Key); read access is governed
    by ``KeyEnvelope`` records at scope ``dept:<department>:doc:<id>``, which the
    pluggable policy in :mod:`core.crypto_scopes` lets the department head (or a
    realm admin) manage.

    The canister never sees the plaintext, the DEK, or any vetKey — those live
    only in authorized members' browsers.
    """

    department = String(max_length=256)  # Department name
    title = String(max_length=512)
    ciphertext = String()  # enc:v=2:iv=...:d=... AES-GCM blob (may be empty until set)
    scope = String(max_length=512)  # dept:<department>:doc:<id>
    created_by = String(max_length=128)  # author principal

    def __repr__(self):
        return (
            f"DepartmentDocument(id={getattr(self, '_id', None)!r}, "
            f"title={self.title!r}, department={self.department!r})"
        )
