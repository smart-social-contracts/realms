from ggg.token import Token
from ggg.world import Land
from typing import Optional

class LandToken(Token):
    UNIT_OF_LAND = 1  # Define the fixed surface area represented by 1 token

    @classmethod
    def new(cls, land: Land, symbol: str, name: Optional[str] = None):
        """
        Create a new LandToken instance with default values for symbol and name.
        """
        obj = super().new(symbol=symbol, name=name)
        obj.__dict__['type'] = 'LandToken'  # Set the correct type
        obj.add_relation("land", "token", land)
        obj = obj.save()  # Save after setting type
        return obj

    def mint(self, address, surface_area, metadata=None):
        """
        Mint tokens based on the surface area and associate metadata.

        Args:
            address (str): The address receiving the tokens.
            surface_area (float): The total surface area being minted (in units).
            metadata (dict, optional): Additional metadata to associate with the land.
        """
        # Calculate the number of tokens based on the surface area
        tokens_to_mint = surface_area / self.UNIT_OF_LAND

        if tokens_to_mint <= 0 or not tokens_to_mint.is_integer():
            raise ValueError("Surface area must map to a positive, whole number of tokens.")

        # Use the base class's mint method
        super().mint(
            address=address,
            amount=int(tokens_to_mint),
            metadata={**metadata, "surface_area": surface_area} if metadata else {"surface_area": surface_area},
        )

    def to_dict(self):
        """Override to_dict to ensure type field is preserved"""
        ret = super().to_dict()
        ret['type'] = 'LandToken'
        return ret

    @property
    def land(self):
        return self.get_relations(Land, "land")[0]
