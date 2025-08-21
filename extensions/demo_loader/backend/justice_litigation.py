"""
Justice Litigation demo data loader
Creates realistic litigation cases for testing and demonstration
"""

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.justice_litigation")

# Sample case types and descriptions
CASE_TYPES = [
    {
        "title": "Contract Breach Dispute",
        "descriptions": [
            "Defendant failed to deliver goods as per smart contract agreement",
            "Service provider did not meet contractual obligations within specified timeframe",
            "Breach of payment terms in commercial agreement",
            "Failure to provide agreed-upon services as outlined in contract",
        ],
    },
    {
        "title": "Payment Dispute",
        "descriptions": [
            "Disagreement over payment terms and late fees",
            "Disputed invoice amounts and billing discrepancies",
            "Non-payment of agreed compensation for services rendered",
            "Overcharging for services beyond agreed scope",
        ],
    },
    {
        "title": "Asset Transfer Violation",
        "descriptions": [
            "Unauthorized transfer of realm assets without proper authorization",
            "Improper handling of digital asset ownership transfer",
            "Violation of asset custody agreements",
            "Unauthorized access and transfer of protected assets",
        ],
    },
    {
        "title": "Service Agreement Breach",
        "descriptions": [
            "Service provider failed to meet agreed upon deliverables",
            "Incomplete or substandard service delivery",
            "Violation of service level agreements",
            "Failure to maintain agreed service quality standards",
        ],
    },
    {
        "title": "Intellectual Property Dispute",
        "descriptions": [
            "Unauthorized use of proprietary algorithms or code",
            "Copyright infringement in digital content creation",
            "Patent violation in smart contract implementation",
            "Trademark misuse in platform branding",
        ],
    },
    {
        "title": "Data Privacy Violation",
        "descriptions": [
            "Unauthorized access to personal user data",
            "Breach of data protection agreements",
            "Improper sharing of confidential information",
            "Violation of privacy consent terms",
        ],
    },
    {
        "title": "Governance Dispute",
        "descriptions": [
            "Disagreement over voting rights and procedures",
            "Challenge to administrative decisions",
            "Dispute over resource allocation policies",
            "Violation of community governance rules",
        ],
    },
    {
        "title": "Employment Dispute",
        "descriptions": [
            "Wrongful termination of service agreement",
            "Dispute over compensation and benefits",
            "Violation of workplace conduct policies",
            "Disagreement over work scope and responsibilities",
        ],
    },
]

# Sample verdicts for resolved cases
SAMPLE_VERDICTS = [
    "transfer(defendant_principal, requester_principal, 1000, 'Compensation for breach of contract')",
    "transfer(defendant_principal, requester_principal, 500, 'Partial refund for incomplete services')",
    "transfer(defendant_principal, requester_principal, 2000, 'Damages for unauthorized asset transfer')",
    "transfer(defendant_principal, requester_principal, 750, 'Settlement for payment dispute')",
    "transfer(defendant_principal, requester_principal, 1500, 'Compensation for intellectual property violation')",
    "transfer(defendant_principal, requester_principal, 300, 'Penalty for data privacy breach')",
    "transfer(requester_principal, defendant_principal, 200, 'Counter-claim settlement')",
    "no_action_required('Case dismissed - insufficient evidence')",
    "mediation_required('Parties must engage in mediation process')",
    "warning_issued('Formal warning issued to defendant')",
]

# Sample actions taken for cases
ACTIONS_TAKEN = [
    ["initial_review", "evidence_collected"],
    ["mediation_attempted", "expert_consultation"],
    ["transfer_executed", "case_closed"],
    ["warning_issued", "monitoring_period"],
    ["settlement_negotiated", "agreement_reached"],
    ["investigation_completed", "verdict_rendered"],
    ["appeal_filed", "review_pending"],
    ["compliance_check", "resolution_verified"],
]


