from kybra_simple_db import Entity, String, TimestampedMixin, Database
from kybra_simple_logging import get_logger

from ggg.user import User

logger = get_logger("demo_loader.demo1")


def run():
    """Get test data from this extension.

    The core module will handle the async wrapping for us.
    """
    logger.info("load_demo_data called")

    logger.info("Clearing database")
    Database.get_instance().clear()

    logger.info("Creating user")
    user = User(
        _id="user_1",
        metadata="{}"
    )

    logger.info(f"User created: {user.to_dict()}")
    
    return "OK"

'''
PYTHONPATH=/home/user/dev/smart-social-contracts/public/realms2/src/realm_backend python src/realm_backend/extensions/demo_loader/demo1.py 
'''
if __name__ == "__main__":
    run()