from kybra_simple_db import *
from .access_control import requires_token




class AutoDecorate:
    def __init_subclass__(cls, **kwargs):
        print('***** __init_subclass__')
        super().__init_subclass__(**kwargs)
        for name, method in cls.__dict__.items():
            if callable(method) and not name.startswith('__'):
                # Apply the decorator with a default token name based on the method
                setattr(cls, name, requires_token(f"{cls.__name__}_{name}")(method))
    
    def __init__(self, **kwargs):
        self.require_token_funcs = {}


class GGGEntity(Entity, TimestampedMixin, AutoDecorate):
    pass