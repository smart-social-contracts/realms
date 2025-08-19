from ggg import (
    Profiles,
    Realm,
    Treasury,
    User,
    UserProfile,
)
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.base_setup")


def run():
    """Create core entities needed for all demos."""
    logger.info("Running base setup")

    # Create the Realm as the top political entity
    realm = Realm(
        name="New Geneva Digital Republic",
        description="A thriving digital democracy with active governance, diverse organizations, and innovative financial systems. Home to 250+ engaged citizens participating in decentralized decision-making.",
    )

    user_profile_admin = UserProfile(
        name=Profiles.ADMIN[0],
        allowed_to=",".join(Profiles.ADMIN[1]),
        description="Admin user profile",
    )

    user_profile_admin = UserProfile(
        name=Profiles.ADMIN[0],
        allowed_to=",".join(Profiles.ADMIN[1]),
        description="Admin user profile",
    )

    user_profile_member = UserProfile(
        name=Profiles.MEMBER[0],
        allowed_to=",".join(Profiles.MEMBER[1]),
        description="Member user profile",
    )

    # Create a system user to represent the realm in transfers
    system_user = User(name="system", profiles=[user_profile_admin])

    # Create the Treasury
    treasury = Treasury(name="New Geneva Treasury", vault_principal_id="abc123")

    logger.info("Base setup completed successfully")

    # Return a string representation instead of objects
    return "Created New Geneva Digital Republic - A thriving democracy with active governance, System User, and Treasury"


if __name__ == "__main__":
    run()
