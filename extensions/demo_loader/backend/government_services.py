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
            "name": "Standard Driver's License",
            "code": "if age >= 16 and passed_test: return True",
        },
        {
            "name": "Professional License",
            "code": "if has_qualification and background_check: return True",
        },
        {
            "name": "Business License",
            "code": "if has_registration and tax_compliant: return True",
        },
        {
            "name": "Digital Asset License",
            "code": "if has_kyc and risk_assessment: return True",
        },
        {
            "name": "Smart Contract License",
            "code": "if has_audit and security_check: return True",
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

    # Create mandates
    mandates = []
    mandate_data = [
        {
            "name": "Retirement Pension",
            "description": "Citizens receive periodic payments upon reaching age 65",
            "cron": "0 0 1 * *",  # First day of each month
        },
        {
            "name": "Land Rental",
            "description": "Standardized land rental agreements and payments",
            "cron": "0 0 1 * *",
        },
        {
            "name": "Tax Collection",
            "description": "Annual tax collection and processing",
            "cron": "0 0 15 4 *",  # April 15th yearly
        },
        {
            "name": "Social Security",
            "description": "Monthly social security payments",
            "cron": "0 0 1 * *",
        },
        {
            "name": "Healthcare Coverage",
            "description": "Healthcare service coverage and payments",
            "cron": "0 0 1 * *",
        },
        {
            "name": "Education Grants",
            "description": "Educational funding and scholarship distribution",
            "cron": "0 0 1 9 *",  # September 1st yearly
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
