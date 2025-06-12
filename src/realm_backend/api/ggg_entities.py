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


def list_transfers(page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """List transfers in the system with pagination."""
    try:
        transfers = []
        total_count = 0

        # Check if Transfer class is available and has instances
        if hasattr(Transfer, "instances"):
            try:
                # Get all transfers as a list to count them
                all_transfers = list(Transfer.instances())
                total_count = len(all_transfers)

                # Early return if there are no transfers
                if total_count == 0:
                    return {
                        "transfers": [],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "total_pages": 0,
                            "has_next": False,
                            "has_prev": page > 1,
                        },
                    }

                # Calculate pagination
                start_index = (page - 1) * per_page
                end_index = min(start_index + per_page, total_count)

                # Get transfers for current page
                for i in range(start_index, end_index):
                    if i < total_count:
                        transfer = all_transfers[i]
                        # Create transfer dict manually to handle missing relationships
                        transfer_dict = {
                            "_id": transfer._id,
                            "amount": transfer.amount,
                            "timestamp_created": (
                                transfer.timestamp_created
                                if hasattr(transfer, "timestamp_created")
                                else None
                            ),
                            "timestamp_updated": (
                                transfer.timestamp_updated
                                if hasattr(transfer, "timestamp_updated")
                                else None
                            ),
                            "relations": {
                                "from_user": [],
                                "to_user": [],
                                "instrument": [],
                            },
                        }

                        # Safely handle relationships - from_user
                        if (
                            hasattr(transfer, "from_user")
                            and transfer.from_user is not None
                        ):
                            try:
                                from_user = {
                                    "_id": transfer.from_user._id,
                                    "name": (
                                        transfer.from_user.name
                                        if hasattr(transfer.from_user, "name")
                                        else "Unknown"
                                    ),
                                }
                                transfer_dict["relations"]["from_user"].append(
                                    from_user
                                )
                            except Exception as user_error:
                                logger.error(
                                    f"Error getting from_user for transfer {transfer._id}: {str(user_error)}"
                                )

                        # Safely handle relationships - to_user
                        if (
                            hasattr(transfer, "to_user")
                            and transfer.to_user is not None
                        ):
                            try:
                                to_user = {
                                    "_id": transfer.to_user._id,
                                    "name": (
                                        transfer.to_user.name
                                        if hasattr(transfer.to_user, "name")
                                        else "Unknown"
                                    ),
                                }
                                transfer_dict["relations"]["to_user"].append(to_user)
                            except Exception as user_error:
                                logger.error(
                                    f"Error getting to_user for transfer {transfer._id}: {str(user_error)}"
                                )

                        # Safely handle relationships - instrument
                        if (
                            hasattr(transfer, "instrument")
                            and transfer.instrument is not None
                        ):
                            try:
                                instrument = {
                                    "_id": transfer.instrument._id,
                                    "name": (
                                        transfer.instrument.name
                                        if hasattr(transfer.instrument, "name")
                                        else "Unknown"
                                    ),
                                }
                                transfer_dict["relations"]["instrument"].append(
                                    instrument
                                )
                            except Exception as instrument_error:
                                logger.error(
                                    f"Error getting instrument for transfer {transfer._id}: {str(instrument_error)}"
                                )

                        transfers.append(transfer_dict)

            except Exception as transfer_error:
                logger.error(f"Error processing transfers: {str(transfer_error)}")
                # Return a useful error response
                return {
                    "transfers": [],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 0,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": page > 1,
                    },
                }

        return {
            "transfers": transfers,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "total_pages": (
                    (total_count + per_page - 1) // per_page if total_count > 0 else 0
                ),
                "has_next": page * per_page < total_count,
                "has_prev": page > 1,
            },
        }
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}")
        # Simplified error handling - return empty results
        return {
            "transfers": [],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": page > 1,
            },
        }


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
