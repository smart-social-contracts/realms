"""Tests for Quarter entity and Realm federation fields (Issue #143 Phase 1)."""

import os
import sys
import pytest

# realm_backend is not an installable package; add src/ to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from ic_python_db import Database

from realm_backend.ggg import Quarter, QuarterStatus, Realm, RealmStatus, Codex


@pytest.fixture(autouse=True)
def clean_db():
    """Clear the database before each test."""
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


class TestQuarterEntity:
    """Tests for the Quarter entity."""

    def test_quarter_creation(self):
        """Test creating a Quarter with required fields."""
        q = Quarter(name="North", canister_id="abc-123-def")
        assert q.name == "North"
        assert q.canister_id == "abc-123-def"

    def test_quarter_default_status(self):
        """Test that Quarter defaults to active status."""
        q = Quarter(name="South")
        assert q.status == QuarterStatus.ACTIVE

    def test_quarter_default_population(self):
        """Test that Quarter population defaults to 0."""
        q = Quarter(name="East")
        assert q.population == 0

    def test_quarter_status_values(self):
        """Test QuarterStatus enum-like values."""
        assert QuarterStatus.ACTIVE == "active"
        assert QuarterStatus.SUSPENDED == "suspended"
        assert QuarterStatus.SPLITTING == "splitting"
        assert QuarterStatus.MERGING == "merging"

    def test_quarter_custom_status(self):
        """Test setting a custom status on Quarter."""
        q = Quarter(name="West", status=QuarterStatus.SPLITTING)
        assert q.status == "splitting"


class TestRealmFederationFields:
    """Tests for the federation fields added to Realm."""

    def test_realm_is_quarter_default_false(self):
        """Test that is_quarter defaults to False (backwards-compatible)."""
        r = Realm(name="Arcadia")
        assert r.is_quarter is False

    def test_realm_federation_realm_id_default_empty(self):
        """Test that federation_realm_id defaults to empty."""
        r = Realm(name="Arcadia")
        assert not r.federation_realm_id

    def test_realm_quarter_ids_default_empty(self):
        """Test that quarter_ids defaults to empty list."""
        r = Realm(name="Arcadia")
        assert len(r.quarter_ids) == 0

    def test_realm_as_quarter(self):
        """Test marking a realm as a quarter."""
        r = Realm(name="North Quarter", is_quarter=True, federation_realm_id="parent-realm-id")
        assert r.is_quarter is True
        assert r.federation_realm_id == "parent-realm-id"

    def test_existing_realm_fields_unaffected(self):
        """Test that existing Realm fields still work after federation additions."""
        r = Realm(
            name="Legacy Realm",
            description="Existing realm",
            status=RealmStatus.ALPHA,
        )
        assert r.name == "Legacy Realm"
        assert r.description == "Existing realm"
        assert r.status == RealmStatus.ALPHA


class TestQuarterRealmRelationship:
    """Tests for Quarter <-> Realm federation relationship."""

    def test_quarter_federation_link(self):
        """Test linking a Quarter to a Realm via federation."""
        realm = Realm(name="Arcadia")
        quarter = Quarter(name="North", canister_id="abc-123")
        quarter.federation = realm
        assert quarter.federation == realm
        assert quarter in realm.quarter_ids

    def test_multiple_quarters_under_realm(self):
        """Test multiple quarters under a single realm."""
        realm = Realm(name="Arcadia")
        q1 = Quarter(name="North", canister_id="can-1")
        q2 = Quarter(name="South", canister_id="can-2")
        q3 = Quarter(name="Central", canister_id="can-3")
        realm.quarter_ids = [q1, q2, q3]
        assert len(realm.quarter_ids) == 3
        assert q1.federation == realm
        assert q2.federation == realm
        assert q3.federation == realm

    def test_single_quarter_realm_backwards_compatible(self):
        """Test that a realm with no quarters is backwards-compatible."""
        realm = Realm(name="Standalone")
        assert realm.is_quarter is False
        assert len(realm.quarter_ids) == 0
        assert not realm.federation_realm_id


class TestFederationCodex:
    """Tests for federation codex relationship."""

    def test_realm_federation_codex_link(self):
        """Test linking a federation codex to a realm."""
        realm = Realm(name="Arcadia")
        codex = Codex(name="federation_codex")
        realm.federation_codex = codex
        assert realm.federation_codex == codex
        assert codex.federation == realm

    def test_realm_without_federation_codex(self):
        """Test that realm without federation codex works (single-quarter mode)."""
        realm = Realm(name="Solo Realm")
        assert realm.federation_codex is None


class TestGGGExports:
    """Tests that Quarter is properly exported from the GGG module."""

    def test_quarter_importable_from_ggg(self):
        """Test that Quarter can be imported from ggg."""
        from realm_backend.ggg import Quarter as Q
        assert Q is Quarter

    def test_quarter_status_importable_from_ggg(self):
        """Test that QuarterStatus can be imported from ggg."""
        from realm_backend.ggg import QuarterStatus as QS
        assert QS is QuarterStatus

    def test_quarter_in_classes(self):
        """Test that Quarter appears in GGG entity classes list."""
        from realm_backend.ggg import classes
        entity_classes = classes()
        assert "Quarter" in entity_classes

    def test_quarter_status_not_in_classes(self):
        """Test that QuarterStatus (helper type) is excluded from entity classes list."""
        from realm_backend.ggg import classes
        entity_classes = classes()
        assert "QuarterStatus" not in entity_classes
