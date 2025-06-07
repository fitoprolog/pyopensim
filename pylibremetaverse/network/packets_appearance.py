import logging
import struct
import dataclasses

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import WearableType # For WearableDataBlock
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

# --- AgentWearablesRequestPacket (Client -> Server) ---
@dataclasses.dataclass
class AgentWearablesRequestAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID

class AgentWearablesRequestPacket(Packet):
    """Client requests its current wearable appearance from the server."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.AgentWearablesRequest, header if header else PacketHeader())
        self.agent_data = AgentWearablesRequestAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.header.reliable = True # Typically reliable

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData block
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("AgentWearablesRequestPacket.from_bytes_body should not be called on client.")
        return self


# --- AgentWearablesUpdatePacket (Server -> Client) ---
@dataclasses.dataclass
class AgentWearablesUpdateAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID # Note: C# packet has AgentID, SerialNum, VisualVersion. SessionID might not be here.
                         # For now, keeping AgentID/SessionID as common pattern.
                         # If SerialNum/VisualVersion needed, adjust.
    SerialNum: int = 0 # u32, version number for this update
    VisualVersion: int = 0 # u8, version of visual params

@dataclasses.dataclass
class WearableDataBlock:
    ItemID: CustomUUID
    AssetID: CustomUUID
    WearableType: int # Actually u8, maps to WearableType enum

@dataclasses.dataclass
class VisualParamBlock:
    ParamValue: int # Actually u8

class AgentWearablesUpdatePacket(Packet):
    """Server sends this with the agent's current wearable items and visual parameters."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.AgentWearablesUpdate, header if header else PacketHeader())
        self.agent_data = AgentWearablesUpdateAgentDataBlock(AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO)
        self.wearable_data: list[WearableDataBlock] = []
        self.visual_param: list[VisualParamBlock] = [] # Should contain 256 params

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset

        # AgentData block
        self.agent_data.AgentID = CustomUUID(buffer, offset); offset += 16
        # Assuming SessionID is here based on common pattern, C# has SerialNum instead.
        # If it's SerialNum (u32) + VisualVersion (u8):
        # self.agent_data.SerialNum = helpers.bytes_to_uint32(buffer, offset); offset += 4
        # self.agent_data.VisualVersion = buffer[offset]; offset += 1
        # For now, let's assume SessionID for placeholder consistency.
        self.agent_data.SessionID = CustomUUID(buffer, offset); offset += 16 # Placeholder for actual AgentData structure
        # Correcting AgentData block based on common AgentWearablesUpdate structure:
        # It's AgentID (16), SerialNum (4), VisualVersion (1)
        # Reset offset and parse correctly:
        offset = initial_offset
        self.agent_data.AgentID = CustomUUID(buffer, offset); offset += 16
        self.agent_data.SerialNum = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.agent_data.VisualVersion = buffer[offset]; offset += 1


        # WearableData blocks (variable count)
        wearable_count = buffer[offset]; offset += 1 # Count is u8
        for _ in range(wearable_count):
            if offset + 16 + 16 + 1 > initial_offset + length: # Check bounds
                logger.warning("AgentWearablesUpdate: WearableData truncated.")
                break
            item_id = CustomUUID(buffer, offset); offset += 16
            asset_id = CustomUUID(buffer, offset); offset += 16
            wearable_type_val = buffer[offset]; offset += 1
            self.wearable_data.append(WearableDataBlock(ItemID=item_id, AssetID=asset_id, WearableType=wearable_type_val))

        # VisualParam blocks (fixed count, typically 256)
        # There's a count byte for visual params as well.
        visual_param_count = buffer[offset]; offset += 1
        for i in range(visual_param_count):
            if offset + 1 > initial_offset + length: # Check bounds
                logger.warning(f"AgentWearablesUpdate: VisualParam data truncated at index {i}.")
                break
            param_val = buffer[offset]; offset += 1
            self.visual_param.append(VisualParamBlock(ParamValue=param_val))

        if visual_param_count != 256 and visual_param_count !=0 : # 0 can be valid if not sent
             logger.warning(f"AgentWearablesUpdate: Expected 256 visual params or 0, got {visual_param_count}")
        return self

    def to_bytes(self) -> bytes:
        logger.warning("AgentWearablesUpdatePacket.to_bytes not typically called on client.")
        return b''


# --- AgentSetAppearancePacket (Client -> Server) ---
@dataclasses.dataclass
class AgentSetAppearanceAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID
    SerialNum: int # u32
    Size: Vector3 # Vector3, but often just sent as all zeros by client initially

@dataclasses.dataclass
class AgentSetAppearanceObjectDataBlock: # For TextureEntry
    TextureEntry: bytes # Variable, up to 2000 bytes (typically ~470 for default, up to 1000 for extended)

# WearableDataBlock for AgentSetAppearance is an array of CacheID (CustomUUID)
# This is typically empty when sent by client, server uses it for its own caching.
# VisualParamBlock is same as for AgentWearablesUpdate (array of ParamValue: byte)

