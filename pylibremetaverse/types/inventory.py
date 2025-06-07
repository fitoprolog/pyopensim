import dataclasses
import datetime
from .custom_uuid import CustomUUID
from .enums import InventoryType, AssetType, SaleType, PermissionMask, InventoryItemFlags

@dataclasses.dataclass
class InventoryBase:
    """Base class for inventory items and folders."""
    uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    parent_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    name: str = ""
    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Owner of this inventory item/folder

    def __str__(self):
        return f"{self.__class__.__name__}(Name='{self.name}', UUID={self.uuid})"

@dataclasses.dataclass
class InventoryFolder(InventoryBase):
    """Represents an inventory folder."""
    preferred_type: AssetType = AssetType.Unknown # Preferred content type for this folder
    version: int = 0 # Incremented when folder contents change
    descendent_count: int = 0 # Number of items and folders within this folder and its subfolders

    def __post_init__(self):
        # Ensure preferred_type is an AssetType enum if an int was passed
        if not isinstance(self.preferred_type, AssetType):
            try: self.preferred_type = AssetType(self.preferred_type)
            except ValueError: self.preferred_type = AssetType.Unknown


@dataclasses.dataclass
class InventoryItem(InventoryBase):
    """Represents an inventory item (not a folder)."""
    asset_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # UUID of the an asset file
    asset_type: AssetType = AssetType.Unknown # Type of the asset pointed to
    inv_type: InventoryType = InventoryType.Unknown # Type of this inventory item itself

    group_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Group that owns this item if group_owned
    group_owned: bool = False # Whether this item is group-owned

    # Permissions
    # C# uses distinct BaseMask, OwnerMask etc. fields.
    # Storing them similarly here. PermissionMask enum defines the bits.
    base_mask: PermissionMask = PermissionMask.ALL
    owner_mask: PermissionMask = PermissionMask.ALL
    group_mask: PermissionMask = PermissionMask.NONE
    everyone_mask: PermissionMask = PermissionMask.NONE
    next_owner_mask: PermissionMask = PermissionMask.ALL # What perms next owner gets on transfer

    sale_price: int = 0 # L$ price if for sale
    sale_type: SaleType = SaleType.NOT_FOR_SALE # How it's for sale

    flags: InventoryItemFlags = InventoryItemFlags.NONE # Special flags for the item
    creation_date: datetime.datetime = dataclasses.field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    description: str = ""
    # crc: int = 0 # CRC of item, used for cache validation with server - not typically set by client directly

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

        # Ensure masks are PermissionMask instances
        for mask_attr in ['base_mask', 'owner_mask', 'group_mask', 'everyone_mask', 'next_owner_mask']:
            val = getattr(self, mask_attr)
            if not isinstance(val, PermissionMask):
                try: setattr(self, mask_attr, PermissionMask(val))
                except ValueError: setattr(self, mask_attr, PermissionMask.NONE)


    @property
    def is_link(self) -> bool:
        """Checks if this item is an inventory link."""
        return bool(self.flags & InventoryItemFlags.LINK)

    # Add other helper properties or methods as needed, e.g., for checking specific permissions.
    def can_copy(self) -> bool: return bool(self.owner_mask & PermissionMask.COPY)
    def can_modify(self) -> bool: return bool(self.owner_mask & PermissionMask.MODIFY)
    def can_transfer(self) -> bool: return bool(self.owner_mask & PermissionMask.TRANSFER)
