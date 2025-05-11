from typing import Any, Dict, Optional

from core.entity import GGGEntity
from kybra_simple_db import *


class World(GGGEntity):
    name = String(min_length=1, max_length=256)
    description = String(max_length=1024)

    @classmethod
    def new(cls, name: str, description: Optional[str] = None, **kwargs) -> "World":
        entity = cls(**kwargs)
        entity.name = name
        entity.description = description
        return entity

    def some_method(self):
        print("some_method")


class Land(Entity):
    """Represents a piece of land in a virtual world."""

    _entity_type = "land"

    # def __init__(self, coordinates: Dict[str, Any], world: World, description: Optional[str] = None):
    #     super().__init__()
    #     self.coordinates = coordinates
    #     self.description = description
    #     self.world_id = world.id

    @classmethod
    def new(
        cls,
        coordinates: Dict[str, Any],
        world: World,
        description: Optional[str] = None,
        **kwargs
    ) -> "Land":
        entity = cls(**kwargs)
        entity.coordinates = coordinates
        entity.description = description
        entity.world = world
        return entity