class AgentSetAppearancePacket(Packet):
    """Client sends this to set its appearance (textures, visual params, wearables)."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 serial_num: int, size_vec: Vector3,
                 texture_entry_bytes: bytes, visual_params_bytes: List[int], # List of int 0-255
                 header: PacketHeader | None = None):
        super().__init__(PacketType.AgentSetAppearance, header if header else PacketHeader())
        self.agent_data = AgentSetAppearanceAgentDataBlock(
            AgentID=agent_id, SessionID=session_id, SerialNum=serial_num, Size=size_vec
        )
        self.object_data = AgentSetAppearanceObjectDataBlock(TextureEntry=texture_entry_bytes)
        self.wearable_data_cache_ids: List[CustomUUID] = [] # Typically empty from client
        self.visual_param_values: List[int] = visual_params_bytes # List of ints (0-255)
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData Block
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.extend(helpers.uint32_to_bytes(self.agent_data.SerialNum))
        data.extend(struct.pack('<fff', self.agent_data.Size.X, self.agent_data.Size.Y, self.agent_data.Size.Z))

        # ObjectData Block (TextureEntry)
        te_len = len(self.object_data.TextureEntry)
        if te_len > 2000: # Max size check
            logger.warning(f"TextureEntry too long ({te_len}), truncating to 2000 bytes.")
            self.object_data.TextureEntry = self.object_data.TextureEntry[:2000]
        # TextureEntry is prefixed by its length (u16 or u32 depending on packet version, assume u16 for now)
        # C# uses WriteUTF8String which implies null termination and length prefix handling by underlying methods.
        # For direct byte array, many viewers expect u16 length prefix for TE.
        # However, AgentSetAppearance TE is often just the raw bytes up to a certain limit (e.g. 1000).
        # For now, assume raw bytes as per some packet captures. This needs verification.
        # If it needs a length prefix: data.extend(helpers.uint16_to_bytes(len(self.object_data.TextureEntry)))
        data.extend(self.object_data.TextureEntry)

        # WearableData Block (array of CacheIDs)
        data.append(len(self.wearable_data_cache_ids) & 0xFF) # Count byte
        for cache_id in self.wearable_data_cache_ids: # Usually empty from client
            data.extend(cache_id.get_bytes())

        # VisualParam Block (array of ParamValue bytes)
        num_visual_params = len(self.visual_param_values)
        if num_visual_params != 256: # Standard count
             logger.warning(f"AgentSetAppearance: Sending {num_visual_params} visual params, expected 256.")
        data.append(num_visual_params & 0xFF) # Count byte (should be 256 or specific count)
        for val in self.visual_param_values:
            data.append(val & 0xFF) # Ensure it's a byte

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("AgentSetAppearancePacket.from_bytes_body should not be called on client.")
        return self


# --- AvatarAppearancePacket (Server -> Client) ---
@dataclasses.dataclass
class AvatarAppearanceSenderBlock:
    ID: CustomUUID
    IsTrial: bool # u8

# ObjectDataBlock (TextureEntry) and VisualParamBlock are same as defined above or in AgentWearablesUpdate
# For clarity, can redefine if needed, or assume AgentWearablesUpdate's are compatible if identical.
# Using AgentWearablesUpdate's VisualParamBlock for now.

# AgentSetAppearancePacket WearableDataBlock is different from AgentWearablesUpdatePacket's.
# For AgentSetAppearance, WearableData is an array of:
#   CacheID (UUID, often zero from client)
#   TextureIndex (u8, maps to a face on the wearable's texture, often zero)
# This is if sending individual texture faces for wearables.
# Simpler AgentSetAppearance sends main wearables via WearableData blocks like AgentWearablesUpdate.
# The C# AgentSetAppearancePacket has `WearableDataBlock[] WearableData;`
# where `WearableDataBlock` has `CacheID`, `TextureIndex`.
# And `VisualParamBlock[] VisualParam;`
# For initial "wear items" via AgentSetAppearance, client sends a list of *worn* items,
# not just texture changes. The server then figures out the TextureEntry.
# The WearableData in AgentSetAppearance for wearing is: ItemID, AssetID, WearableType.
# This is confusing. Let's assume the WearableData in AgentSetAppearance is for *overriding*
# specific wearable's textures (CacheID/TextureIndex), and the primary list of worn items
# is implicitly defined by what's baked into the TextureEntry or by AgentIsNowWearing.

# For this implementation, AgentSetAppearance will send the full list of current wearables
# in a simplified format if the C# packet structure is complex for WearableData.
# The prompt says: "WearableDataBlock array (in to_bytes) can be populated from a list of
# (wearable_type, item_id, asset_id) tuples."
# This implies a structure similar to AgentWearablesUpdate's WearableData for *sending*.
# C# AgentSetAppearancePacket.WearableData is `public WearableDataBlock[] WearableData;`
# `WearableDataBlock` is: `public UUID CacheID; public byte TextureIndex;`
# This is for sending *texture overrides* for already worn items, not for specifying what's worn.
# The items being worn are implicitly defined by the TextureEntry and VisualParams.

# Let's simplify AgentSetAppearance for now: client sends TE and VPs.
# Wearing/unwearing is done via AgentIsNowWearing and server rebakes TE.
# Or, a more complete AgentSetAppearance also includes a list of (ItemID, AssetID, WearableType)
# for the server to bake. This seems more likely.
# The prompt for AgentSetAppearancePacket `to_bytes` mentions:
# "WearableData count is 0". This implies client doesn't usually send this block.
# "VisualParam count is typically 256."
# This means the client primarily sends TE + VPs. The *server* knows what items these correspond to.

# For `AgentIsNowWearingPacket`, it's a list of (ItemID, WearableType).

@dataclasses.dataclass
class AgentIsNowWearingItemDataBlock:
    ItemID: CustomUUID
    WearableType: int # u8, maps to WearableType enum

class AgentIsNowWearingPacket(Packet):
    """Client informs the server about explicitly worn or detached items."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 items: list[tuple[CustomUUID, WearableType]],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.AgentIsNowWearing, header if header else PacketHeader())
        self.agent_data = AgentSetAppearanceAgentDataBlock( # Re-use AgentData from AgentSetAppearance
            AgentID=agent_id, SessionID=session_id, SerialNum=0, Size=Vector3.ZERO # SerialNum/Size might not be used
        )
        self.item_data_blocks: list[AgentIsNowWearingItemDataBlock] = []
        for item_id, wearable_type_enum in items:
            self.item_data_blocks.append(
                AgentIsNowWearingItemDataBlock(ItemID=item_id, WearableType=wearable_type_enum.value)
            )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ItemData array
        data.append(len(self.item_data_blocks) & 0xFF) # Count byte
        for block in self.item_data_blocks:
            data.extend(block.ItemID.get_bytes())
            data.append(block.WearableType & 0xFF)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("AgentIsNowWearingPacket.from_bytes_body not typically called on client.")
        return self


