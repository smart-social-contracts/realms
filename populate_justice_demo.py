#!/usr/bin/env python3
"""
Direct demo data population script for Justice Litigation extension
Generates and inserts demo litigation cases directly into the extension backend
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Sample case types and descriptions
CASE_TYPES = [
    {
        "title": "Contract Breach Dispute",
        "descriptions": [
            "Defendant failed to deliver goods as per smart contract agreement",
            "Service provider did not meet contractual obligations within specified timeframe",
            "Breach of payment terms in commercial agreement",
            "Failure to provide agreed-upon services as outlined in contract"
        ]
    },
    {
        "title": "Payment Dispute",
        "descriptions": [
            "Disagreement over payment terms and late fees",
            "Disputed invoice amounts and billing discrepancies",
            "Non-payment of agreed compensation for services rendered",
            "Overcharging for services beyond agreed scope"
        ]
    },
    {
        "title": "Asset Transfer Violation",
        "descriptions": [
            "Unauthorized transfer of realm assets without proper authorization",
            "Improper handling of digital asset ownership transfer",
            "Violation of asset custody agreements",
            "Unauthorized access and transfer of protected assets"
        ]
    },
    {
        "title": "Service Agreement Breach",
        "descriptions": [
            "Service provider failed to meet agreed upon deliverables",
            "Incomplete or substandard service delivery",
            "Violation of service level agreements",
            "Failure to maintain agreed service quality standards"
        ]
    },
    {
        "title": "Intellectual Property Dispute",
        "descriptions": [
            "Unauthorized use of proprietary algorithms or code",
            "Copyright infringement in digital content creation",
            "Patent violation in smart contract implementation",
            "Trademark misuse in platform branding"
        ]
    },
    {
        "title": "Data Privacy Violation",
        "descriptions": [
            "Unauthorized access to personal user data",
            "Breach of data protection agreements",
            "Improper sharing of confidential information",
            "Violation of privacy consent terms"
        ]
    },
    {
        "title": "Governance Dispute",
        "descriptions": [
            "Disagreement over voting rights and procedures",
            "Challenge to administrative decisions",
            "Dispute over resource allocation policies",
            "Violation of community governance rules"
        ]
    },
    {
        "title": "Employment Dispute",
        "descriptions": [
            "Wrongful termination of service agreement",
            "Dispute over compensation and benefits",
            "Violation of workplace conduct policies",
            "Disagreement over work scope and responsibilities"
        ]
    }
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
    "warning_issued('Formal warning issued to defendant')"
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
    ["compliance_check", "resolution_verified"]
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
        "cbopz-duaaa-aaaah-qcaiq-cai"
    ]
    
    statuses = ["pending", "in_review", "mediation", "resolved", "dismissed", "appealed"]
    status_weights = [0.3, 0.25, 0.15, 0.2, 0.05, 0.05]  # More pending and in_review cases
    
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
            "actions_taken": []
        }
        
        # Add verdict and actions for resolved cases
        if status in ["resolved", "dismissed"]:
            if status == "resolved":
                case["verdict"] = random.choice(SAMPLE_VERDICTS)
                case["actions_taken"] = ["transfer_executed", "case_closed"] if "transfer(" in case["verdict"] else ["verdict_rendered", "case_closed"]
            else:
                case["verdict"] = "no_action_required('Case dismissed - insufficient evidence')"
                case["actions_taken"] = ["investigation_completed", "case_dismissed"]
        elif status in ["in_review", "mediation"]:
            case["actions_taken"] = random.choice(ACTIONS_TAKEN[:6])  # Partial actions
        elif status == "appealed":
            case["verdict"] = random.choice(SAMPLE_VERDICTS)
            case["actions_taken"] = ["verdict_rendered", "appeal_filed", "review_pending"]
        
        cases.append(case)
    
    return cases

def update_justice_litigation_backend():
    """Update the Justice Litigation backend with demo data"""
    
    # Generate demo cases
    demo_cases = generate_litigation_cases(25)
    
    # Read the current backend entry.py file
    backend_file = "/home/user/dev/smartsocialcontracts/realms3/extensions/justice_litigation/backend/entry.py"
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    # Create the demo data as a Python list string
    demo_data_str = "[\n"
    for i, case in enumerate(demo_cases):
        demo_data_str += "    " + json.dumps(case, indent=4).replace('\n', '\n    ')
        if i < len(demo_cases) - 1:
            demo_data_str += ","
        demo_data_str += "\n"
    demo_data_str += "]"
    
    # Replace the empty LITIGATION_STORAGE with demo data
    updated_content = content.replace(
        "LITIGATION_STORAGE = []",
        f"LITIGATION_STORAGE = {demo_data_str}"
    )
    
    # Write the updated content back
    with open(backend_file, 'w') as f:
        f.write(updated_content)
    
    print(f"✅ Successfully populated Justice Litigation extension with {len(demo_cases)} demo cases")
    
    # Print summary statistics
    status_counts = {}
    for case in demo_cases:
        status = case["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    case_type_counts = {}
    for case in demo_cases:
        case_type = case["case_title"]
        case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1
    
    print("\n📊 Demo Data Statistics:")
    print(f"Total Cases: {len(demo_cases)}")
    print("\nStatus Distribution:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    print("\nCase Type Distribution:")
    for case_type, count in case_type_counts.items():
        print(f"  {case_type}: {count}")
    
    print(f"\nDate Range: {min(case['requested_at'] for case in demo_cases)} to {max(case['requested_at'] for case in demo_cases)}")

if __name__ == "__main__":
    update_justice_litigation_backend()
