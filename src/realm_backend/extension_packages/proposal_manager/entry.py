import json
import math
from typing import Any, Dict

from ggg.proposal import Proposal
from ggg.vote import Vote
from kybra_simple_logging import get_logger

logger = get_logger("proposal_manager")


def list_proposals(args: str) -> str:
    """List proposals with pagination"""
    try:
        params = json.loads(args) if args else {}
        page_num = params.get("page_num", 0)
        page_size = params.get("page_size", 10)

        from_id = page_num * page_size + 1
        proposals = Proposal.load_some(from_id=from_id, count=page_size)
        count = Proposal.count()

        result = {
            "success": True,
            "proposals": [p.to_dict() for p in proposals],
            "pagination": {
                "page_num": page_num,
                "page_size": page_size,
                "total_items": count,
                "total_pages": math.ceil(count / page_size) if count > 0 else 0,
            },
        }
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error listing proposals: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def create_proposal(args: str) -> str:
    """Create a new proposal"""
    try:
        params = json.loads(args)

        proposal_metadata = {
            "title": params.get("title", ""),
            "description": params.get("description", ""),
            "author": params.get("author", ""),
            "forum_url": params.get("forum_url", ""),
            "status": "pending_review",
            "vote_counts": {"yes": 0, "no": 0, "abstain": 0, "null": 0},
            "voting_deadline": params.get("voting_deadline", ""),
            "created_by": params.get("created_by", ""),
        }

        proposal = Proposal(metadata=json.dumps(proposal_metadata))
        proposal.save()

        logger.info(f"Created proposal with ID: {proposal.id}")
        return json.dumps(
            {
                "success": True,
                "proposal_id": proposal.id,
                "proposal": proposal.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"Error creating proposal: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def update_proposal(args: str) -> str:
    """Update an existing proposal (admin only)"""
    try:
        params = json.loads(args)
        proposal_id = params.get("proposal_id")

        if not proposal_id:
            return json.dumps({"success": False, "error": "proposal_id is required"})

        proposal = Proposal.load(proposal_id)
        if not proposal:
            return json.dumps({"success": False, "error": "Proposal not found"})

        current_metadata = json.loads(proposal.metadata) if proposal.metadata else {}

        if "title" in params:
            current_metadata["title"] = params["title"]
        if "description" in params:
            current_metadata["description"] = params["description"]
        if "status" in params:
            current_metadata["status"] = params["status"]
        if "voting_deadline" in params:
            current_metadata["voting_deadline"] = params["voting_deadline"]

        current_metadata["updated_by"] = params.get("updated_by", "")

        proposal.metadata = json.dumps(current_metadata)
        proposal.save()

        logger.info(f"Updated proposal with ID: {proposal_id}")
        return json.dumps({"success": True, "proposal": proposal.to_dict()})
    except Exception as e:
        logger.error(f"Error updating proposal: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def delete_proposal(args: str) -> str:
    """Delete a proposal (admin only)"""
    try:
        params = json.loads(args)
        proposal_id = params.get("proposal_id")

        if not proposal_id:
            return json.dumps({"success": False, "error": "proposal_id is required"})

        proposal = Proposal.load(proposal_id)
        if not proposal:
            return json.dumps({"success": False, "error": "Proposal not found"})

        current_metadata = json.loads(proposal.metadata) if proposal.metadata else {}
        current_metadata["status"] = "cancelled"
        current_metadata["cancelled_by"] = params.get("cancelled_by", "")

        proposal.metadata = json.dumps(current_metadata)
        proposal.save()

        logger.info(f"Cancelled proposal with ID: {proposal_id}")
        return json.dumps(
            {"success": True, "message": "Proposal cancelled successfully"}
        )
    except Exception as e:
        logger.error(f"Error cancelling proposal: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def vote_on_proposal(args: str) -> str:
    """Cast a vote on a proposal"""
    try:
        params = json.loads(args)
        proposal_id = params.get("proposal_id")
        vote_value = params.get("vote")
        voter_id = params.get("voter_id")

        if not all([proposal_id, vote_value, voter_id]):
            return json.dumps(
                {
                    "success": False,
                    "error": "proposal_id, vote, and voter_id are required",
                }
            )

        if vote_value not in ["yes", "no", "abstain", "null"]:
            return json.dumps(
                {
                    "success": False,
                    "error": "Invalid vote value. Must be yes, no, abstain, or null",
                }
            )

        proposal = Proposal.load(proposal_id)
        if not proposal:
            return json.dumps({"success": False, "error": "Proposal not found"})

        current_metadata = json.loads(proposal.metadata) if proposal.metadata else {}

        if current_metadata.get("status") != "voting":
            return json.dumps(
                {"success": False, "error": "Proposal is not open for voting"}
            )

        vote_metadata = {
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "vote_value": vote_value,
        }

        vote = Vote(metadata=json.dumps(vote_metadata))
        vote.save()

        vote_counts = current_metadata.get(
            "vote_counts", {"yes": 0, "no": 0, "abstain": 0, "null": 0}
        )
        vote_counts[vote_value] = vote_counts.get(vote_value, 0) + 1
        current_metadata["vote_counts"] = vote_counts

        proposal.metadata = json.dumps(current_metadata)
        proposal.save()

        logger.info(f"Vote cast on proposal {proposal_id}: {vote_value} by {voter_id}")
        return json.dumps(
            {"success": True, "vote_id": vote.id, "updated_counts": vote_counts}
        )
    except Exception as e:
        logger.error(f"Error voting on proposal: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_proposal_details(args: str) -> str:
    """Get detailed information about a specific proposal"""
    try:
        params = json.loads(args)
        proposal_id = params.get("proposal_id")

        if not proposal_id:
            return json.dumps({"success": False, "error": "proposal_id is required"})

        proposal = Proposal.load(proposal_id)
        if not proposal:
            return json.dumps({"success": False, "error": "Proposal not found"})

        proposal_dict = proposal.to_dict()
        metadata = json.loads(proposal.metadata) if proposal.metadata else {}
        proposal_dict["parsed_metadata"] = metadata

        from_id = 1
        votes = Vote.load_some(from_id=from_id, count=1000)
        proposal_votes = []
        for vote in votes:
            vote_metadata = json.loads(vote.metadata) if vote.metadata else {}
            if vote_metadata.get("proposal_id") == proposal_id:
                proposal_votes.append(
                    {
                        "id": vote.id,
                        "voter_id": vote_metadata.get("voter_id"),
                        "vote_value": vote_metadata.get("vote_value"),
                        "created_at": (
                            vote.created_at if hasattr(vote, "created_at") else None
                        ),
                    }
                )

        result = {"success": True, "proposal": proposal_dict, "votes": proposal_votes}
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error getting proposal details: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
