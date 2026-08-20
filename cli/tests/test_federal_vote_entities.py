"""Declarative and in-memory tests for federal vote GGG entities (issue #300)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend"))

from ic_python_db import Database

from realm_backend.ggg import (
    FederalVote,
    FederalVoteLeg,
    LEG_STATUS_OPEN,
    VOTE_STATUS_OPEN,
    classes,
)
from realm_backend.ggg.governance.federal_vote import (
    LEG_STATUS_ARMED,
    LEG_STATUS_OPEN,
    VOTE_STATUS_OPEN,
)


@pytest.fixture(autouse=True)
def clean_db():
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


class TestFederalVoteEntity:
    def test_defaults(self):
        vote = FederalVote(
            vote_id="fv-1",
            origin_quarter="q-origin",
            action='{"type":"noop"}',
            rule_json='{"mode":"per_quarter"}',
            vote_hash="sha256:" + "a" * 64,
        )
        assert vote.deadline == 0
        assert vote.status == VOTE_STATUS_OPEN
        assert vote.tally_json == ""
        assert vote.known_quarters == 0

    def test_alias_is_vote_id(self):
        assert FederalVote.__alias__ == "vote_id"

    def test_status_is_indexed(self):
        indexed = FederalVote._indexed_properties()
        assert "status" in indexed
        assert indexed["status"].indexed is True


class TestFederalVoteLegEntity:
    def test_defaults(self):
        leg = FederalVoteLeg(
            leg_key="fv-1:quarter-canister",
            vote_id="fv-1",
            quarter_canister_id="quarter-canister",
        )
        assert leg.proposal_id == ""
        assert leg.outcome == ""
        assert leg.votes_yes == 0
        assert leg.votes_no == 0
        assert leg.votes_abstain == 0
        assert leg.eligible == 0
        assert leg.reported is False
        assert leg.status == LEG_STATUS_OPEN
        assert leg.vote_hash == ""
        assert leg.error == ""

    def test_alias_is_leg_key(self):
        assert FederalVoteLeg.__alias__ == "leg_key"

    def test_vote_id_and_status_are_indexed(self):
        indexed = FederalVoteLeg._indexed_properties()
        assert "vote_id" in indexed
        assert indexed["vote_id"].indexed is True
        assert "status" in indexed
        assert indexed["status"].indexed is True


class TestGGGExports:
    def test_importable_from_ggg_package_path(self):
        from ggg import FederalVote as Vote, FederalVoteLeg as Leg

        assert Vote.__name__ == "FederalVote"
        assert Leg.__name__ == "FederalVoteLeg"
        assert Vote.__alias__ == "vote_id"
        assert Leg.__alias__ == "leg_key"

    def test_entities_in_classes(self):
        entity_classes = classes()
        assert "FederalVote" in entity_classes
        assert "FederalVoteLeg" in entity_classes

    def test_status_constants_not_in_classes(self):
        entity_classes = classes()
        for name in (
            "VOTE_STATUS_OPEN",
            "VOTE_STATUS_ADOPTED",
            "LEG_STATUS_OPEN",
            "LEG_STATUS_ARMED",
        ):
            assert name not in entity_classes
