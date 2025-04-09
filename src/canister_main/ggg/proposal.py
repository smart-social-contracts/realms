from kybra_simple_db import *
from ggg.extension_code import ExtensionCode
from core.entity import GGGEntity
class Proposal(GGGEntity):
    """Represents a proposal for organizational governance."""
    _entity_type = "proposal"

    NOT_SUBMITTED = "Not Submitted"
    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    VOTING_YAY = "Yay"
    VOTING_NAY = "Nay"
    VOTING_ABSTAIN = "Abstain"
    VOTING_NOT = "Did Not Vote"

    # def __init__(self, title: str, source_code: str, deadline: int):
    #     super().__init__()
    #     self.title = title
    #     self.deadline = deadline
    #     self.status = Proposal.NOT_SUBMITTED
    #     self.token_balances = {}
    #     self.votes = {}
    #     self.vote_counts = {}
    #     self.result = None
    #     self.organization = None
    #     self.extension_code = ExtensionCode.new(source_code)

    @classmethod
    def new(cls, title: str, source_code: str, deadline: int, **kwargs) -> 'Proposal':
        entity = cls(**kwargs)
        entity.title = title
        entity.extension_code = ExtensionCode.new(source_code)
        entity.deadline = deadline
        return entity


    def submit(self, organization):
        """Submit the proposal to an organization.

        Args:
            organization: The organization to submit the proposal to
        """
        self.organization = organization
        self.token_balances = organization.token.balances.copy()
        self.tokens_total = sum(self.token_balances.values())
        self.token_id = organization.token.id
        self.status = Proposal.SUBMITTED
        self.save()
        self.status = Proposal.SUBMITTED

    def vote(self, address, vote_sign):
        # TODO: use caller() too instead of just address
        if address not in self.token_balances.keys():
            raise Exception("Address %s is not eligible to participate in this voting because balance of token %s is zero" % (address, self.token_id))

        if vote_sign not in [self.VOTING_YAY, self.VOTING_ABSTAIN, self.VOTING_ABSTAIN]:
            raise Exception("Unknown vote sign")

        if address in self.votes:
            previous_vote_sign = self.votes[address]
            self.vote_counts[previous_vote_sign] = self.vote_counts.get(previous_vote_sign, 0) - self.token_balances[address]
        self.votes[address] = vote_sign
        self.vote_counts[vote_sign] = self.vote_counts.get(vote_sign, 0) + self.token_balances[address]
        self.save()
