import dataclasses
import logging
from typing import Dict, Any # For type hints

from .asset_base import Asset
from pylibremetaverse.types import CustomUUID, AssetType, WearableType, PermissionMask, SaleType
from pylibremetaverse.structured_data import parse_llsd_xml, OSDMap, OSDString, OSDInteger, OSDArray, OSDBoolean, OSDReal, OSDUUID

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class AssetWearable(Asset):
    """Represents a wearable asset (clothing, body parts)."""
    wearable_type: WearableType = WearableType.Shape # Default, will be parsed
    permissions: Dict[str, PermissionMask] = dataclasses.field(default_factory=dict)
    sale_info: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Textures: key is texture index (int) or special name (string), value is texture asset UUID
    textures: Dict[int | str, CustomUUID] = dataclasses.field(default_factory=dict)
    # Parameters: key is visual parameter ID (int), value is float (0-1)
    parameters: Dict[int, float] = dataclasses.field(default_factory=dict)

    # Specific to AssetClothing (inherits from AssetWearable in C#)
    # For AssetBodypart, these might not all be relevant or present.
    # This class tries to cover both by making them optional.

    def __post_init__(self):
        super().__post_init__()
        # asset_type will be set by AssetManager before calling from_bytes
        # Defaulting wearable_type based on asset_type if not parsed
        if self.asset_type == AssetType.Clothing and self.wearable_type == WearableType.Shape: # Invalid default for clothing
            self.wearable_type = WearableType.Shirt # A more common default for clothing
        elif self.asset_type == AssetType.Bodypart and self.wearable_type != WearableType.Shape:
             # Bodyparts are usually Shape, Skin, Hair, Eyes. If not Shape, might be an issue or specific type.
             pass


    def from_bytes(self, data: bytes) -> bool:
        """
        Parses wearable asset data from its raw byte representation (LLSD XML).
        """
        super().from_bytes(data) # Stores raw_data
        self.loaded_successfully = False

        try:
            osd = parse_llsd_xml(data)
            if not isinstance(osd, OSDMap):
                logger.warning(f"AssetWearable {self.asset_id}: Parsed LLSD is not an OSDMap ({type(osd)}).")
                return False

            self.name = osd.get('name', OSDString(self.name)).as_string()
            self.description = osd.get('description', OSDString(self.description)).as_string()

            # Type: maps to WearableType enum
            self.wearable_type = WearableType(osd.get('type', OSDInteger(self.wearable_type.value)).as_integer())

            # Permissions
            perms_osd = osd.get('permissions')
            if isinstance(perms_osd, OSDMap):
                self.permissions['base_mask'] = PermissionMask(perms_osd.get('base_mask', OSDInteger(0)).as_integer())
                self.permissions['owner_mask'] = PermissionMask(perms_osd.get('owner_mask', OSDInteger(0)).as_integer())
                self.permissions['group_mask'] = PermissionMask(perms_osd.get('group_mask', OSDInteger(0)).as_integer())
                self.permissions['everyone_mask'] = PermissionMask(perms_osd.get('everyone_mask', OSDInteger(0)).as_integer())
                self.permissions['next_owner_mask'] = PermissionMask(perms_osd.get('next_owner_mask', OSDInteger(0)).as_integer())
                # creator_id, owner_id, last_owner_id, group_id, group_owned are also in permissions block in some viewers
                # For now, relying on inventory item for these if not directly on asset.

            # Sale Info
            sale_osd = osd.get('sale_info') # C# uses 'sale-info'
            if not sale_osd: sale_osd = osd.get('sale-info')
            if isinstance(sale_osd, OSDMap):
                self.sale_info['sale_type'] = SaleType(sale_osd.get('sale_type', OSDInteger(0)).as_integer())
                self.sale_info['sale_price'] = sale_osd.get('sale_price', OSDInteger(0)).as_integer()

            # Parameters (Visual Params)
            params_osd = osd.get('parameters')
            if isinstance(params_osd, OSDMap):
                for key_osd, val_osd in params_osd.items():
                    try:
                        param_id = int(key_osd) # Should be integer visual param ID
                        # Value can be int (0-255) or float (0-1). Normalize to float 0-1.
                        if isinstance(val_osd, OSDInteger):
                            self.parameters[param_id] = float(val_osd.as_integer()) / 255.0
                        elif isinstance(val_osd, OSDReal):
                            self.parameters[param_id] = val_osd.as_real()
                    except ValueError:
                        logger.warning(f"AssetWearable {self.asset_id}: Could not parse parameter ID '{key_osd}'.")

            # Textures
            textures_osd = osd.get('textures')
            if isinstance(textures_osd, OSDMap):
                for key_osd, val_osd in textures_osd.items():
                    try:
                        # Key can be an integer string (texture index) or a special name (e.g. "baked")
                        texture_key: int | str
                        try: texture_key = int(key_osd)
                        except ValueError: texture_key = key_osd # Use as string if not int

                        if isinstance(val_osd, OSDUUID):
                            self.textures[texture_key] = val_osd.as_uuid()
                        elif isinstance(val_osd, OSDString)): # Sometimes UUIDs might be strings
                             self.textures[texture_key] = CustomUUID(val_osd.as_string())
                    except (ValueError, TypeError):
                        logger.warning(f"AssetWearable {self.asset_id}: Could not parse texture entry '{key_osd}': '{val_osd}'.")

            self.loaded_successfully = True

        except Exception as e:
            logger.exception(f"Failed to parse AssetWearable LLSD XML for {self.asset_id}: {e}")
            self.loaded_successfully = False

        return self.loaded_successfully

    def __str__(self):
        perm_str = f"Perms(Owner: {self.permissions.get('owner_mask', '')!s})" if self.permissions else "Perms(N/A)"
        return (f"{super().__str__()} WearableType={self.wearable_type.name}, {perm_str}, "
                f"Textures={len(self.textures)}, Params={len(self.parameters)}")
