"""
Justice Litigation extension entry point
"""

import json
import traceback
from datetime import datetime
from typing import Any, Dict

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("extensions.justice_litigation")

DUMMY_LITIGATIONS = [
    {
        "id": "lit_001",
        "requester_principal": "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "defendant_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "case_title": "Contract Breach Dispute",
        "description": "Defendant failed to deliver goods as per smart contract agreement",
        "status": "pending",
        "requested_at": "2025-06-20T10:30:00Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_001b",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "case_title": "Contract Breach Dispute",
        "description": "Defendant failed to deliver goods as per smart contract agreement",
        "status": "pending",
        "requested_at": "2025-06-20T10:30:00Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_002",
        "requester_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "case_title": "Payment Dispute",
        "description": "Disagreement over payment terms and late fees",
        "status": "in_review",
        "requested_at": "2025-06-18T14:15:00Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_003",
        "requester_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "defendant_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "case_title": "Asset Transfer Violation",
        "description": "Unauthorized transfer of realm assets without proper authorization",
        "status": "resolved",
        "requested_at": "2025-06-15T09:45:00Z",
        "verdict": "transfer(defendant_principal, requester_principal, 1000, 'Compensation for unauthorized transfer')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_004",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "case_title": "Service Agreement Breach",
        "description": "Service provider failed to meet agreed upon deliverables",
        "status": "resolved",
        "requested_at": "2025-06-12T16:20:00Z",
        "verdict": "transfer(defendant_principal, requester_principal, 500, 'Partial refund for incomplete services')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
]


def get_litigations(args: str) -> str:
    """Get litigation records - all for admin, user's own for citizens"""
    logger.info(f"justice_litigation.get_litigations called with args: {args}")

    try:
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        user_principal = params.get("user_principal")
        user_profile = params.get("user_profile", "member")

        if not user_principal:
            return json.dumps(
                {"success": False, "error": "user_principal parameter is required"}
            )

        if user_profile == "admin":
            filtered_litigations = DUMMY_LITIGATIONS
        else:
            filtered_litigations = [
                lit
                for lit in DUMMY_LITIGATIONS
                if lit["requester_principal"] == user_principal
            ]

        return json.dumps(
            {
                "success": True,
                "data": {
                    "litigations": filtered_litigations,
                    "total_count": len(filtered_litigations),
                    "user_profile": user_profile,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in get_litigations: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def create_litigation(args: str) -> str:
    """Create a new litigation request"""
    logger.info(f"justice_litigation.create_litigation called with args: {args}")

    try:
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        requester_principal = params.get("requester_principal")
        defendant_principal = params.get("defendant_principal")
        case_title = params.get("case_title")
        description = params.get("description")

        if not all([requester_principal, defendant_principal, case_title, description]):
            return json.dumps(
                {
                    "success": False,
                    "error": "requester_principal, defendant_principal, case_title, and description are required",
                }
            )

        new_litigation = {
            "id": f"lit_{len(DUMMY_LITIGATIONS) + 1:03d}",
            "requester_principal": requester_principal,
            "defendant_principal": defendant_principal,
            "case_title": case_title,
            "description": description,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "verdict": None,
            "actions_taken": [],
        }

        DUMMY_LITIGATIONS.append(new_litigation)

        return json.dumps(
            {
                "success": True,
                "data": {
                    "litigation": new_litigation,
                    "message": "Litigation created successfully",
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in create_litigation: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def execute_verdict(args: str) -> str:
    """Execute codex verdict for a litigation"""
    logger.info(f"justice_litigation.execute_verdict called with args: {args}")

    try:
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        litigation_id = params.get("litigation_id")
        verdict_code = params.get("verdict_code")
        executor_principal = params.get("executor_principal")

        if not all([litigation_id, verdict_code, executor_principal]):
            return json.dumps(
                {
                    "success": False,
                    "error": "litigation_id, verdict_code, and executor_principal are required",
                }
            )

        litigation = None
        for lit in DUMMY_LITIGATIONS:
            if lit["id"] == litigation_id:
                litigation = lit
                break

        if not litigation:
            return json.dumps(
                {"success": False, "error": f"Litigation {litigation_id} not found"}
            )

        if litigation["status"] == "resolved":
            return json.dumps(
                {"success": False, "error": "Litigation is already resolved"}
            )

        litigation["verdict"] = verdict_code
        litigation["status"] = "resolved"
        litigation["actions_taken"] = ["verdict_executed", "case_closed"]

        executed_actions = []
        if verdict_code and "transfer(" in verdict_code:
            executed_actions.append("Token transfer simulated")
            logger.info(f"Simulated execution of codex: {verdict_code}")

        return json.dumps(
            {
                "success": True,
                "data": {
                    "litigation": litigation,
                    "executed_actions": executed_actions,
                    "message": "Verdict executed successfully",
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in execute_verdict: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
