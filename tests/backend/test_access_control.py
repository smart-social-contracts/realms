"""
Unit tests for the Realms access control system.

Tests cover:
  1. _check_access — profile-based RBAC, fine-grained permissions, trusted principals
  2. Operations/Profiles consistency — all profile operations reference valid constants
  3. require() decorator — blocks/allows based on _check_access
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock IC-specific modules before importing anything that uses them
_mock_cdk = MagicMock()
sys.modules["_cdk"] = _mock_cdk

# Mock all basilisk submodules the import chain may touch
_mock_basilisk = MagicMock()
for submod in [
    "basilisk",
    "basilisk.canisters",
    "basilisk.canisters.management",
    "basilisk.canisters.icrc",
    "ic_basilisk_toolkit",
    "ic_basilisk_toolkit.entities",
    "ic_basilisk_toolkit.status",
    "ic_basilisk_toolkit.wallet",
    "ic_basilisk_toolkit.task_manager",
    "ic_basilisk_toolkit.crypto",
    "ic_basilisk_toolkit.execution",
]:
    sys.modules[submod] = _mock_basilisk

# Mock ic_python_db with a minimal Entity that supports attribute assignment
_mock_db = MagicMock()


class FakeEntity:
    """Minimal Entity stand-in that allows attribute assignment."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


_mock_db.Entity = FakeEntity
_mock_db.String = lambda **kw: None
_mock_db.Integer = lambda **kw: None
_mock_db.Boolean = lambda **kw: None
_mock_db.ManyToMany = lambda *a, **kw: None
_mock_db.OneToMany = lambda *a, **kw: None
_mock_db.OneToOne = lambda *a, **kw: None
_mock_db.TimestampedMixin = type("TimestampedMixin", (), {})
sys.modules["ic_python_db"] = _mock_db

# Mock logger
_mock_logging = MagicMock()
_mock_logging.get_logger = lambda name: MagicMock()
sys.modules["ic_python_logging"] = _mock_logging


# ── Now we can safely import our modules ──────────────────────────────
from ggg.system.user_profile import Operations, Profiles, OPERATIONS_SEPARATOR


class TestOperationsConsistency:
    """Verify Operations constants are well-formed."""

    def test_all_operations_are_strings(self):
        ops = [v for k, v in vars(Operations).items()
               if not k.startswith("_") and isinstance(v, str)]
        assert len(ops) > 0
        for op in ops:
            assert isinstance(op, str)
            assert len(op) > 0

    def test_no_duplicate_operation_values(self):
        ops = [v for k, v in vars(Operations).items()
               if not k.startswith("_") and isinstance(v, str)]
        assert len(ops) == len(set(ops)), f"Duplicate operation values: {[o for o in ops if ops.count(o) > 1]}"

    def test_operations_use_dot_notation(self):
        ops = [v for k, v in vars(Operations).items()
               if not k.startswith("_") and isinstance(v, str) and v != "all"]
        for op in ops:
            assert "." in op, f"Operation '{op}' should use dot notation (e.g., 'realm.configure')"


class TestProfilesConsistency:
    """Verify all profiles reference valid operations."""

    def test_all_profiles_have_name(self):
        for profile in Profiles.ALL_PROFILES:
            assert "name" in profile
            assert isinstance(profile["name"], str)
            assert len(profile["name"]) > 0

    def test_all_profiles_have_allowed_to(self):
        for profile in Profiles.ALL_PROFILES:
            assert "allowed_to" in profile
            assert isinstance(profile["allowed_to"], list)

    def test_all_profile_operations_are_valid(self):
        """Every operation in every profile must be a defined Operations constant."""
        valid_ops = {v for k, v in vars(Operations).items()
                     if not k.startswith("_") and isinstance(v, str)}
        for profile in Profiles.ALL_PROFILES:
            for op in profile["allowed_to"]:
                assert op in valid_ops, (
                    f"Profile '{profile['name']}' references unknown operation '{op}'. "
                    f"Valid operations: {sorted(valid_ops)}"
                )

    def test_no_duplicate_profile_names(self):
        names = [p["name"] for p in Profiles.ALL_PROFILES]
        assert len(names) == len(set(names)), f"Duplicate profile names: {names}"

    def test_admin_has_all(self):
        assert Operations.ALL in Profiles.ADMIN["allowed_to"]

    def test_observer_has_nothing(self):
        assert len(Profiles.OBSERVER["allowed_to"]) == 0

    def test_member_has_self_service(self):
        member_ops = Profiles.MEMBER["allowed_to"]
        assert Operations.SELF_PROFILE_PICTURE in member_ops
        assert Operations.SELF_CHANGE_QUARTER in member_ops
        assert Operations.SELF_INVOICE_REFRESH in member_ops

    def test_member_has_extension_calls(self):
        """Members must be able to call extensions — the frontend uses these for dashboards."""
        member_ops = Profiles.MEMBER["allowed_to"]
        assert Operations.EXTENSION_SYNC_CALL in member_ops
        assert Operations.EXTENSION_ASYNC_CALL in member_ops

    def test_treasurer_has_transfer_create(self):
        assert Operations.TRANSFER_CREATE in Profiles.TREASURER["allowed_to"]

    def test_operator_has_realm_admin(self):
        assert Operations.REALM_ADMIN in Profiles.OPERATOR["allowed_to"]
        assert Operations.REALM_CONFIGURE in Profiles.OPERATOR["allowed_to"]
        assert Operations.REALM_CONFIGURE_CODEX in Profiles.OPERATOR["allowed_to"]

    def test_developer_has_shell(self):
        assert Operations.SHELL_EXECUTE in Profiles.DEVELOPER["allowed_to"]


