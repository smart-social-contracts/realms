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
from ggg.user import User
from ggg.vote import Vote
from kybra_simple_logging import get_logger

logger = get_logger("api.ggg_entities")


def list_users() -> Dict[str, Any]:
    """List all users in the system."""
    try:
        users = [user.to_dict() for user in User.instances()]
        return {"users": users}
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise


def list_humans() -> Dict[str, Any]:
    """List all humans in the system."""
    try:
        humans = [human.to_dict() for human in Human.instances()]
        return {"humans": humans}
    except Exception as e:
        logger.error(f"Error listing humans: {str(e)}")
        raise


def list_mandates() -> Dict[str, Any]:
    """List all mandates in the system."""
    try:
        mandates = [mandate.to_dict() for mandate in Mandate.instances()]
        return {"mandates": mandates}
    except Exception as e:
        logger.error(f"Error listing mandates: {str(e)}")
        raise


def list_tasks() -> Dict[str, Any]:
    """List all tasks in the system."""
    try:
        tasks = [task.to_dict() for task in Task.instances()]
        return {"tasks": tasks}
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


def list_codexes() -> Dict[str, Any]:
    """List all codexes in the system."""
    try:
        codexes = [codex.to_dict() for codex in Codex.instances()]
        return {"codexes": codexes}
    except Exception as e:
        logger.error(f"Error listing codexes: {str(e)}")
        raise


def list_instruments() -> Dict[str, Any]:
    """List all instruments in the system."""
    try:
        instruments = [instrument.to_dict() for instrument in Instrument.instances()]
        return {"instruments": instruments}
    except Exception as e:
        logger.error(f"Error listing instruments: {str(e)}")
        raise


def list_trades() -> Dict[str, Any]:
    """List all trades in the system."""
    try:
        trades = [trade.to_dict() for trade in Trade.instances()]
        return {"trades": trades}
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


def list_organizations() -> Dict[str, Any]:
    """List all organizations in the system."""
    try:
        organizations = [org.to_dict() for org in Organization.instances()]
        return {"organizations": organizations}
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        raise


def list_realms() -> Dict[str, Any]:
    """List all realms in the system."""
    try:
        realms = [realm.to_dict() for realm in Realm.instances()]
        return {"realms": realms}
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}")
        raise


def list_licenses() -> Dict[str, Any]:
    """List all licenses in the system."""
    try:
        licenses = [license.to_dict() for license in License.instances()]
        return {"licenses": licenses}
    except Exception as e:
        logger.error(f"Error listing licenses: {str(e)}")
        raise


def list_disputes() -> Dict[str, Any]:
    """List all disputes in the system."""
    try:
        disputes = [dispute.to_dict() for dispute in Dispute.instances()]
        return {"disputes": disputes}
    except Exception as e:
        logger.error(f"Error listing disputes: {str(e)}")
        raise


def list_proposals() -> Dict[str, Any]:
    """List all proposals in the system."""
    try:
        proposals = [proposal.to_dict() for proposal in Proposal.instances()]
        return {"proposals": proposals}
    except Exception as e:
        logger.error(f"Error listing proposals: {str(e)}")
        raise


def list_votes() -> Dict[str, Any]:
    """List all votes in the system."""
    try:
        votes = [vote.to_dict() for vote in Vote.instances()]
        return {"votes": votes}
    except Exception as e:
        logger.error(f"Error listing votes: {str(e)}")
        raise
