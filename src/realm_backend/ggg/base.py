"""Base module providing core initialization and database functionality.

This module contains the core initialization logic for the GGG framework and
provides access to the underlying database functionality.
"""

import inspect
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import ggg
from core.access_control import context_caller
from core.execution import contains_function
# from core.db import Database, Entity
from core.logger import log
from core.system_time import get_system_time
from core.token_factory import token_factory
from core.token_icrc1 import TokenICRC1
from ggg.extension_code import ExtensionCode
from ggg.token import Token
from kybra_simple_db import *


def initialize() -> None:
    """Initialize the GGG framework with default entities and configurations.

    This function performs the following setup:
    1. Creates the default user
    2. Sets up default extension code
    3. Creates initial tokens
    4. Initializes the world
    """

    def create_first_user():
        ggg.User.new("aaa-0")

    def create_default_extension_code():
        # import ggg.default_extension_code
        # ExtensionCode.new(inspect.getsource(ggg.default_extension_code).strip(), 'DEFAULT_EXTENSION_CODE_ORGANIZATION')
        # this_folder = os.path.dirname(os.path.abspath(__file__))
        # print('this_folder', this_folder)
        # default_extension_code = open(os.path.join(this_folder, 'default_extension_code.py')).read().strip()
        # print('default_extension_code', default_extension_code)
        ExtensionCode.new(
            ggg.extension_code.DEFAULT_EXTENSION_CODE_ORGANIZATION,
            _id="DEFAULT_EXTENSION_CODE_ORGANIZATION",
        )
        ExtensionCode.new(
            ggg.extension_code.DEFAULT_EXTENSION_CODE_TOKEN,
            _id="DEFAULT_EXTENSION_CODE_TOKEN",
        )

    def create_tokens():

        for ccy_data in [
            # ("BTC", "Bitcoin", None),
            (
                "ckBTC",
                "Chain-Key Bitcoin",
                "bkyz2-fmaaa-aaaaa-qaaaq-cai",
            ),  # TODO: check principal
            # ("ETH", "Ethereum"),
            # ("ICP", "Internet Computer Protocol"),
            # ("CKBTC", "Chain-Key Bitcoin"),
            # ("CKETH", "Chain-Key Ethereum"),
            # ("CUSD", "CUSD"),
        ]:
            (symbol, name, principal) = ccy_data  # TODO: **ccy_data ?
            log("Creating token {}...".format(symbol))

            if principal:
                token_factory(symbol, "TokenICRC1", principal=principal, name=name)
            else:
                token_factory(symbol, "TokenInternal")

    # def create_realm():
    #     # The address of the first realm in database is set to the principal of the canister the platform is running on
    #     real_name = ''
    #     try:
    #         from kybra import ic
    #         if hasattr(ic, '_kybra_ic'):
    #             pass # TODO
    #     except ImportError:
    #         import uuid
    #         real_name = str(uuid.uuid4())
    #     ggg.Realm(real_name)

    # def create_world():
    #     ggg.World.new("Earth")

    # context_caller.reset()

    create_first_user()
    create_default_extension_code()
    create_tokens()
    # create_world()

    # print(Entity.db().dump_json())
    # world = ggg.World.instances()[0]
    # print(world.name)
    # print(world.to_dict())

    # world.some_method()

    print("initialized")

    # # Create the main state organization
    # state = ggg.Organization.new('state')
    # government = ggg.Organization.new('Government')
    # tax_department = ggg.Organization.new('Tax Department')

    # # Link the organizations
    # state.add_member(government)
    # government.add_member(tax_department)

    # # Create users and assign identities
    # alice = ggg.User.new('alice_identity')
    # bob = ggg.User.new('bob_identity')

    # # Join users to the state
    # state.add_member(alice)
    # state.add_member(bob)


def universe(recursive=True) -> dict:
    from core.token_icrc1 import TokenICRC1
    from core.token_internal import TokenInternal
    from ggg.extension_code import ExtensionCode
    # from ggg.state import State
    from ggg.organization import Organization
    from ggg.proposal import Proposal
    from ggg.resources import LandToken
    from ggg.token import Token
    from ggg.user import User
    from ggg.wallet import Wallet
    from ggg.world import World

    return {
        "tokens": [i.to_dict() for i in Token.instances()],
        "tokenICRC1s": [i.to_dict() for i in TokenICRC1.instances()],
        "landTokens": [i.to_dict() for i in LandToken.instances()],
        "extensions": [i.to_dict() for i in ExtensionCode.instances()],
        "users": [i.to_dict() for i in User.instances()],
        "organizations": [i.to_dict() for i in Organization.instances()],
        "wallets": [i.to_dict() for i in Wallet.instances()],
        "proposals": [i.to_dict() for i in Proposal.instances()],
        "worlds": [i.to_dict() for i in World.instances()],
    }


def audit() -> dict:
    return db