def generate_litigation_cases(num_cases: int = 25) -> List[Dict[str, Any]]:
    """Generate realistic litigation cases with various statuses and types"""

    # Sample principals (these should match existing users in the system)
    sample_principals = [
        "zstof-mh46j-ewupb-oxihp-j5cpv-d5d7p-6o6i4-spm3c-54ho5-meqol-xqe",
        "rrkah-fqaaa-aaaah-qcaiq-cai",
        "rdmx6-jaaaa-aaaah-qcaiq-cai",
        "be2us-64aaa-aaaah-qcaiq-cai",
        "bkyz2-fmaaa-aaaah-qcaiq-cai",
        "br5f7-7uaaa-aaaah-qcaiq-cai",
        "bw4dl-smaaa-aaaah-qcaiq-cai",
        "by6od-j4aaa-aaaah-qcaiq-cai",
        "c5kvi-uuaaa-aaaah-qcaiq-cai",
        "cbopz-duaaa-aaaah-qcaiq-cai",
    ]

    statuses = [
        "pending",
        "in_review",
        "mediation",
        "resolved",
        "dismissed",
        "appealed",
    ]
    status_weights = [
        0.3,
        0.25,
        0.15,
        0.2,
        0.05,
        0.05,
    ]  # More pending and in_review cases

    cases = []
    base_date = datetime.now() - timedelta(days=90)  # Start 90 days ago

    for i in range(num_cases):
        case_type = random.choice(CASE_TYPES)
        status = random.choices(statuses, weights=status_weights)[0]

        # Ensure different principals for requester and defendant
        requester = random.choice(sample_principals)
        defendant = random.choice([p for p in sample_principals if p != requester])

        # Generate case date (more recent cases are more likely)
        days_ago = random.randint(1, 90)
        case_date = base_date + timedelta(days=days_ago)

        case = {
            "id": f"lit_{i+100:03d}",  # Start from lit_100 to avoid conflicts
            "requester_principal": requester,
            "defendant_principal": defendant,
            "case_title": case_type["title"],
            "description": random.choice(case_type["descriptions"]),
            "status": status,
            "requested_at": case_date.isoformat() + "Z",
            "verdict": None,
            "actions_taken": [],
        }

        # Add verdict and actions for resolved cases
        if status in ["resolved", "dismissed"]:
            if status == "resolved":
                case["verdict"] = random.choice(SAMPLE_VERDICTS)
                case["actions_taken"] = (
                    ["transfer_executed", "case_closed"]
                    if "transfer(" in case["verdict"]
                    else ["verdict_rendered", "case_closed"]
                )
            else:
                case["verdict"] = (
                    "no_action_required('Case dismissed - insufficient evidence')"
                )
                case["actions_taken"] = ["investigation_completed", "case_dismissed"]
        elif status in ["in_review", "mediation"]:
            case["actions_taken"] = random.choice(ACTIONS_TAKEN[:6])  # Partial actions
        elif status == "appealed":
            case["verdict"] = random.choice(SAMPLE_VERDICTS)
            case["actions_taken"] = [
                "verdict_rendered",
                "appeal_filed",
                "review_pending",
            ]

        cases.append(case)

    return cases


def run(batch: int = None) -> str:
    """Load justice litigation demo data"""
    try:
        logger.info("Starting justice litigation demo data creation")

        # Generate litigation cases
        litigation_cases = generate_litigation_cases(25)

        logger.info(f"Generated {len(litigation_cases)} litigation cases")

        # Direct integration: Import and populate the justice_litigation storage
        try:
            # Import the justice_litigation module directly to populate its storage
            import os
            import sys

            # Get the path to the justice_litigation extension
            justice_litigation_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "justice_litigation", "backend"
            )

            if os.path.exists(justice_litigation_path):
                sys.path.insert(0, justice_litigation_path)

                # Import and directly populate the litigation storage
                import entry as justice_litigation_entry

                # Clear existing storage and add our demo cases
                justice_litigation_entry.LITIGATION_STORAGE.clear()
                justice_litigation_entry.LITIGATION_STORAGE.extend(litigation_cases)

                logger.info(
                    f"Successfully loaded {len(litigation_cases)} cases into justice_litigation storage"
                )

            else:
                logger.warning(
                    f"Justice litigation path not found: {justice_litigation_path}"
                )

        except Exception as integration_error:
            logger.warning(f"Direct integration failed: {integration_error}")
            logger.info(
                "Demo cases generated but not loaded - use manual loading process"
            )

        # Summary statistics
        status_counts = {}
        for case in litigation_cases:
            status = case["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        case_type_counts = {}
        for case in litigation_cases:
            case_type = case["case_title"]
            case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1

        result = {
            "success": True,
            "message": f"Successfully generated and loaded {len(litigation_cases)} litigation cases",
            "statistics": {
                "total_cases": len(litigation_cases),
                "status_distribution": status_counts,
                "case_type_distribution": case_type_counts,
                "date_range": {
                    "earliest": min(case["requested_at"] for case in litigation_cases),
                    "latest": max(case["requested_at"] for case in litigation_cases),
                },
            },
            "sample_cases": litigation_cases[:3],  # Include first 3 cases as examples
        }

        logger.info(
            f"Justice litigation demo data creation completed: {result['statistics']}"
        )
        return json.dumps(result, indent=2)

    except Exception as e:
        error_msg = f"Error creating justice litigation demo data: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})
