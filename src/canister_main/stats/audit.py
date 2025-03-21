from kybra_simple_db import *
# from core.db_storage import db_history # TODO: broken


class AuditEntity(Entity):
    """Base class for auditable entities that store history."""
    _db_storage = db_history
