from typing import List, Optional

from core.entity import GGGEntity
from kybra_simple_db import *

from .wallet import Wallet


class User(GGGEntity):
    # principal = String(min_length=1)
    # organizations = ManyToMany('Organization', 'members')
    wallet = OneToOne(["Wallet"], "controller")

    @classmethod
    def new(cls, principal: str, **kwargs) -> "User":
        kwargs["_id"] = principal
        entity = cls(**kwargs)
        entity.wallet = (
            Wallet.new()
        )  # TODO: should I initialize everything with kwargs... before cls(...)?
        return entity

    def join(self, organization: "Organization") -> None:
        organization.append(self)  # TODO: can I do that? or just
