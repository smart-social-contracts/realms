
from kybra_simple_db import *
from typing import Optional

class TokenInternal(Entity, TimestampedMixin):

    token_type = String(default='TokenInternal')
    token_core = OneToOne(['Token'], 'token')
    total_supply = String(default='0')
    

    @classmethod
    def new(cls):
        return TokenInternal()

