import logging
import struct
import dataclasses
import time

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import AssetType, InventoryType, SaleType, PermissionMask
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class UpdateCreateInventoryItemAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID
    TransactionID: CustomUUID # Used to correlate with asset upload or other operations

@dataclasses.dataclass
class UpdateCreateInventoryItemInventoryDataBlock:
    CallbackID: int = 0 # uint32, client sets, server echoes. Often 0.
    FolderID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Parent folder
    AssetID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # UUID of the asset this item represents
    InvType: int = InventoryType.Unknown.value # sbyte
    Type: int = AssetType.Unknown.value      # sbyte (AssetType)
    Name: bytes = b''            # Variable, null-terminated string (max 63 + null)
    Description: bytes = b''     # Variable, null-terminated string (max 127 + null)
    NextOwnerMask: int = PermissionMask.ALL.value # uint32
    OwnerMask: int = PermissionMask.ALL.value     # uint32
    GroupMask: int = PermissionMask.NONE.value    # uint32
    EveryoneMask: int = PermissionMask.NONE.value # uint32
    BaseMask: int = PermissionMask.ALL.value      # uint32
    SalePrice: int = 0           # int32
    SaleType: int = SaleType.NOT_FOR_SALE.value # byte
    CreationDate: int = int(time.time()) # uint32, Unix timestamp
    GroupID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    GroupOwned: bool = False

class UpdateCreateInventoryItemPacket(Packet): # Client -> Server
    """
    Client sends this to create a new inventory item from an existing asset,
    or to update an existing inventory item (though creation is the focus here).
    """
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, transaction_id: CustomUUID,
                 folder_id: CustomUUID, asset_uuid: CustomUUID,
                 inv_type: InventoryType, asset_type: AssetType,
                 name: str, description: str,
                 permissions: dict, # Expects {'base': PM, 'owner': PM, ...}
                 sale_price: int = 0, sale_type: SaleType = SaleType.NOT_FOR_SALE,
                 creation_date_unix: int | None = None,
                 group_id: CustomUUID = CustomUUID.ZERO, group_owned: bool = False,
                 callback_id: int = 0,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.UpdateCreateInventoryItem, header if header else PacketHeader())

        self.agent_data = UpdateCreateInventoryItemAgentDataBlock(
            AgentID=agent_id, SessionID=session_id, TransactionID=transaction_id
        )

        name_bytes = name.encode('utf-8')[:63] + b'\0'
        desc_bytes = description.encode('utf-8')[:127] + b'\0'

        self.inventory_data = UpdateCreateInventoryItemInventoryDataBlock(
            CallbackID=callback_id,
            FolderID=folder_id,
            AssetID=asset_uuid,
            InvType=inv_type.value,
            Type=asset_type.value,
            Name=name_bytes,
            Description=desc_bytes,
            NextOwnerMask=permissions.get('next_owner', PermissionMask.ALL).value,
            OwnerMask=permissions.get('owner', PermissionMask.ALL).value,
            GroupMask=permissions.get('group', PermissionMask.NONE).value,
            EveryoneMask=permissions.get('everyone', PermissionMask.NONE).value,
            BaseMask=permissions.get('base', PermissionMask.ALL).value,
            SalePrice=sale_price,
            SaleType=sale_type.value,
            CreationDate=creation_date_unix if creation_date_unix is not None else int(time.time()),
            GroupID=group_id,
            GroupOwned=group_owned
        )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentDataBlock
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.extend(self.agent_data.TransactionID.get_bytes())

        # InventoryDataBlock
        inv = self.inventory_data
        data.extend(helpers.uint32_to_bytes(inv.CallbackID))
        data.extend(inv.FolderID.get_bytes())
        data.extend(inv.AssetID.get_bytes())
        data.append(struct.pack('<b', inv.InvType)[0]) # sbyte
        data.append(struct.pack('<b', inv.Type)[0])    # sbyte

        data.extend(inv.Name) # Already null-terminated and length-limited
        data.extend(inv.Description) # Already null-terminated and length-limited

        data.extend(helpers.uint32_to_bytes(inv.NextOwnerMask))
        data.extend(helpers.uint32_to_bytes(inv.OwnerMask))
        data.extend(helpers.uint32_to_bytes(inv.GroupMask))
        data.extend(helpers.uint32_to_bytes(inv.EveryoneMask))
        data.extend(helpers.uint32_to_bytes(inv.BaseMask))

        data.extend(helpers.int32_to_bytes(inv.SalePrice))
        data.append(inv.SaleType & 0xFF) # byte
        data.extend(helpers.uint32_to_bytes(inv.CreationDate))
        data.extend(inv.GroupID.get_bytes())
        data.append(1 if inv.GroupOwned else 0) # bool as byte

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive UpdateCreateInventoryItemPacket.")
        return self


