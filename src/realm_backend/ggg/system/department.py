from ic_python_db import (
    Boolean,
    Entity,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from ic_python_logging import get_logger

logger = get_logger("entity.department")

# Reserved name for the quarter's top governing organization (issue #240).
ROOT_ORG_NAME = "root"


class Department(Entity, TimestampedMixin):
    """Governance organization within a quarter (product name: Organization).

    See https://github.com/smart-social-contracts/realms/issues/240

    - Members are users only (no org nesting).
    - Policy (M/N, quorum, veto) governs how members exercise powers.
    - Optional fund link is the org's budget envelope.
    - Exactly one org named ``root`` with ``is_root=True`` per quarter.
    - Authority *over* other orgs is modeled by ``DepartmentAuthority``,
      not by parent/child membership.
    """

    __alias__ = "name"
    __version__ = 2

    name = String(max_length=256)
    description = String(max_length=512)
    head = ManyToOne("User", "headed_departments")
    members = ManyToMany(["User"], "departments")
    permissions = ManyToMany(["Permission"], "departments")
    extensions = ManyToMany(["Extension"], "departments")
    # Deprecated: org nesting is forbidden (issue #240). Kept for schema
    # compatibility with existing data; create/update APIs must reject writes.
    parent = ManyToOne("Department", "sub_departments")
    sub_departments = OneToMany("Department", "parent")
    notifications = OneToMany("Notification", "department")

    # --- Organization model (issue #240) ---
    is_root = Boolean(default=False)
    # Policy: require M approvals out of N eligible members (N=0 → use member count).
    policy_threshold_m = Integer(default=1)
    policy_threshold_n = Integer(default=1)
    # Minimum participation percent (0–100) among eligible members; 0 = no extra quorum.
    policy_quorum_percent = Integer(default=0)
    # Comma-separated principals that may veto an action under this org's policy.
    policy_veto_principals = String(max_length=2048, default="")
    # Budget envelope (governmental Fund).
    fund = OneToOne("Fund", "department")
    authorities_granted = OneToMany("DepartmentAuthority", "grantor")
    authorities_received = OneToMany("DepartmentAuthority", "target")

    @classmethod
    def migrate(cls, obj, from_version, to_version):
        if from_version < 2:
            obj.setdefault("is_root", (obj.get("name") or "") == ROOT_ORG_NAME)
            obj.setdefault("policy_threshold_m", 1)
            obj.setdefault("policy_threshold_n", 1)
            obj.setdefault("policy_quorum_percent", 0)
            obj.setdefault("policy_veto_principals", "")
        return obj

    def __repr__(self):
        return f"Department(name={self.name!r}, is_root={self.is_root!r})"

    def veto_principal_list(self) -> list[str]:
        raw = self.policy_veto_principals or ""
        return [p.strip() for p in raw.split(",") if p.strip()]
