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

# Global litigation storage - will be populated by demo_loader
LITIGATION_STORAGE = [
    {
        "id": "lit_100",
        "requester_principal": "by6od-j4aaa-aaaah-qcaiq-cai",
        "defendant_principal": "bw4dl-smaaa-aaaah-qcaiq-cai",
        "case_title": "Governance Dispute",
        "description": "Challenge to administrative decisions",
        "status": "appealed",
        "requested_at": "2025-07-04T08:52:58.901560Z",
        "verdict": "transfer(requester_principal, defendant_principal, 200, 'Counter-claim settlement')",
        "actions_taken": [
            "verdict_rendered",
            "appeal_filed",
            "review_pending"
        ]
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "warning_issued",
            "monitoring_period"
        ]
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
        "actions_taken": []
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "verdict_rendered",
            "case_closed"
        ]
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
        "actions_taken": []
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
        "actions_taken": [
            "warning_issued",
            "monitoring_period"
        ]
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
        "actions_taken": [
            "verdict_rendered",
            "appeal_filed",
            "review_pending"
        ]
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
        "actions_taken": []
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "investigation_completed",
            "case_dismissed"
        ]
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
        "actions_taken": [
            "settlement_negotiated",
            "agreement_reached"
        ]
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "investigation_completed",
            "verdict_rendered"
        ]
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
        "actions_taken": []
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "settlement_negotiated",
            "agreement_reached"
        ]
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
        "actions_taken": [
            "settlement_negotiated",
            "agreement_reached"
        ]
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
        "actions_taken": [
            "investigation_completed",
            "verdict_rendered"
        ]
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
        "actions_taken": [
            "transfer_executed",
            "case_closed"
        ]
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
        "actions_taken": [
            "initial_review",
            "evidence_collected"
        ]
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
        "actions_taken": [
            "verdict_rendered",
            "case_closed"
        ]
    }
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
            filtered_litigations = LITIGATION_STORAGE
        else:
            # For demo purposes, show all cases to any authenticated user
            # In production, this would filter by user_principal
            filtered_litigations = LITIGATION_STORAGE

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
            "id": f"lit_{len(LITIGATION_STORAGE) + 1:03d}",
            "requester_principal": requester_principal,
            "defendant_principal": defendant_principal,
            "case_title": case_title,
            "description": description,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "verdict": None,
            "actions_taken": [],
        }

        LITIGATION_STORAGE.append(new_litigation)

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
        for lit in LITIGATION_STORAGE:
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


def load_demo_litigations(args: str) -> str:
    """Load demo litigation data - called by demo_loader extension"""
    logger.info(f"justice_litigation.load_demo_litigations called with args: {args}")
    
    try:
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}
        
        demo_cases = params.get("cases", [])
        
        if not demo_cases:
            return json.dumps({"success": False, "error": "No demo cases provided"})
        
        # Clear existing storage and load demo cases
        global LITIGATION_STORAGE
        LITIGATION_STORAGE.clear()
        LITIGATION_STORAGE.extend(demo_cases)
        
        logger.info(f"Loaded {len(demo_cases)} demo litigation cases")
        
        return json.dumps({
            "success": True,
            "message": f"Successfully loaded {len(demo_cases)} demo litigation cases",
            "data": {
                "total_loaded": len(demo_cases),
                "storage_size": len(LITIGATION_STORAGE)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in load_demo_litigations: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
