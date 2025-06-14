from ggg import (
    Organization,
    Instrument,
)
from kybra_simple_logging import get_logger
from .config import NUM_ORGANIZATIONS, NUM_INSTRUMENTS

logger = get_logger("demo_loader.financial_services")

def run():
    """Create financial services related entities."""
    logger.info(f"Creating {NUM_ORGANIZATIONS} organizations and {NUM_INSTRUMENTS} instruments")

    # Create organizations
    organizations = []
    org_names = [
        "Financial Services Inc.",
        "Digital Banking Solutions",
        "Crypto Exchange Platform",
        "Investment Management Corp",
        "Blockchain Technology Group",
        "Digital Asset Securities",
        "Smart Contract Solutions",
        "Decentralized Finance Hub",
        "Digital Payment Systems",
        "Blockchain Infrastructure Co."
    ]

    for i in range(NUM_ORGANIZATIONS):
        org = Organization(name=org_names[i])
        organizations.append(org)

    # Create financial instruments
    instruments = []
    instrument_names = [
        "Bitcoin",
        "Ethereum",
        "Digital Dollar",
        "Smart Contract Token",
        "Governance Token"
    ]

    for i in range(NUM_INSTRUMENTS):
        instrument = Instrument(name=instrument_names[i])
        instruments.append(instrument)

    logger.info(f"Created {len(organizations)} organizations and {len(instruments)} instruments")

    return f"Created {len(organizations)} organizations and {len(instruments)} instruments"
