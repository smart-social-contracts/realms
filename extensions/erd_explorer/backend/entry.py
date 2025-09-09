"""
ERD Explorer Extension Backend
Provides entity relationship data and metadata for the ERD visualization
"""

import inspect

from api.ggg_entities import (
    list_codexes,
    list_disputes,
    list_instruments,
    list_licenses,
    list_mandates,
    list_organizations,
    list_proposals,
    list_realms,
    list_tasks,
    list_trades,
    list_transfers,
    list_users,
    list_votes,
)
from ggg.balance import Balance
from ggg.citizen import Citizen
from ggg.codex import Codex
from ggg.contract import Contract
from ggg.dispute import Dispute
from ggg.human import Human
from ggg.identity import Identity
from ggg.instrument import Instrument
from ggg.land import Land
from ggg.license import License
from ggg.mandate import Mandate
from ggg.organization import Organization
from ggg.proposal import Proposal
from ggg.realm import Realm
from ggg.task import Task
from ggg.task_executions import TaskExecution
from ggg.task_schedule import TaskSchedule
from ggg.trade import Trade
from ggg.transfer import Transfer
from ggg.treasury import Treasury
from ggg.user import User
from ggg.user_profile import UserProfile
from ggg.vote import Vote
from kybra_simple_db import (
    Boolean,
    Entity,
    Float,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)


def extract_entity_schema():
    """
    Dynamically extracts entity schema from GGG class definitions
    """
    # Get all entity classes
    entity_classes = [
        User,
        Realm,
        Human,
        Identity,
        Citizen,
        Organization,
        Codex,
        Task,
        Transfer,
        Trade,
        Instrument,
        Mandate,
        Dispute,
        License,
        Proposal,
        Vote,
        Treasury,
        Balance,
        Land,
        UserProfile,
        TaskSchedule,
        TaskExecution,
        Contract,
    ]

    entities = {}

    for entity_class in entity_classes:
        class_name = entity_class.__name__
        fields = []
        relationships = {}

        # Get all class attributes
        for attr_name in dir(entity_class):
            if attr_name.startswith("_"):
                continue

            attr = getattr(entity_class, attr_name)

            # Check if it's a field type
            if isinstance(attr, (String, Integer, Boolean, Float)):
                fields.append(attr_name)

            # Check if it's a relationship
            elif isinstance(attr, (OneToOne, OneToMany, ManyToOne, ManyToMany)):
                rel_type = type(attr).__name__
                target = attr.target if hasattr(attr, "target") else "Unknown"
                related_name = (
                    attr.related_name if hasattr(attr, "related_name") else None
                )

                # Clean target name if it's a list
                if isinstance(target, list) and len(target) > 0:
                    target = target[0]

                relationships[attr_name] = {
                    "type": rel_type,
                    "target": target,
                    "field": related_name,
                }

        # Add default fields from TimestampedMixin if present
        if issubclass(entity_class, TimestampedMixin):
            fields.extend(["created_at", "updated_at"])

        # Always include id field
        if "id" not in fields:
            fields.insert(0, "id")

        entities[class_name] = {"fields": fields, "relationships": relationships}

    return {"entities": entities}


def get_entity_schema():
    """
    Returns the complete entity schema with relationships extracted from class definitions
    """
    return extract_entity_schema()


def get_entity_data(entity_type, page_num=0, page_size=10):
    """
    Returns actual entity data from the database
    """
    try:
        entity_map = {
            "User": list_users,
            "Codex": list_codexes,
            "Dispute": list_disputes,
            "Instrument": list_instruments,
            "License": list_licenses,
            "Mandate": list_mandates,
            "Organization": list_organizations,
            "Proposal": list_proposals,
            "Realm": list_realms,
            "Task": list_tasks,
            "Trade": list_trades,
            "Transfer": list_transfers,
            "Vote": list_votes,
        }

        if entity_type in entity_map:
            result = entity_map[entity_type](page_num, page_size)
            # Convert entity objects to dictionaries
            items = []
            for item in result["items"]:
                if hasattr(item, "to_dict"):
                    items.append(item.to_dict())
                else:
                    items.append(str(item))

            return {
                "items": items,
                "page_num": result["page_num"],
                "page_size": result["page_size"],
                "total_items_count": result["total_items_count"],
                "total_pages": result["total_pages"],
            }
        else:
            # For entities without list functions, return empty result
            return {
                "items": [],
                "page_num": page_num,
                "page_size": page_size,
                "total_items_count": 0,
                "total_pages": 0,
            }
    except Exception as e:
        # Return empty result if there's an error
        return {
            "items": [],
            "page_num": page_num,
            "page_size": page_size,
            "total_items_count": 0,
            "total_pages": 0,
        }
