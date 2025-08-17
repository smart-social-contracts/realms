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
LITIGATION_STORAGE = []


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
            filtered_litigations = [
                lit
                for lit in LITIGATION_STORAGE
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
