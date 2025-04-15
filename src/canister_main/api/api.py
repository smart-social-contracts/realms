"""API implementation using Kybra Simple DB."""

from typing import List, Dict, Optional
from pprint import pprint

import ggg

# from core.db import (
#     User,
#     Organization,
#     Token,
#     Proposal,
#     get_user,
#     get_all_users,
#     get_organization,
#     get_all_organizations,
#     get_token,
#     get_all_tokens,
#     get_proposal
# )


def get_organization_list():
    """
    Get a list of all organizations in the system.

    Returns:
        List[Dict]: A list of organization dictionaries containing basic information
    """
    return [org.to_dict() for org in ggg.Organization.instances()]


def get_organization_data(organization_id: str):
    """
    Get detailed data for a specific organization.

    Args:
        organization_id (str): The ID of the organization to retrieve

    Returns:
        Optional[Dict]: Organization data dictionary containing:
            - Basic organization info
            - Token details
            - Member list
    """
    org = ggg.Organization.load(organization_id)
    if not org:
        return None
    
    data = org.to_dict()
    
    # Add token information
    for token_id in org.tokens:
        token = get_token(token_id)
        if token:
            if 'tokens' not in data:
                data['tokens'] = {}
            data['tokens'][token.id] = token.to_dict()
    
    return data


def create_user(name: str):
    """
    Create a new user in the system.

    Args:
        name (str): Name of the user

    Returns:
        Dict: The newly created user's data
    """
    user = User(name=name)
    user.save()
    return user.to_dict()


def get_user_data(user_id: str):
    """
    Get detailed data for a specific user.

    Args:
        user_id (str): The ID of the user to retrieve

    Returns:
        Optional[Dict]: User data dictionary if found, None otherwise
    """
    user = get_user(user_id)
    if not user:
        return None
    return user.to_dict()


def get_user_list():
    """
    Get a list of all users in the system.

    Returns:
        List[Dict]: A list of user dictionaries containing basic information
    """
    users = get_all_users()
    return [user.to_dict() for user in users]


def get_token_data(token_id: str):
    """
    Get detailed data for a specific token.

    Args:
        token_id (str): The ID/symbol of the token to retrieve

    Returns:
        Optional[Dict]: Token data dictionary containing:
            - Basic token info (symbol, name)
            - Total supply
            - Holder information
    """
    token = get_token(token_id)
    if not token:
        return None
    return token.to_dict()


def get_token_list():
    """
    Get a list of all tokens in the system.

    Returns:
        List[Dict]: A list of token dictionaries containing basic information:
            - id
            - name
            - symbol
            - total_supply
            - holders
    """
    tokens = get_all_tokens()
    return [token.to_dict() for token in tokens]


def get_token_transactions(token_id: str, address: str = None, limit: int = 100):
    """
    Get transaction history for a specific token.

    Args:
        token_id (str): The ID/symbol of the token
        address (str, optional): Filter transactions by address
        limit (int, optional): Maximum number of transactions to return

    Returns:
        Optional[Dict]: Dictionary containing:
            - token_symbol: str
            - transactions: List[Dict] where each Dict contains:
                - id: str
                - from_address: Optional[str]
                - to_address: Optional[str]
                - amount: float
                - timestamp: float
    """
    token = get_token(token_id)
    if not token:
        return None
    
    # Note: Transaction history is not implemented in the current version
    return {
        'token_symbol': token.symbol,
        'transactions': []
    }


def get_proposal_data(proposal_id: str):
    """
    Get detailed data for a specific proposal.

    Args:
        proposal_id (str): The ID of the proposal to retrieve

    Returns:
        Optional[Dict]: Proposal data dictionary if found, None otherwise
    """
    proposal = get_proposal(proposal_id)
    if not proposal:
        return None
    return proposal.to_dict()


def user_join_organization(user_principal: str):
    """
    Add a user to the organization/realm based on their principal ID.
    
    Args:
        user_principal (str): The principal ID of the user to add
        
    Returns:
        bool: True if user was successfully added, False otherwise
    """
    # In a real implementation, you would add the user to your organization's members list
    # For example:
    # organization = ggg.Organization.get_default()
    # if organization:
    #     organization.add_member(user_principal)
    #     organization.save()
    #     return True
    # return False
    
    # For now, simply return success
    print(f"User with principal {user_principal} joined the organization")
    return True


def get_realm_name():
    """
    Get the name of the realm/organization.
    
    Returns:
        str: The name of the realm/organization
    """
    # In a real implementation, you would get this from your organization data
    # For example:
    # organization = ggg.Organization.get_default()
    # if organization:
    #     return organization.name
    # return "Default Realm"
    
    # For now, return a default name
    return "Smart Social Contracts Realm"
