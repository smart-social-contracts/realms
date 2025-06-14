from ggg import (
    Human,
    User,
)
from kybra_simple_logging import get_logger
from .config import NUM_USERS

logger = get_logger("demo_loader.user_management")

def run():
    """Create a larger set of users and humans for the demo.
    
    Args:
        base_entities (dict): Dictionary containing core entities from base_setup
    """
    logger.info(f"Creating {NUM_USERS} users and humans")

    # Create a list of demo users and humans
    users_data = [
        {"name": "alice", "human_name": "Alice Johnson"},
        {"name": "bob", "human_name": "Bob Smith"},
        {"name": "carol", "human_name": "Carol White"},
        {"name": "dave", "human_name": "Dave Brown"},
        {"name": "eve", "human_name": "Eve Wilson"},
        {"name": "frank", "human_name": "Frank Miller"},
        {"name": "grace", "human_name": "Grace Davis"},
        {"name": "henry", "human_name": "Henry Taylor"},
        {"name": "ivy", "human_name": "Ivy Anderson"},
        {"name": "jack", "human_name": "Jack Martinez"},
        {"name": "kate", "human_name": "Kate Wilson"},
        {"name": "leo", "human_name": "Leo Brown"},
        {"name": "mia", "human_name": "Mia Davis"},
        {"name": "nina", "human_name": "Nina Taylor"},
        {"name": "oscar", "human_name": "Oscar Martinez"},
        {"name": "paul", "human_name": "Paul Anderson"},
        {"name": "quinn", "human_name": "Quinn Wilson"},
        {"name": "ryan", "human_name": "Ryan Brown"},
        {"name": "sara", "human_name": "Sara Davis"},
        {"name": "tom", "human_name": "Tom Taylor"}
    ]

    # Ensure we don't exceed the configured number of users
    users_data = users_data[:NUM_USERS]

    # Create users and their corresponding humans
    users = []
    humans = []
    
    for user_data in users_data:
        human = Human(name=user_data["human_name"])
        user = User(name=user_data["name"])
        humans.append(human)
        users.append(user)

    logger.info(f"Created {len(users)} users and {len(humans)} humans")

    return f"Created {len(users)} users and {len(humans)} humans"

