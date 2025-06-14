from ggg import (
    Realm,
    Treasury,
    User,
)
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.base_setup")


def run():
    """Create core entities needed for all demos."""
    logger.info("Running base setup")

    # Create the Realm as the top political entity
    realm = Realm(
        name="Digital Republic",
        description="A digital sovereign realm governing digital assets and relationships",
    )

    # Create a system user to represent the realm in transfers
    system_user = User(name="system")

    # Create the Treasury
    treasury = Treasury(name="Digital Republic Treasury", vault_principal_id="abc123")

    logger.info("Base setup completed successfully")

    # Return a string representation instead of objects
    return "Created Realm, System User, and Treasury"


if __name__ == "__main__":
    run()
