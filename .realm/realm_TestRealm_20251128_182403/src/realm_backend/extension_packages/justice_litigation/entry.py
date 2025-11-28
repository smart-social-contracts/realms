"""
Justice Litigation extension entry point
"""

import json
import traceback
from datetime import datetime
from typing import Any, Dict

from ggg import Dispute, User
from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("extensions.justice_litigation")


def _dispute_to_dict(dispute: Dispute) -> Dict[str, Any]:
    """Convert Dispute entity to dictionary format"""
    # Parse actions_taken JSON string to list
    actions_taken = json.loads(dispute.actions_taken) if dispute.actions_taken else []

    # Handle timestamp - it could be string or datetime object
    timestamp = dispute.timestamp_created
    if hasattr(timestamp, "strftime"):
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        timestamp_str = str(timestamp) if timestamp else ""

    return {
        "id": dispute.dispute_id,
        "requester_principal": dispute.requester.id if dispute.requester else "unknown",
        "defendant_principal": dispute.defendant.id if dispute.defendant else "unknown",
        "case_title": dispute.case_title,
        "description": dispute.description,
        "status": dispute.status,
        "requested_at": timestamp_str,
        "verdict": dispute.verdict if dispute.verdict else None,
        "actions_taken": actions_taken,
    }


# Removed hardcoded litigation storage - now using database
_REMOVED_LITIGATION_STORAGE = [
    {
        "id": "lit_100",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Governance Dispute",
        "description": "Challenge to administrative decisions",
        "status": "appealed",
        "requested_at": "2025-07-04T08:52:58.901560Z",
        "verdict": "transfer(requester_principal, defendant_principal, 200, 'Counter-claim settlement')",
        "actions_taken": ["verdict_rendered", "appeal_filed", "review_pending"],
    },
    {
        "id": "lit_101",
        "requester_principal": "bkyz2-fmaaa-aaaah-qcaiq-cai",
        "defendant_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "case_title": "Governance Dispute",
        "description": "Violation of community governance rules",
        "status": "resolved",
        "requested_at": "2025-06-16T08:52:58.901560Z",
        "verdict": "transfer(requester_principal, defendant_principal, 200, 'Counter-claim settlement')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_102",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "case_title": "Data Privacy Violation",
        "description": "Violation of privacy consent terms",
        "status": "resolved",
        "requested_at": "2025-07-05T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 1000, 'Compensation for breach of contract')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_103",
        "requester_principal": "cbopz-duaaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Data Privacy Violation",
        "description": "Unauthorized access to personal user data",
        "status": "mediation",
        "requested_at": "2025-08-13T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["warning_issued", "monitoring_period"],
    },
    {
        "id": "lit_104",
        "requester_principal": "br5f7-7uaaa-aaaah-qcaiq-cai",
        "defendant_principal": "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "case_title": "Employment Dispute",
        "description": "Dispute over compensation and benefits",
        "status": "pending",
        "requested_at": "2025-07-26T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_105",
        "requester_principal": "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "defendant_principal": "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "case_title": "Payment Dispute",
        "description": "Overcharging for services beyond agreed scope",
        "status": "resolved",
        "requested_at": "2025-06-17T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 500, 'Partial refund for incomplete services')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_106",
        "requester_principal": "bkyz2-fmaaa-aaaah-qcaiq-cai",
        "defendant_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "case_title": "Asset Transfer Violation",
        "description": "Violation of asset custody agreements",
        "status": "resolved",
        "requested_at": "2025-08-16T08:52:58.901560Z",
        "verdict": "no_action_required('Case dismissed - insufficient evidence')",
        "actions_taken": ["verdict_rendered", "case_closed"],
    },
    {
        "id": "lit_107",
        "requester_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "defendant_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "case_title": "Intellectual Property Dispute",
        "description": "Patent violation in smart contract implementation",
        "status": "pending",
        "requested_at": "2025-06-29T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_108",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "case_title": "Intellectual Property Dispute",
        "description": "Patent violation in smart contract implementation",
        "status": "mediation",
        "requested_at": "2025-07-09T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["warning_issued", "monitoring_period"],
    },
    {
        "id": "lit_109",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "br5f7-7uaaa-aaaah-qcaiq-cai",
        "case_title": "Intellectual Property Dispute",
        "description": "Trademark misuse in platform branding",
        "status": "appealed",
        "requested_at": "2025-05-31T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 500, 'Partial refund for incomplete services')",
        "actions_taken": ["verdict_rendered", "appeal_filed", "review_pending"],
    },
    {
        "id": "lit_110",
        "requester_principal": "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "defendant_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "case_title": "Payment Dispute",
        "description": "Non-payment of agreed compensation for services rendered",
        "status": "pending",
        "requested_at": "2025-08-09T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_111",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "br5f7-7uaaa-aaaah-qcaiq-cai",
        "case_title": "Asset Transfer Violation",
        "description": "Unauthorized access and transfer of protected assets",
        "status": "resolved",
        "requested_at": "2025-06-24T08:52:58.901560Z",
        "verdict": "transfer(requester_principal, defendant_principal, 200, 'Counter-claim settlement')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_112",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "cbopz-duaaa-aaaah-qcaiq-cai",
        "case_title": "Contract Breach Dispute",
        "description": "Defendant failed to deliver goods as per smart contract agreement",
        "status": "dismissed",
        "requested_at": "2025-07-31T08:52:58.901560Z",
        "verdict": "no_action_required('Case dismissed - insufficient evidence')",
        "actions_taken": ["investigation_completed", "case_dismissed"],
    },
    {
        "id": "lit_113",
        "requester_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Employment Dispute",
        "description": "Dispute over compensation and benefits",
        "status": "mediation",
        "requested_at": "2025-08-10T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["settlement_negotiated", "agreement_reached"],
    },
    {
        "id": "lit_114",
        "requester_principal": "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "defendant_principal": "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "case_title": "Service Agreement Breach",
        "description": "Incomplete or substandard service delivery",
        "status": "in_review",
        "requested_at": "2025-06-13T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_115",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "cbopz-duaaa-aaaah-qcaiq-cai",
        "case_title": "Contract Breach Dispute",
        "description": "Failure to provide agreed-upon services as outlined in contract",
        "status": "in_review",
        "requested_at": "2025-06-17T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["investigation_completed", "verdict_rendered"],
    },
    {
        "id": "lit_116",
        "requester_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "defendant_principal": "be2us-64aaa-aaaah-qcaiq-cai",
        "case_title": "Data Privacy Violation",
        "description": "Breach of data protection agreements",
        "status": "pending",
        "requested_at": "2025-07-31T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": [],
    },
    {
        "id": "lit_117",
        "requester_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Intellectual Property Dispute",
        "description": "Patent violation in smart contract implementation",
        "status": "resolved",
        "requested_at": "2025-06-03T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 2000, 'Damages for unauthorized asset transfer')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_118",
        "requester_principal": "cbopz-duaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "case_title": "Intellectual Property Dispute",
        "description": "Unauthorized use of proprietary algorithms or code",
        "status": "resolved",
        "requested_at": "2025-07-10T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 2000, 'Damages for unauthorized asset transfer')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_119",
        "requester_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "case_title": "Governance Dispute",
        "description": "Disagreement over voting rights and procedures",
        "status": "in_review",
        "requested_at": "2025-07-25T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["settlement_negotiated", "agreement_reached"],
    },
    {
        "id": "lit_120",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "case_title": "Contract Breach Dispute",
        "description": "Breach of payment terms in commercial agreement",
        "status": "in_review",
        "requested_at": "2025-07-20T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["settlement_negotiated", "agreement_reached"],
    },
    {
        "id": "lit_121",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "case_title": "Asset Transfer Violation",
        "description": "Unauthorized transfer of realm assets without proper authorization",
        "status": "in_review",
        "requested_at": "2025-06-27T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["investigation_completed", "verdict_rendered"],
    },
    {
        "id": "lit_122",
        "requester_principal": "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Governance Dispute",
        "description": "Dispute over resource allocation policies",
        "status": "resolved",
        "requested_at": "2025-08-11T08:52:58.901560Z",
        "verdict": "transfer(defendant_principal, requester_principal, 500, 'Partial refund for incomplete services')",
        "actions_taken": ["transfer_executed", "case_closed"],
    },
    {
        "id": "lit_123",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Payment Dispute",
        "description": "Non-payment of agreed compensation for services rendered",
        "status": "in_review",
        "requested_at": "2025-08-08T08:52:58.901560Z",
        "verdict": None,
        "actions_taken": ["initial_review", "evidence_collected"],
    },
    {
        "id": "lit_124",
        "requester_principal": "bkyz2-fmaaa-aaaah-qcaiq-cai",
        "defendant_principal": "rrkah-fqaaa-aaaah-qcaiq-cai",
        "case_title": "Service Agreement Breach",
        "description": "Violation of service level agreements",
        "status": "resolved",
        "requested_at": "2025-06-26T08:52:58.901560Z",
        "verdict": "mediation_required('Parties must engage in mediation process')",
        "actions_taken": ["verdict_rendered", "case_closed"],
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

        # Get all disputes from database
        all_disputes = Dispute.instances()

        # Convert to dict format
        filtered_litigations = [_dispute_to_dict(d) for d in all_disputes]

        # For non-admin users, could filter by user_principal here
        # For now, showing all disputes to all users for demo purposes
        if user_profile != "admin":
            # Filter to show only disputes where user is involved
            filtered_litigations = [
                d
                for d in filtered_litigations
                if d["requester_principal"] == user_principal
                or d["defendant_principal"] == user_principal
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

        # Find requester and defendant users
        requester_user = None
        defendant_user = None
        for u in User.instances():
            if u.id == requester_principal:
                requester_user = u
            if u.id == defendant_principal:
                defendant_user = u

        # Generate dispute ID
        existing_disputes = Dispute.instances()
        dispute_id = f"lit_{len(existing_disputes) + 1:03d}"

        # Create Dispute entity
        new_dispute = Dispute(
            dispute_id=dispute_id,
            requester=requester_user,
            defendant=defendant_user,
            case_title=case_title,
            description=description,
            status="pending",
            verdict="",
            actions_taken="[]",  # Empty JSON array
            metadata="{}",
        )

        new_litigation = _dispute_to_dict(new_dispute)

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

        # Find dispute in database
        dispute = None
        for d in Dispute.instances():
            if d.dispute_id == litigation_id:
                dispute = d
                break

        if not dispute:
            return json.dumps(
                {"success": False, "error": f"Litigation {litigation_id} not found"}
            )

        if dispute.status == "resolved":
            return json.dumps(
                {"success": False, "error": "Litigation is already resolved"}
            )

        # Update dispute
        dispute.verdict = verdict_code
        dispute.status = "resolved"
        dispute.actions_taken = json.dumps(["verdict_executed", "case_closed"])
        dispute.save()

        executed_actions = []
        if verdict_code and "transfer(" in verdict_code:
            executed_actions.append("Token transfer simulated")
            logger.info(f"Simulated execution of codex: {verdict_code}")

        litigation = _dispute_to_dict(dispute)

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


def load_demo_litigations(args: str) -> str:
    """
    DEPRECATED: Load demo litigation data - no longer needed

    Litigation data is now automatically loaded from extensions/justice_litigation/data/*.json
    during realm deployment via the automatic extension data loading feature.
    """
    logger.info(f"justice_litigation.load_demo_litigations called (DEPRECATED)")

    # Get current count from database
    disputes_count = len(Dispute.instances())

    return json.dumps(
        {
            "success": True,
            "message": f"Litigation data is now loaded from database. Current count: {disputes_count}",
            "data": {
                "total_loaded": disputes_count,
                "storage_size": disputes_count,
                "note": "This function is deprecated. Use automatic data loading instead.",
            },
        }
    )
