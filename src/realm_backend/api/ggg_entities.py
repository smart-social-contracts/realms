import importlib
import math
import traceback
from typing import Any, Dict, List, Optional

from ggg.balance import Balance
from ggg.budget import Budget, BudgetStatus
from ggg.call import Call
from ggg.codex import Codex
from ggg.contract import Contract
from ggg.dispute import Dispute
from ggg.fiscal_period import FiscalPeriod, FiscalPeriodStatus
from ggg.fund import Fund, FundType
from ggg.human import Human
from ggg.identity import Identity
from ggg.instrument import Instrument
from ggg.invoice import Invoice
from ggg.land import Land, LandType
from ggg.ledger_entry import Category, EntryType, LedgerEntry
from ggg.license import License, LicenseType, license_issue, license_revoke
from ggg.mandate import Mandate

# Justice System entities
from ggg.justice_system import JusticeSystem, JusticeSystemType
from ggg.court import Court, CourtLevel
from ggg.judge import Judge
from ggg.case import Case, CaseStatus, case_file, case_assign_judges, case_issue_verdict, case_close
from ggg.verdict import Verdict, verdict_prehook, verdict_posthook
from ggg.penalty import Penalty, PenaltyType, penalty_execute, penalty_waive
from ggg.appeal import Appeal, AppealStatus, appeal_file, appeal_decide

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
from ggg.token import Token
from ggg.trade import Trade
from ggg.transfer import Transfer
from ggg.treasury import Treasury
from ggg.user import User
from ggg.user_profile import Operations, Profiles, UserProfile
from ggg.vote import Vote
from ggg.zone import Zone
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


def search_objects(class_name: str, params: List[tuple[str, str]]) -> List[Any]:
    """Search for objects matching the given field criteria using Entity.find().

    Args:
        class_name: Name of the entity class to query. Supports namespaced format
                    for extension entities (e.g., "vault::KnownSubaccount")
        params: List of (field_name, field_value) tuples to match

    Returns:
        List of entities matching all criteria
    """
    try:
        # Handle namespaced extension entities (e.g., "vault::KnownSubaccount")
        if "::" in class_name:
            ext_name, entity_name = class_name.split("::", 1)
            try:
                entities_module = importlib.import_module(
                    f"extension_packages.{ext_name}.{ext_name}_lib.entities"
                )
            except ImportError:
                entities_module = importlib.import_module(
                    f"extension_packages.{ext_name}.vault_lib.entities"
                )
            class_object = getattr(entities_module, entity_name)
        else:
            class_object = globals()[class_name]

        search_dict = {k: v for k, v in params}
        logger.info(f"Searching {class_name} with criteria: {search_dict}")
        results = class_object.find(search_dict)
        logger.info(f"Found {len(results)} matching objects")
        return results
    except KeyError as e:
        logger.error(
            f"Entity class '{class_name}' not found in globals(). "
            f"Make sure it's imported in ggg_entities.py. "
            f"Available classes: {[k for k in globals().keys() if k[0].isupper() and not k.startswith('_')]}"
        )
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error searching {class_name}: {e}")
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
        max_id = class_object.max_id()
        logger.info(f"Total count: {count}, max_id: {max_id}")

        if order == "desc":
            # For descending order: use max_id to calculate from_id
            # Page 0: load last page_size items (max_id - page_size + 1 to max_id)
            # Page 1: load previous page_size items, etc.
            from_id = max(1, max_id - ((page_num + 1) * page_size) + 1)

            logger.info(
                f"Listing objects (desc): loading {page_size} items from ID {from_id}"
            )
            objects = class_object.load_some(from_id=from_id, count=page_size)

            # Reverse to show newest first
            objects.reverse()
        else:
            # For ascending order, use standard pagination
            # Calculate min_id from max_id and count
            min_id = max(1, max_id - count + 1)
            from_id = min_id + (page_num * page_size)
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
    except KeyError as e:
        logger.error(
            f"Entity class '{class_name}' not found in globals(). "
            f"Make sure it's imported in ggg_entities.py. "
            f"Available classes: {[k for k in globals().keys() if k[0].isupper() and not k.startswith('_')]}"
        )
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error listing {class_name}: {e}")
        logger.error(traceback.format_exc())
    return {}
