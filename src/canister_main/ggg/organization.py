"""Organization management module for the GGG framework.

This module provides the Organization class for managing decentralized
organizations with support for proposals, tokens, and extensions.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from kybra_simple_db import *
from core.execution import contains_function, run_code
from core.system_time import get_system_time
from core.token_factory import token_factory
from core.access_control import requires_owner

from .proposal import Proposal
from .wallet import Wallet
from .extension_code import ExtensionCode
from .token import Token


class Organization(Entity, TimestampedMixin):
    """Represents a decentralized organization with governance capabilities.

    An organization has its own token, wallet, and can execute proposals through
    extension code. It supports member management and organizational operations.
    """

    name = String(min_length=3, max_length=256)
    description = String(max_length=256)
    # token = ManyToOne(['Token'], 'holder')
    extension_code = ManyToOne(['ExtensionCode'], 'programmable_entity')
    wallet = OneToOne(['Wallet'], 'controller')
    proposals = OneToMany("Proposal", "organization")

    # def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
    #     Entity.__init__(self, {'name': name, 'description': description})
    #     TimestampedMixin.__init__(self)
    #     wallet = Wallet()
    #     self.wallet = wallet

    # def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
    #     Entity.__init__(self)
    #     TimestampedMixin.__init__(self)

    #     self.description = description
    #     self.wallet = None
    #     self.token = None
    #     self.extension_code = None
    #     self.members = []
    #     self.proposals = []

    @classmethod
    def new(cls, name: str, description: Optional[str] = "") -> 'Organization':
        entity = cls(name=name, description=description)

        # Create and associate wallet
        wallet = Wallet.new()
        entity.wallet = wallet

        # Create and associate organization token
        token = token_factory(f"organization_{entity._id}" , "TokenInternal")

        wallet.create_address(token)
        # entity.token.owner = wallet.address(entity.token)

        # Set default extension code
        entity.extension_code = ExtensionCode['DEFAULT_EXTENSION_CODE_ORGANIZATION']
        # entity.add_relation("extension_code", "organizations", extension_code)

        return entity

    def run(self, function_name: str, function_signature: str = "",
            locals: Dict[str, Any] = {}) -> Any:
        """Run a function from the organization's extension code.

        Args:
            function_name: Name of the function to run
            function_signature: Optional signature for the function
            locals: Local variables to pass to the function

        Returns:
            Any: Result of the function execution
        """
        # extension_codes = self.extension_code.get_extension()
        # print('extension_codes', extension_codes)
        # extension_code = ExtensionCode.get_extension(function_name, extension_codes[::-1])

        print('function_name', function_name)
        print('function_signature', function_signature)
        print('locals', locals)
        return self.extension_code.run(function_name, function_signature, locals)

    @requires_owner()
    def add_member(self, member: Union['Organization', 'User']) -> None:
        """Add a member to this organization.

        Args:
            member: Organization or User to add as a member
            
        Raises:
            Exception: If caller is not the owner
        """
        hook_result = self.run(
            "hook_join",
            "organization=organization,joiner=joiner",
            locals={"organization": self, "joiner": member}
        )

        # TODO: implement
        pass
        # Mint 1 token unit to the new member's wallet
        # token = self.token
        # if token and member.wallet:
        #     member_address = member.wallet.get_address(token)
        #     token.mint(member_address, 1)

    def has_member(self, member: Union['Organization', 'User']) -> bool:
        """Check if an organization or user is a member of this organization.

        Args:
            member: Organization or User to check membership for

        Returns:
            bool: True if the member has at least 1 organization token unit
        """
        token = self.token
        if not token or not member.wallet:
            return False

        member_address = member.wallet.get_address(token)
        balance = token.balance_of(member_address)
        return balance >= 1

    @property
    def extension(self) -> Optional[ExtensionCode]:
        """Get the organization's current extension code."""
        extension_codes = self.get_relations(ExtensionCode, "extension_code")
        return extension_codes[-1] if extension_codes else None  # TODO: IMPORTANT! resolve this... remove_relation needed?

    @requires_owner()
    @extension.setter
    def extension(self, source_code: str) -> None:
        """Set new extension code for the organization.

        Args:
            source_code: Source code for the new extension
            
        Raises:
            Exception: If caller is not the owner
        """
        print('extension.setter')
        print('source_code', source_code, '.')
        extension_code = ExtensionCode.new(source_code)
        self.add_relation("extension_code", "organizations", extension_code)
        print('self.relations', self.relations)


    def check_proposals(self) -> List[Proposal]:
        """Check and update status of all pending proposals."""
        now = get_system_time()
        proposals_processed = []

        for proposal in self.proposals:
            if proposal.status == Proposal.SUBMITTED and proposal.deadline < now:
                proposals_processed.append(proposal)

                yay_votes = proposal.vote_counts.get(Proposal.VOTING_YAY, 0)
                nay_votes = proposal.vote_counts.get(Proposal.VOTING_NAY, 0)

                if yay_votes > nay_votes:
                    proposal.status = Proposal.APPROVED
                    extension_code = proposal.get_relations(ExtensionCode, "extension_code")[0]
                    proposal.result = extension_code.run(locals={"organization": self})
                else:
                    proposal.status = Proposal.REJECTED

        return proposals_processed

    @requires_owner()
    def spinoff(self, id: str) -> 'Organization':
        """Create a new organization as a spinoff.

        Args:
            id: Identifier for the new organization

        Returns:
            Organization: The newly created spinoff organization
            
        Raises:
            Exception: If caller is not the owner
        """
        new_org = Organization.new(id)
        self.add_relation("spun_offs", "spun_from", new_org)
        return new_org

    @requires_owner()
    def merge(self, target: 'Organization') -> None:
        """Merge this organization into a target organization.

        Args:
            target: Organization to merge into
            
        Raises:
            Exception: If caller is not the owner
        """
        # Transfer members
        for member in self.get_relations(EntityLayer, "members"):
            target.add_member(member)

        # Transfer assets through wallet
        if self.wallet and target.wallet and self.token and target.token:
            source_address = self.wallet.get_address(self.token)
            target_address = target.wallet.get_address(target.token)
            balance = self.token.balance_of(source_address)

            if balance > 0:
                self.token.transfer(source_address, target_address, balance)

