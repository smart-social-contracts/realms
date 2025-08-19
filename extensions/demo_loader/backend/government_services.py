from ggg import (
    Codex,
    License,
    Mandate,
    Task,
    TaskSchedule,
)
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.government_services")


def run():
    """Create government services related entities."""

    # Create licenses
    licenses = []
    license_data = [
        {
            "name": "Digital Citizenship License",
            "code": "if age >= 16 and identity_verified and civic_test_passed: return True",
        },
        {
            "name": "DeFi Trading License",
            "code": "if financial_literacy_certified and risk_assessment_passed: return True",
        },
        {
            "name": "DAO Governance License",
            "code": "if governance_training_completed and community_standing >= 80: return True",
        },
        {
            "name": "Smart Contract Developer License",
            "code": "if security_audit_passed and code_review_approved: return True",
        },
        {
            "name": "Community Leader License",
            "code": "if leadership_experience and community_endorsement >= 5: return True",
        },
        {
            "name": "Innovation Project License",
            "code": "if project_proposal_approved and sustainability_score >= 70: return True",
        },
        {
            "name": "Digital Asset Custodian License",
            "code": "if security_certification and insurance_coverage and audit_passed: return True",
        },
    ]

    logger.info(f"Creating {len(license_data)} licenses")

    for i in range(len(license_data)):
        license_info = license_data[i]
        codex = Codex(
            name=f"{license_info['name']} Verification", code=license_info["code"]
        )
        license = License(name=license_info["name"])
        licenses.append(license)

    # Create mandates - Enhanced for impressive demo
    mandates = []
    mandate_data = [
        {
            "name": "Universal Basic Income",
            "description": "Monthly UBI payments to all verified citizens - 500 tokens per month",
            "cron": "0 0 1 * *",  # First day of each month
        },
        {
            "name": "Carbon Credit Distribution",
            "description": "Quarterly carbon credit rewards for sustainable practices",
            "cron": "0 0 1 1,4,7,10 *",  # Quarterly
        },
        {
            "name": "Democratic Participation Rewards",
            "description": "Monthly rewards for active governance participation and voting",
            "cron": "0 0 15 * *",  # 15th of each month
        },
        {
            "name": "Innovation Fund Grants",
            "description": "Quarterly grants for community innovation projects and startups",
            "cron": "0 0 1 3,6,9,12 *",  # Quarterly
        },
        {
            "name": "Digital Infrastructure Maintenance",
            "description": "Weekly automated maintenance and security updates for realm infrastructure",
            "cron": "0 2 * * 0",  # Every Sunday at 2 AM
        },
        {
            "name": "Community Health Monitoring",
            "description": "Daily health checks and wellness support for all citizens",
            "cron": "0 8 * * *",  # Daily at 8 AM
        },
        {
            "name": "Education Excellence Program",
            "description": "Bi-annual educational advancement and skill development funding",
            "cron": "0 0 1 3,9 *",  # March and September
        },
        {
            "name": "Transparency Reporting",
            "description": "Monthly automated transparency reports on governance activities",
            "cron": "0 0 1 * *",  # First day of each month
        },
    ]

    logger.info(f"Creating {len(mandate_data)} mandates")

    for i in range(len(mandate_data)):
        mandate_info = mandate_data[i]
        mandate = Mandate(
            name=mandate_info["name"],
            metadata=f'{{"description": "{mandate_info["description"]}"}}',
        )

        # Create associated task and schedule
        task = Task(
            name=f"{mandate_info['name']} Processing",
            metadata=f'{{"description": "Process {mandate_info["name"].lower()} payments"}}',
        )

        schedule = TaskSchedule(cron_expression=mandate_info["cron"])
        schedule.tasks.add(task)

        mandates.append(mandate)

    logger.info(f"Created {len(mandates)} mandates")

    return f"Created {len(mandates)} mandates"
