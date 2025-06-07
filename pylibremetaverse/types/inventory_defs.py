import dataclasses
import datetime
import uuid # Standard UUID for compatibility if needed, though CustomUUID is primary

from .custom_uuid import CustomUUID
# Enums will be imported from .enums via types.__init__ usually, or directly if preferred
from .enums import InventoryType, AssetType, SaleType, PermissionMask, InventoryItemFlags

@dataclasses.dataclass
class InventoryBase:
    """Base class for all inventory items and folders."""
    uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    parent_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    name: str = ""
    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)

    def __str__(self):
        return f"{self.__class__.__name__}(Name='{self.name}', UUID={self.uuid})"

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}' uuid={self.uuid} parent={self.parent_uuid} owner={self.owner_id}>"


@dataclasses.dataclass
class InventoryFolder(InventoryBase):
    """Represents an inventory folder."""
    preferred_type: AssetType = AssetType.Unknown
    version: int = 0
    descendent_count: int = 0
    children: list[CustomUUID] = dataclasses.field(default_factory=list) # New field for direct children UUIDs

    def __post_init__(self):
        if not isinstance(self.preferred_type, AssetType):
            try: self.preferred_type = AssetType(self.preferred_type)
            except ValueError: self.preferred_type = AssetType.Unknown


@dataclasses.dataclass
class InventoryItem(InventoryBase):
    """Represents an inventory item (an asset instance)."""
    asset_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    asset_type: AssetType = AssetType.Unknown
    inv_type: InventoryType = InventoryType.Unknown

    group_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    group_owned: bool = False

    creator_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Often different from owner_id

    # Permissions
    base_mask: PermissionMask = PermissionMask.ALL
    owner_mask: PermissionMask = PermissionMask.ALL
    group_mask: PermissionMask = PermissionMask.NONE
    everyone_mask: PermissionMask = PermissionMask.NONE
    next_owner_mask: PermissionMask = PermissionMask.ALL

    sale_price: int = 0
    sale_type: SaleType = SaleType.NOT_FOR_SALE

    flags: InventoryItemFlags = InventoryItemFlags.NONE
    creation_date: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc) # Default to epoch
    )
    description: str = ""
    crc: int = 0 # CRC hash of the item, used by server for cache coherency

    def __post_init__(self):
        # Ensure enum types if integers were passed
        if not isinstance(self.asset_type, AssetType):
            try: self.asset_type = AssetType(self.asset_type)
            except ValueError: self.asset_type = AssetType.Unknown
        if not isinstance(self.inv_type, InventoryType):
            try: self.inv_type = InventoryType(self.inv_type)
            except ValueError: self.inv_type = InventoryType.Unknown
        if not isinstance(self.sale_type, SaleType):
            try: self.sale_type = SaleType(self.sale_type)
            except ValueError: self.sale_type = SaleType.NOT_FOR_SALE
        if not isinstance(self.flags, InventoryItemFlags):
            try: self.flags = InventoryItemFlags(self.flags)
            except ValueError: self.flags = InventoryItemFlags.NONE

        for mask_attr in ['base_mask', 'owner_mask', 'group_mask', 'everyone_mask', 'next_owner_mask']:
            val = getattr(self, mask_attr)
            if not isinstance(val, PermissionMask):
                try: setattr(self, mask_attr, PermissionMask(val))
                except ValueError: setattr(self, mask_attr, PermissionMask.NONE)

    @property
    def is_link(self) -> bool: return bool(self.flags & InventoryItemFlags.LINK)
    def can_copy(self) -> bool: return bool(self.owner_mask & PermissionMask.COPY)
    def can_modify(self) -> bool: return bool(self.owner_mask & PermissionMask.MODIFY)
    def can_transfer(self) -> bool: return bool(self.owner_mask & PermissionMask.TRANSFER)

    @property
    def wearable_type(self) -> 'WearableType | None':
        """
        Attempts to determine the WearableType of this item.
        This relies on the item's inv_type matching a WearableType enum value.
        Returns None if inv_type does not correspond to a valid WearableType.
        """
        from .enums import WearableType # Late import to avoid circular dependency at module load time
        try:
            # If self.inv_type is already an enum member, get its value
            inv_type_val = self.inv_type.value if isinstance(self.inv_type, enum.Enum) else self.inv_type
            return WearableType(inv_type_val)
        except ValueError:
            # If inv_type is not a valid WearableType (e.g., it's Folder, Object, etc.)
            return None