# --- UpdateInventoryItemPacket (Server -> Client) ---
# This packet is sent by the server to inform the client about a new or updated inventory item.
# Crucially, it confirms item creation and provides the server-assigned ItemID.

@dataclasses.dataclass
class UpdateInventoryItemAgentDataBlockServer: # Matches C# AgentData block
    AgentID: CustomUUID
    SessionID: CustomUUID # Not always used by client for this packet, but present
    TransactionID: CustomUUID # Matches TransactionID from client's UpdateCreateInventoryItemPacket

@dataclasses.dataclass
class ServerInventoryDataBlock: # Based on C# InventoryData block in UpdateInventoryItem
    ItemID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    ParentID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # FolderID
    CreatorID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    OwnerID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    GroupID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    BaseMask: int = PermissionMask.ALL.value # uint32
    OwnerMask: int = PermissionMask.ALL.value # uint32
    GroupMask: int = PermissionMask.NONE.value # uint32
    EveryoneMask: int = PermissionMask.NONE.value # uint32
    NextOwnerMask: int = PermissionMask.ALL.value # uint32
    GroupOwned: bool = False # u8
    Flags: int = 0 # uint32 (InventoryItemFlags)
    InvType: int = InventoryType.Unknown.value # sbyte
    Type: int = AssetType.Unknown.value # sbyte (AssetType)
    AssetID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    SaleType: int = SaleType.NOT_FOR_SALE.value # u8
    SalePrice: int = 0 # int32
    Name: bytes = b'' # Variable, null-terminated string
    Description: bytes = b'' # Variable, null-terminated string
    CreationDate: int = 0 # int32 (Unix timestamp)
    CRC32: int = 0 # uint32
    CallbackID: int = 0 # uint32 (Should echo what client sent in UpdateCreateInventoryItemPacket)

    # Helper properties for string conversion
    @property
    def name_str(self) -> str: return helpers.bytes_to_string(self.Name)
    @property
    def description_str(self) -> str: return helpers.bytes_to_string(self.Description)


class UpdateInventoryItemPacket(Packet): # Server -> Client
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.UpdateInventoryItem, header if header else PacketHeader()) # Assuming PacketType.UpdateInventoryItem will be added
        self.agent_data = UpdateInventoryItemAgentDataBlockServer(
            AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO, TransactionID=CustomUUID.ZERO
        )
        self.inventory_data_blocks: list[ServerInventoryDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "UpdateInventoryItemPacket":
        initial_offset = offset

        # AgentDataBlock
        self.agent_data.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.SessionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.TransactionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # InventoryDataBlock array
        num_blocks = buffer[offset]; offset += 1
        for _ in range(num_blocks):
            block = ServerInventoryDataBlock()
            block.ItemID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            block.ParentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            block.CreatorID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            block.OwnerID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            block.GroupID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

            block.BaseMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            block.OwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            block.GroupMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            block.EveryoneMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            block.NextOwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4

            block.GroupOwned = buffer[offset] != 0; offset += 1
            block.Flags = helpers.bytes_to_uint32(buffer, offset); offset += 4

            block.InvType = struct.unpack_from('<b', buffer, offset)[0]; offset += 1
            block.Type = struct.unpack_from('<b', buffer, offset)[0]; offset += 1

            block.AssetID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

            block.SaleType = buffer[offset]; offset += 1
            block.SalePrice = helpers.bytes_to_int32(buffer, offset); offset += 4

            # Name (variable length string)
            name_end = buffer.find(b'\0', offset)
            if name_end == -1: raise ValueError("No null terminator for Name string in ServerInventoryDataBlock")
            block.Name = buffer[offset:name_end]; offset = name_end + 1

            # Description (variable length string)
            desc_end = buffer.find(b'\0', offset)
            if desc_end == -1: raise ValueError("No null terminator for Description string in ServerInventoryDataBlock")
            block.Description = buffer[offset:desc_end]; offset = desc_end + 1

            block.CreationDate = helpers.bytes_to_int32(buffer, offset); offset += 4 # C# uses int for this, though it's a Unix timestamp
            block.CRC32 = helpers.bytes_to_uint32(buffer, offset); offset += 4
            block.CallbackID = helpers.bytes_to_uint32(buffer, offset); offset += 4

            self.inventory_data_blocks.append(block)

        if offset - initial_offset != length:
            logger.warning(f"UpdateInventoryItemPacket: Expected to read {length} bytes, but read {offset - initial_offset}")
        return self

    def to_bytes(self) -> bytes: # Server -> Client, client does not send this
        logger.error("Client does not send UpdateInventoryItemPacket.")
        return b''
