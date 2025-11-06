import math
import traceback
from typing import Any, Dict, List, Optional

from ggg.balance import Balance
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
from ggg.user_profile import UserProfile
from ggg.vote import Vote
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
    return []


def list_objects_paginated(
    class_name: str, page_num: int, page_size: int, order: str = "asc"
) -> Dict[str, Any]:
    """List objects in the system with pagination.
    
    Args:
        class_name: Name of the entity class to query
        page_num: Page number (0-indexed)
        page_size: Number of items per page
        order: Sort order, either 'asc' (ascending) or 'desc' (descending). Default is 'asc'.
    """
    try:
        class_object = globals()[class_name]
        count = class_object.count()
        logger.info(f"Total count: {count}")
        
        if order == "desc":
            # For descending order with efficient loading:
            # Assume IDs are mostly sequential. Load from calculated position.
            # Page 0: from_id = count - page_size + 1 (e.g., 94 for 103 total, size 10)
            # Page 1: from_id = count - 2*page_size + 1 (e.g., 84)
            from_id = max(1, count - ((page_num + 1) * page_size) + 1)
            
            logger.info(f"Listing objects (desc): loading {page_size} items from ID {from_id}")
            objects = class_object.load_some(from_id=from_id, count=page_size)
            
            # Reverse to show newest first
            objects.reverse()
        else:
            # For ascending order, use standard pagination
            from_id = page_num * page_size + 1
            logger.info(f"Listing objects (asc) from {from_id} with page size {page_size}")
            objects = class_object.load_some(from_id=from_id, count=page_size)
        
        logger.info(f"Loaded {len(objects)} objects")
        
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