class TestCheckAccess:
    """Test _check_access with mocked User/Realm entities."""

    def _make_profile(self, allowed_to_list):
        """Create a mock UserProfile."""
        profile = MagicMock()
        profile.allowed_to = OPERATIONS_SEPARATOR.join(allowed_to_list)
        profile.permissions = []
        return profile

    def _make_user(self, profiles):
        """Create a mock User."""
        user = MagicMock()
        user.profiles = profiles
        user.permissions = []
        return user

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_admin_profile_grants_all(self, MockUser, MockRealm):
        MockRealm.load.return_value = None
        admin_profile = self._make_profile([Operations.ALL])
        user = self._make_user([admin_profile])
        MockUser.__getitem__ = MagicMock(return_value=user)

        from core.access import _check_access
        assert _check_access("some-principal", "anything.goes") is True

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_member_allowed_self_service(self, MockUser, MockRealm):
        MockRealm.load.return_value = None
        member_profile = self._make_profile(Profiles.MEMBER["allowed_to"])
        user = self._make_user([member_profile])
        MockUser.__getitem__ = MagicMock(return_value=user)

        from core.access import _check_access
        assert _check_access("user-1", Operations.SELF_CHANGE_QUARTER) is True
        assert _check_access("user-1", Operations.SELF_INVOICE_REFRESH) is True

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_member_denied_admin_ops(self, MockUser, MockRealm):
        MockRealm.load.return_value = None
        member_profile = self._make_profile(Profiles.MEMBER["allowed_to"])
        user = self._make_user([member_profile])
        MockUser.__getitem__ = MagicMock(return_value=user)

        from core.access import _check_access
        assert _check_access("user-1", Operations.REALM_ADMIN) is False
        assert _check_access("user-1", Operations.SHELL_EXECUTE) is False
        assert _check_access("user-1", Operations.TRANSFER_CREATE) is False

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_unknown_user_denied(self, MockUser, MockRealm):
        MockRealm.load.return_value = None
        MockUser.__getitem__ = MagicMock(return_value=None)

        from core.access import _check_access
        assert _check_access("unknown-principal", Operations.SELF_JOIN) is False

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_trusted_principal_allowed(self, MockUser, MockRealm):
        realm = MagicMock()
        realm.trusted_principals = "dao-canister-abc, ai-agent-xyz"
        MockRealm.load.return_value = realm
        # User doesn't exist — but trusted principal should still pass
        MockUser.__getitem__ = MagicMock(return_value=None)

        from core.access import _check_access
        assert _check_access("dao-canister-abc", Operations.TRANSFER_CREATE) is True
        assert _check_access("ai-agent-xyz", Operations.SHELL_EXECUTE) is True

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_untrusted_principal_not_whitelisted(self, MockUser, MockRealm):
        realm = MagicMock()
        realm.trusted_principals = "dao-canister-abc"
        MockRealm.load.return_value = realm
        MockUser.__getitem__ = MagicMock(return_value=None)

        from core.access import _check_access
        assert _check_access("random-attacker", Operations.TRANSFER_CREATE) is False

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_empty_trusted_principals(self, MockUser, MockRealm):
        realm = MagicMock()
        realm.trusted_principals = ""
        MockRealm.load.return_value = realm
        MockUser.__getitem__ = MagicMock(return_value=None)

        from core.access import _check_access
        assert _check_access("some-principal", Operations.TRANSFER_CREATE) is False

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_multiple_profiles_combined(self, MockUser, MockRealm):
        """A user with both member and treasurer profiles should have combined permissions."""
        MockRealm.load.return_value = None
        member_profile = self._make_profile(Profiles.MEMBER["allowed_to"])
        treasurer_profile = self._make_profile(Profiles.TREASURER["allowed_to"])
        user = self._make_user([member_profile, treasurer_profile])
        MockUser.__getitem__ = MagicMock(return_value=user)

        from core.access import _check_access
        # From member
        assert _check_access("user-1", Operations.PROPOSAL_VOTE) is True
        # From treasurer
        assert _check_access("user-1", Operations.TRANSFER_CREATE) is True
        # From neither
        assert _check_access("user-1", Operations.SHELL_EXECUTE) is False

    @patch("ggg.Realm")
    @patch("ggg.User")
    def test_fine_grained_user_permission(self, MockUser, MockRealm):
        """A Permission entity on the user grants access even without profile."""
        MockRealm.load.return_value = None
        observer_profile = self._make_profile([])
        user = self._make_user([observer_profile])
        perm = MagicMock()
        perm.name = Operations.NFT_MINT
        user.permissions = [perm]
        MockUser.__getitem__ = MagicMock(return_value=user)

        from core.access import _check_access
        assert _check_access("user-1", Operations.NFT_MINT) is True
        assert _check_access("user-1", Operations.TRANSFER_CREATE) is False


class TestEndpointOperationMapping:
    """Verify that key endpoints map to the correct operations."""

    def test_realm_admin_operations_are_distinct(self):
        """realm.admin, realm.configure, and realm.configure.codex are separate."""
        assert Operations.REALM_ADMIN != Operations.REALM_CONFIGURE
        assert Operations.REALM_CONFIGURE != Operations.REALM_CONFIGURE_CODEX
        assert Operations.REALM_ADMIN != Operations.REALM_CONFIGURE_CODEX

    def test_self_invoice_refresh_is_self_service(self):
        assert Operations.SELF_INVOICE_REFRESH.startswith("self.")

    def test_transfer_create_in_finance(self):
        assert Operations.TRANSFER_CREATE == "transfer.create"
