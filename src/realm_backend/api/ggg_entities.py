import math
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
from kybra_simple_logging import get_logger

logger = get_logger("api.ggg_entities")


def list_users(page_num: int, page_size: int) -> Dict[str, Any]:
    """List users in the system with pagination."""
    try:
        from_id = page_num * page_size + 1
        logger.info(f"Listing users from {from_id} with page size {page_size}")
        users = User.load_some(from_id=from_id, count=page_size)
        count = User.count()
        return {
            "items": users,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise


def list_humans(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all humans in the system."""
    try:
        from_id = page_num * page_size + 1
        humans = Human.load_some(from_id=from_id, count=page_size)
        count = Human.count()
        return {
            "items": humans,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing humans: {str(e)}")
        raise


def list_mandates(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all mandates in the system."""
    try:
        from_id = page_num * page_size + 1
        mandates = Mandate.load_some(from_id=from_id, count=page_size)
        count = Mandate.count()
        return {
            "items": mandates,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing mandates: {str(e)}")
        raise


def list_tasks(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all tasks in the system."""
    try:
        from_id = page_num * page_size + 1
        tasks = Task.load_some(from_id=from_id, count=page_size)
        count = Task.count()
        return {
            "items": tasks,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise


def list_task_schedules() -> Dict[str, Any]:
    """List all task schedules in the system."""
    try:
        schedules = [schedule.to_dict() for schedule in TaskSchedule.instances()]
        return {"schedules": schedules}
    except Exception as e:
        logger.error(f"Error listing task schedules: {str(e)}")
        raise


def list_codexes(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all codexes in the system."""
    try:
        from_id = page_num * page_size + 1
        codexes = Codex.load_some(from_id=from_id, count=page_size)
        count = Codex.count()
        return {
            "items": codexes,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing codexes: {str(e)}")
        raise


def list_instruments(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all instruments in the system."""
    try:
        from_id = page_num * page_size + 1
        instruments = Instrument.load_some(from_id=from_id, count=page_size)
        count = Instrument.count()
        return {
            "items": instruments,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing instruments: {str(e)}")
        raise


def list_trades(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all trades in the system."""
    try:
        from_id = page_num * page_size + 1
        trades = Trade.load_some(from_id=from_id, count=page_size)
        count = Trade.count()
        return {
            "items": trades,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}")
        raise


def list_transfers(page_num: int, page_size: int) -> List[Transfer]:
    """List transfers in the system with pagination."""

    try:
        from_id = page_num * page_size + 1
        logger.info(f"Listing transfers from {from_id} with page size {page_size}")
        transfers = Transfer.load_some(from_id=from_id, count=page_size)
        count = Transfer.count()
        return {
            "items": transfers,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}")
        return []


def list_organizations(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all organizations in the system."""
    try:
        from_id = page_num * page_size + 1
        organizations = Organization.load_some(from_id=from_id, count=page_size)
        count = Organization.count()
        return {
            "items": organizations,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        raise


def list_realms(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all realms in the system."""
    try:
        from_id = page_num * page_size + 1
        realms = Realm.load_some(from_id=from_id, count=page_size)
        count = Realm.count()
        return {
            "items": realms,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}")
        raise


def list_licenses(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all licenses in the system."""
    try:
        from_id = page_num * page_size + 1
        licenses = License.load_some(from_id=from_id, count=page_size)
        count = License.count()
        return {
            "items": licenses,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing licenses: {str(e)}")
        raise


def list_disputes(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all disputes in the system."""
    try:
        from_id = page_num * page_size + 1
        disputes = Dispute.load_some(from_id=from_id, count=page_size)
        count = Dispute.count()
        return {
            "items": disputes,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing disputes: {str(e)}")
        raise


def list_proposals(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all proposals in the system."""
    try:
        from_id = page_num * page_size + 1
        proposals = Proposal.load_some(from_id=from_id, count=page_size)
        count = Proposal.count()
        return {
            "items": proposals,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing proposals: {str(e)}")
        raise


def list_votes(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all votes in the system."""
    try:
        from_id = page_num * page_size + 1
        votes = Vote.load_some(from_id=from_id, count=page_size)
        count = Vote.count()
        return {
            "items": votes,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing votes: {str(e)}")
        raise


def list_treasuries(page_num: int, page_size: int) -> Dict[str, Any]:
    """List all treasuries in the system."""
    try:
        from_id = page_num * page_size + 1
        treasuries = Treasury.load_some(from_id=from_id, count=page_size)

        # Load realm relationships for each treasury
        for treasury in treasuries:
            if hasattr(treasury, "realm") and treasury.realm:
                # Force load the realm relationship
                treasury._relations["realm"] = [treasury.realm]

        logger.info(f"Listing treasuries from {from_id} with page size {page_size}")
        logger.info(f"Treasuries[0]: {treasuries[0].to_dict()}")

        count = Treasury.count()
        return {
            "items": treasuries,
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": count,
            "total_pages": math.ceil(count / page_size),
        }
    except Exception as e:
        logger.error(f"Error listing treasuries: {str(e)}")
        raise
