from typing import Any

from ggg.organization import Organization


def organization_register(principal: str) -> dict[str, Any]:
    organization = Organization[principal]
    if not organization:
        organization = Organization(_id=principal)
    else:
        raise Exception("Organization already registered")

    return {"principal": organization._id}


def organization_get(principal: str) -> dict[str, Any]:
    organization = Organization[principal]
    return {"principal": organization._id}


def organization_list() -> dict[str, Any]:
    return {
        "organizations": [
            organization.serialize() for organization in Organization.instances()
        ]
    }
