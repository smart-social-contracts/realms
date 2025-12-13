import importlib
import math
import traceback
from typing import Any, Dict, List, Optional

from ggg.balance import Balance
from ggg.call import Call
from ggg.codex import Codex
from ggg.contract import Contract
from ggg.dispute import Dispute
from ggg.human import Human
from ggg.identity import Identity
from ggg.instrument import Instrument
from ggg.invoice import Invoice
from ggg.land import Land, LandType
from ggg.license import License
from ggg.mandate import Mandate
from ggg.member import Member
from ggg.notification import Notification
from ggg.organization import Organization
from ggg.payment_account import PaymentAccount
from ggg.permission import Permission
from ggg.proposal import Proposal
from ggg.realm import Realm
from ggg.registry import Registry
from ggg.service import Service
from ggg.task import Task
from ggg.task_execution import TaskExecution
from ggg.task_schedule import TaskSchedule
from ggg.task_step import TaskStep
from ggg.trade import Trade
from ggg.transfer import Transfer
from ggg.treasury import Treasury
from ggg.user import User
from ggg.user_profile import Operations, Profiles, UserProfile
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
        class_name: Name of the entity class to query. Supports namespaced format
                    for extension entities (e.g., "vault::KnownSubaccount")
        page_num: Page number (0-indexed)
        page_size: Number of items per page
        order: Sort order, either 'asc' (ascending) or 'desc' (descending). Default is 'asc'.
    """
    try:
        # Handle namespaced extension entities (e.g., "vault::KnownSubaccount")
        if "::" in class_name:
            ext_name, entity_name = class_name.split("::", 1)
            try:
                # Try extension_packages.{ext}.{ext}_lib.entities first
                entities_module = importlib.import_module(
                    f"extension_packages.{ext_name}.{ext_name}_lib.entities"
                )
            except ImportError:
                # Fallback to extension_packages.{ext}.vault_lib.entities (legacy)
                entities_module = importlib.import_module(
                    f"extension_packages.{ext_name}.vault_lib.entities"
                )
            class_object = getattr(entities_module, entity_name)
        else:
            class_object = globals()[class_name]
        count = class_object.count()
        logger.info(f"Total count: {count}")

        if order == "desc":
            # For descending order with efficient loading:
            # Assume IDs are mostly sequential. Load from calculated position.
            # Page 0: from_id = count - page_size + 1 (e.g., 94 for 103 total, size 10)
            # Page 1: from_id = count - 2*page_size + 1 (e.g., 84)
            from_id = max(1, count - ((page_num + 1) * page_size) + 1)

            logger.info(
                f"Listing objects (desc): loading {page_size} items from ID {from_id}"
            )
            objects = class_object.load_some(from_id=from_id, count=page_size)

            # Reverse to show newest first
            objects.reverse()
        else:
            # For ascending order, use standard pagination
            from_id = page_num * page_size + 1
            logger.info(
                f"Listing objects (asc) from {from_id} with page size {page_size}"
            )
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
