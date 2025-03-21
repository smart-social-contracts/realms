from kybra_simple_db import *

class Snapshot(Entity):
    """Entity for storing system snapshots."""
    _entity_type = "snapshot"

    def __init__(self, date: str, data: dict):
        super().__init__()
        self.date = date
        self.data = data

    @classmethod
    def new(cls, date: str, data: dict) -> 'Snapshot':
        snapshot = cls(date=date, data=data)
        snapshot.save()
        return snapshot


def take_snapshot(date: str):
    """Take a snapshot of the current system state."""
    # from core.db import get_all_organizations, get_all_proposals, get_all_tokens, get_all_users
    # TODO: broken

    data = {}

    # Gather organization statistics
    total_num_members = 0
    organizations = {}
    for organization in get_all_organizations():
        organizations[organization.id] = {}
        num_members = len(organization.members)
        num_proposals = 0  # TODO: Add proposal tracking to Organization
        total_num_members += num_members
        organizations[organization.id]["num_members"] = num_members
        organizations[organization.id]["num_proposals"] = num_proposals
        organizations[organization.id]["assets_usd"] = 0  # TODO: Add asset tracking

    data["organizations"] = organizations
    data["total_num_members"] = total_num_members
    data["total_assets_usd"] = 0  # TODO: Add asset tracking

    # total number of users/proposals
    # states and number of user/proposals per state
    # total value of assets per state

    ret = Snapshot.new(date, data)
    return ret