class AvatarAppearancePacket(Packet):
    """Server sends this to inform about another avatar's appearance."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.AvatarAppearance, header if header else PacketHeader())
        self.sender = AvatarAppearanceSenderBlock(ID=CustomUUID.ZERO, IsTrial=False)
        self.object_data = AgentSetAppearanceObjectDataBlock(TextureEntry=b'') # Reusing for TE
        self.visual_param: list[VisualParamBlock] = [] # List of VisualParamBlock from AgentWearablesUpdate structure

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset

        # Sender Block
        self.sender.ID = CustomUUID(buffer, offset); offset += 16
        self.sender.IsTrial = (buffer[offset] != 0); offset += 1

        # ObjectData Block (TextureEntry)
        # TextureEntry is complex. It's a variable length byte array.
        # The length is determined by how much of the packet is left before VisualParams.
        # VisualParams are a fixed block at the end (typically 256 bytes + 1 count byte).

        # Calculate visual param block size first
        # If VisualParam count is always 256 + 1 byte for count:
        vp_count_assumed = 256 # This is an assumption, might be a byte in packet
        # Check if there's a visual param count byte
        # C# AvatarAppearancePacket has a VisualParam (count byte + 256 bytes) block at the end.
        # So, texture entry length is total_length - header - sender - visual_params_with_count.

        # Assuming VisualParam data is at the end and has a count byte
        # This is a common pattern: [Data] [VPCount (1 byte)] [VPData (VPCount bytes)]
        # If VPCount is fixed at 256, then it's simpler:
        # texture_entry_len = length - (offset - initial_offset) - (1 + 256) # if count byte + 256 params
        # This needs careful checking against actual packet structure from C# / captures.

        # For now, let's assume TextureEntry takes up space until a known fixed size for VisualParams.
        # If VisualParams are always 256 bytes + 1 count byte:
        visual_params_size_with_count = 256 + 1
        texture_entry_end_offset = (initial_offset + length) - visual_params_size_with_count

        if offset <= texture_entry_end_offset:
            self.object_data.TextureEntry = buffer[offset:texture_entry_end_offset]
            offset = texture_entry_end_offset
        else: # Not enough space for TE and full visual params
            logger.warning("AvatarAppearancePacket: Not enough data for TextureEntry and VisualParams.")
            # Fallback: try to read TE up to where visual params would start, or assume empty TE.
            min_remaining_for_vp = 1 # count byte
            if initial_offset + length - offset > min_remaining_for_vp:
                 self.object_data.TextureEntry = buffer[offset : (initial_offset + length - min_remaining_for_vp)]
            else: self.object_data.TextureEntry = b''
            offset += len(self.object_data.TextureEntry)


        # VisualParam Block
        if offset < initial_offset + length:
            visual_param_count = buffer[offset]; offset += 1
            for i in range(visual_param_count):
                if offset + 1 > initial_offset + length: break
                param_val = buffer[offset]; offset += 1
                self.visual_param.append(VisualParamBlock(ParamValue=param_val))
            if visual_param_count != 256 and visual_param_count != 0:
                 logger.warning(f"AvatarAppearance: Expected 256 or 0 visual params, got {visual_param_count}")
        else:
            logger.warning("AvatarAppearancePacket: No data left for VisualParams count.")

        return self

    def to_bytes(self) -> bytes: # Client doesn't send this typically
        logger.warning("AvatarAppearancePacket.to_bytes not implemented (server sends this).")
        return b''
