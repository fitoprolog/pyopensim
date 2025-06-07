import dataclasses
from pylibremetaverse.types import CustomUUID, AssetType

@dataclasses.dataclass
class Asset:
    """Base class for all asset types."""
    asset_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    asset_type: AssetType = AssetType.Unknown
    name: str = ""  # Often derived from inventory item name, not part of raw asset data for all types
    description: str = "" # Often from inventory item, not always in asset data
    raw_data: bytes = b""
    loaded_successfully: bool = False

    def __post_init__(self):
        # Ensure asset_type is an enum member if an int was passed
        if not isinstance(self.asset_type, AssetType):
            try:
                self.asset_type = AssetType(self.asset_type)
            except ValueError:
                self.asset_type = AssetType.Unknown # Default if conversion fails

    def from_bytes(self, data: bytes) -> bool:
        """
        Populates asset fields from raw byte data.
        Base implementation stores raw data and marks as loaded.
        Subclasses should override this to perform actual parsing.
        """
        self.raw_data = data
        self.loaded_successfully = True # Base assumption, subclasses might fail parsing
        return self.loaded_successfully

    def __str__(self):
        return f"{self.__class__.__name__}(ID={self.asset_id}, Type={self.asset_type.name}, Loaded={self.loaded_successfully}, DataSize={len(self.raw_data)})"

    def __repr__(self):
        return f"<{self.__class__.__name__} asset_id={self.asset_id!r} asset_type={self.asset_type!r} loaded_successfully={self.loaded_successfully}>"
