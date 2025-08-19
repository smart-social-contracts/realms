"""
Voting Extension Backend Entry Point
Placeholder implementation for governance voting system
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List

# Dummy data for development
DUMMY_PROPOSALS = [
    {
        "id": "prop_001",
        "title": "Increase Transaction Fees",
        "description": "Proposal to increase transaction fees by 0.1%",
        "code_url": "https://github.com/example/proposal-001.py",
        "code_checksum": "sha256:a1b2c3d4e5f6...",
        "proposer": "alice.principal",
        "status": "voting",
        "created_at": "2024-01-15T10:00:00Z",
        "voting_deadline": "2024-01-22T10:00:00Z",
        "votes": {"yes": 15, "no": 3, "abstain": 2},
        "total_voters": 20,
        "required_threshold": 0.6,
    },
    {
        "id": "prop_002",
        "title": "Update Governance Rules",
        "description": "Modify voting threshold requirements",
        "code_url": "https://github.com/example/proposal-002.py",
        "code_checksum": "sha256:f6e5d4c3b2a1...",
        "proposer": "bob.principal",
        "status": "pending_vote",
        "created_at": "2024-01-16T14:30:00Z",
        "voting_deadline": None,
        "votes": {"yes": 0, "no": 0, "abstain": 0},
        "total_voters": 0,
        "required_threshold": 0.6,
    },
]


def get_proposals(args: str) -> Dict[str, Any]:
    """Get all proposals with optional filtering"""
    try:
        # Parse JSON string to dictionary
        if isinstance(args, str):
            args_dict = json.loads(args) if args.strip() else {}
        else:
            args_dict = args

        status_filter = args_dict.get("status", None)
        proposals = DUMMY_PROPOSALS

        if status_filter:
            proposals = [p for p in proposals if p["status"] == status_filter]

        return json.dumps(
            {"success": True, "data": {"proposals": proposals, "total": len(proposals)}}
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def get_proposal(args: str) -> Dict[str, Any]:
    """Get a specific proposal by ID"""
    try:
        # Parse JSON string to dictionary
        if isinstance(args, str):
            args_dict = json.loads(args) if args.strip() else {}
        else:
            args_dict = args

        proposal_id = args_dict.get("proposal_id")
        if not proposal_id:
            return json.dumps({"success": False, "error": "proposal_id is required"})

        proposal = next((p for p in DUMMY_PROPOSALS if p["id"] == proposal_id), None)
        if not proposal:
            return json.dumps({"success": False, "error": "Proposal not found"})

        return json.dumps({"success": True, "data": proposal})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def submit_proposal(args: str) -> Dict[str, Any]:
    """Submit a new proposal"""
    try:
        # Parse JSON string to dictionary
        if isinstance(args, str):
            args_dict = json.loads(args) if args.strip() else {}
        else:
            args_dict = args

        required_fields = ["title", "description", "code_url", "proposer"]
        for field in required_fields:
            if field not in args_dict:
                return json.dumps({"success": False, "error": f"{field} is required"})

        # Generate checksum placeholder
        code_checksum = f"sha256:{hashlib.sha256(args_dict['code_url'].encode()).hexdigest()[:16]}..."

        new_proposal = {
            "id": f"prop_{len(DUMMY_PROPOSALS) + 1:03d}",
            "title": args_dict["title"],
            "description": args_dict["description"],
            "code_url": args_dict["code_url"],
            "code_checksum": code_checksum,
            "proposer": args_dict["proposer"],
            "status": "pending_review",
            "created_at": datetime.now().isoformat() + "Z",
            "voting_deadline": None,
            "votes": {"yes": 0, "no": 0, "abstain": 0},
            "total_voters": 0,
            "required_threshold": 0.6,
        }

        return json.dumps({"success": True, "data": new_proposal})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cast_vote(args: str) -> Dict[str, Any]:
    """Cast a vote on a proposal"""
    try:
        # Parse JSON string to dictionary
        if isinstance(args, str):
            args_dict = json.loads(args) if args.strip() else {}
        else:
            args_dict = args

        proposal_id = args_dict.get("proposal_id")
        vote = args_dict.get("vote")  # 'yes', 'no', 'abstain'
        voter = args_dict.get("voter")

        if not all([proposal_id, vote, voter]):
            return json.dumps(
                {"success": False, "error": "proposal_id, vote, and voter are required"}
            )

        if vote not in ["yes", "no", "abstain"]:
            return json.dumps(
                {"success": False, "error": "vote must be 'yes', 'no', or 'abstain'"}
            )

        return json.dumps(
            {"success": True, "data": {"message": "Vote cast successfully"}}
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# Extension API endpoints
EXTENSION_FUNCTIONS = {
    "get_proposals": get_proposals,
    "get_proposal": get_proposal,
    "submit_proposal": submit_proposal,
    "cast_vote": cast_vote,
}
