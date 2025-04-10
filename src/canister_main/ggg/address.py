from typing import Optional
from kybra_simple_db import *
from core.system_time import get_system_time
import ggg


class Address(Entity):
    token = ManyToOne(['Token'], 'address')
    address_id = String()

    @classmethod
    def new(cls, token: ggg.Token, address_id: str,  **kwargs) -> 'Address':
        address = cls(**kwargs)
        address.token = token
        address.address_id = address_id
        return address
 