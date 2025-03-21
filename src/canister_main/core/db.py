from core.utils import running_on_ic
from kybra_simple_db import *

# Global database instance
db = None

# Global database storage instances
storage_db = None
# storage_db_history = None
storage_db_audit = None


if running_on_ic():
    from kybra import StableBTreeMap

    # TODO: StableBTreeMap[str, Variant] and the Variant being a StableBTreeMap[str, Variant] too?
    storage_db = StableBTreeMap[str, str](
        memory_id=9, max_key_size=100_000, max_value_size=1_000_000
    )

    # storage_db_history = StableBTreeMap[str, str](
    #     memory_id=10, max_key_size=100_000, max_value_size=1_000_000
    # )

    storage_db_audit = StableBTreeMap[str, str](
        memory_id=11, max_key_size=100_000, max_value_size=1_000_000
    )

else:
    from kybra_simple_db import MemoryStorage

    storage_db = MemoryStorage()
    # storage_db_history = MemoryStorage()
    storage_db_audit = MemoryStorage()


def get_db() -> Database:
    """Get the database instance."""
    return db


def init_db():
    """Initialize the database with required collections."""
    global db
    if db is None:
        db = Database(db_storage=storage_db, db_audit=storage_db_audit)
        Database._instance = db
    return db
