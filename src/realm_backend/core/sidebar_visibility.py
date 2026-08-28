"""Guest vs member sidebar visibility.

Guest = authenticated principal with no realm membership (no member/admin
profile). ``get_sidebar`` must not treat “has a caller” as “is a member”:
that is how guests were seeing REALM MANAGEMENT / System.
"""

MEMBER_SIDEBAR_PROFILES = frozenset({"member", "admin"})
REALM_MANAGEMENT_CATEGORY = "realm_management"


def is_realm_member(profiles) -> bool:
    if not profiles:
        return False
    return any(profile in MEMBER_SIDEBAR_PROFILES for profile in profiles)


def should_include_core_system(profiles) -> bool:
    """System is core chrome for members, not a guest row."""
    return is_realm_member(profiles)


def include_sidebar_category(category_id, profiles) -> bool:
    if category_id == REALM_MANAGEMENT_CATEGORY:
        return is_realm_member(profiles)
    return True
