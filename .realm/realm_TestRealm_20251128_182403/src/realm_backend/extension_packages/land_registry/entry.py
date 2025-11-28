"""
Land Registry extension entry point
"""

import json
import traceback
from typing import Any, Dict

from ggg import Land, LandType, Organization, User
from kybra_simple_logging import get_logger

logger = get_logger("extensions.land_registry")


def get_lands(args: str) -> str:
    """Get all land parcels with optional filtering"""
    logger.info(f"land_registry.get_lands called with args: {args}")

    try:
        params = json.loads(args) if args else {}

        lands = Land.instances()

        land_data = []
        for land in lands:
            land_dict = {
                "id": land.id,
                "x_coordinate": land.x_coordinate,
                "y_coordinate": land.y_coordinate,
                "land_type": land.land_type,
                "size_width": land.size_width,
                "size_height": land.size_height,
                "metadata": land.metadata,
                "owner_user_id": land.owner_user.id if land.owner_user else None,
                "owner_organization_id": (
                    land.owner_organization.id if land.owner_organization else None
                ),
            }
            land_data.append(land_dict)

        return json.dumps({"success": True, "data": land_data})

    except Exception as e:
        logger.error(f"Error in get_lands: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def create_land(args: str) -> str:
    """Create a new land parcel"""
    logger.info(f"land_registry.create_land called with args: {args}")

    try:
        params = json.loads(args) if args else {}

        x_coord = params.get("x_coordinate")
        y_coord = params.get("y_coordinate")
        land_type = params.get("land_type", LandType.UNASSIGNED)

        if x_coord is None or y_coord is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "x_coordinate and y_coordinate are required",
                }
            )

        existing_lands = Land.instances()
        for existing_land in existing_lands:
            if (
                existing_land.x_coordinate == x_coord
                and existing_land.y_coordinate == y_coord
            ):
                return json.dumps(
                    {
                        "success": False,
                        "error": "Land already exists at these coordinates",
                    }
                )

        land = Land(
            x_coordinate=x_coord,
            y_coordinate=y_coord,
            land_type=land_type,
            size_width=params.get("size_width", 1),
            size_height=params.get("size_height", 1),
            metadata=params.get("metadata", "{}"),
        )

        return json.dumps(
            {
                "success": True,
                "data": {"id": land.id, "message": "Land created successfully"},
            }
        )

    except Exception as e:
        logger.error(f"Error in create_land: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def update_land_ownership(args: str) -> str:
    """Update land ownership"""
    logger.info(f"land_registry.update_land_ownership called with args: {args}")

    try:
        params = json.loads(args) if args else {}

        land_id = params.get("land_id")
        owner_user_id = params.get("owner_user_id")
        owner_organization_id = params.get("owner_organization_id")

        if not land_id:
            return json.dumps({"success": False, "error": "land_id is required"})

        land = None
        for existing_land in Land.instances():
            if existing_land.id == land_id:
                land = existing_land
                break

        if not land:
            return json.dumps({"success": False, "error": "Land not found"})

        if owner_user_id and owner_organization_id:
            return json.dumps(
                {
                    "success": False,
                    "error": "Land cannot be owned by both user and organization",
                }
            )

        if owner_user_id:
            if land.land_type != LandType.RESIDENTIAL:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Members can only own residential land",
                    }
                )

            user = None
            for existing_user in User.instances():
                if existing_user.id == owner_user_id:
                    user = existing_user
                    break

            if not user:
                return json.dumps({"success": False, "error": "User not found"})

            land.owner_user = user
            land.owner_organization = None

        elif owner_organization_id:
            if land.land_type == LandType.RESIDENTIAL:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Organizations cannot own residential land",
                    }
                )

            org = None
            for existing_org in Organization.instances():
                if existing_org.id == owner_organization_id:
                    org = existing_org
                    break

            if not org:
                return json.dumps({"success": False, "error": "Organization not found"})

            land.owner_organization = org
            land.owner_user = None

        else:
            land.owner_user = None
            land.owner_organization = None

        land.save()

        return json.dumps(
            {"success": True, "data": {"message": "Ownership updated successfully"}}
        )

    except Exception as e:
        logger.error(
            f"Error in update_land_ownership: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_land_map(args: str) -> str:
    """Get land map data for visualization"""
    logger.info(f"land_registry.get_land_map called with args: {args}")

    try:
        params = json.loads(args) if args else {}

        min_x = params.get("min_x", 0)
        max_x = params.get("max_x", 20)
        min_y = params.get("min_y", 0)
        max_y = params.get("max_y", 20)

        lands = Land.instances()
        map_data = {}

        for land in lands:
            if (
                min_x <= land.x_coordinate <= max_x
                and min_y <= land.y_coordinate <= max_y
            ):
                key = f"{land.x_coordinate},{land.y_coordinate}"
                map_data[key] = {
                    "id": land.id,
                    "x": land.x_coordinate,
                    "y": land.y_coordinate,
                    "type": land.land_type,
                    "owner_type": (
                        "user"
                        if land.owner_user
                        else "organization" if land.owner_organization else "none"
                    ),
                    "owner_name": (
                        land.owner_user.id
                        if land.owner_user
                        else (
                            land.owner_organization.name
                            if land.owner_organization
                            else None
                        )
                    ),
                }

        return json.dumps(
            {
                "success": True,
                "data": {
                    "bounds": {
                        "min_x": min_x,
                        "max_x": max_x,
                        "min_y": min_y,
                        "max_y": max_y,
                    },
                    "lands": map_data,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in get_land_map: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
