import math
import traceback
from typing import Any, Dict, List, Optional

from ggg.codex import Codex
from ggg.dispute import Dispute
from ggg.human import Human
from ggg.instrument import Instrument
from ggg.license import License
from ggg.mandate import Mandate
from ggg.organization import Organization
from ggg.proposal import Proposal
from ggg.realm import Realm
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from ggg.trade import Trade
from ggg.transfer import Transfer
from ggg.treasury import Treasury
from ggg.user import User
from ggg.vote import Vote
from ggg.user_profile import UserProfile

from kybra_simple_logging import get_logger

logger = get_logger("api.ggg_entities")


def list_objects(params: tuple[str, str]) -> List[Any]:
    """List objects in the system."""
    try:
        ret = []
        for param in params:
            try:
                class_name = param[0]
                id = param[1]
                class_object = globals()[class_name]
                object = class_object[id]
                ret.append(object)
            except Exception as e:
                logger.error(traceback.format_exc())
        return ret
    except Exception as e:
        logger.error(traceback.format_exc())
        ret.append(None)
    return []


def list_objects_paginated(
    class_name: str, page_num: int, page_size: int
) -> Dict[str, Any]:
    """List objects in the system with pagination."""
    try:
        from_id = page_num * page_size + 1
        logger.info(f"Listing objects from {from_id} with page size {page_size}")
        class_object = globals()[class_name]
        logger.info(f"Class object: {class_object}")
        objects = class_object.load_some(from_id=from_id, count=page_size)
        logger.info(f"Objects: {objects}")
        count = class_object.count()
        logger.info(f"Count: {count}")
        return {
            "items": objects,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(traceback.format_exc())
    return {}
