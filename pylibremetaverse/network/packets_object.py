import logging
import struct
import dataclasses

from pylibremetaverse.types import CustomUUID, Vector3, Quaternion, Color4
from pylibremetaverse.types.enums import PCode, Material, ClickAction, PrimFlags, PathCurve, ProfileCurve # Added Path/ProfileCurve
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class ObjectDataBlock:
    id: int = 0
    state: int = 0
    full_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    crc: int = 0 # u32
    parent_id: int = 0
    update_flags: int = 0 # u32, SL UpdateType enum

    pcode: PCode = PCode.Primitive
    material: Material = Material.STONE
    click_action: ClickAction = ClickAction.TOUCH

    scale: Vector3 = dataclasses.field(default_factory=lambda: Vector3(0.5, 0.5, 0.5))
    position: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    rotation: Quaternion = dataclasses.field(default_factory=Quaternion.IDENTITY)

    path_curve: PathCurve = PathCurve.LINE; profile_curve: ProfileCurve = ProfileCurve.CIRCLE
    path_begin: float = 0.0; path_end: float = 0.0
    profile_begin: float = 0.0; profile_hollow: float = 0.0

    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    group_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)

    name_value_bytes: bytes = b'' # Raw NameValue string bytes
    name: str = ""; description: str = ""; text: str = "" # Parsed from NameValue

    text_color: Color4 = dataclasses.field(default_factory=lambda: Color4(1.0,1.0,1.0,1.0))
    media_url: bytes = b'' # Raw MediaURL string bytes
    texture_entry_bytes: bytes | None = None

    def parse_name_value(self):
        try:
            decoded_nv = self.name_value_bytes.decode('utf-8', errors='replace')
            parts = decoded_nv.split("\n", 2)
            self.name = parts[0]
            if len(parts) > 1: self.description = parts[1]
            if len(parts) > 2: self.text = parts[2]
        except Exception: logger.warning("Error parsing NameValue string.")


class ObjectUpdatePacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectUpdate, header if header else PacketHeader())
        self.region_handle: int = 0; self.time_dilation: int = 0
        self.object_data_blocks: list[ObjectDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset
        self.region_handle = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.time_dilation = helpers.bytes_to_uint16(buffer, offset); offset += 2

        # This is still a VAST simplification of ObjectUpdate parsing.
        # A proper implementation needs to handle different update types (Terse, Full, etc.)
        # and conditionally parse fields based on UpdateFlags and PCode.
        # For now, attempting to parse one "full-like" block.
        while offset < initial_offset + length: # Loop to parse multiple blocks if present
            if initial_offset + length - offset < 20: break # Heuristic: not enough for a minimal block

            block = ObjectDataBlock()
            try:
                block.id = helpers.bytes_to_uint32(buffer, offset); offset += 4 # LocalID
                block.state = buffer[offset]; offset += 1
                block.full_id = CustomUUID(buffer, offset); offset += 16
                block.crc = helpers.bytes_to_uint32(buffer, offset); offset += 4
                block.pcode = PCode(buffer[offset]); offset += 1
                block.material = Material(buffer[offset]); offset += 1
                # ... many more fixed fields like ClickAction, ParentID, UpdateFlags
                # For now, skipping to some common variable or easily identifiable ones

                # Assuming some fields are present for this simplified parse:
                # This does not correctly handle terse updates or conditional fields.
                # This is a placeholder for a much more complex parsing logic.
                offset_before_vectors = offset
                try:
                    block.scale = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12
                    block.position = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12
                    block.rotation = Quaternion(*struct.unpack_from('<ffff', buffer, offset)); offset += 16
                    block.owner_id = CustomUUID(buffer, offset); offset += 16 # Example, might be conditional
                except struct.error: # If vector/quat data is not where expected, log and skip this block
                    logger.warning(f"ObjectUpdate: struct error parsing vectors/quat for block ID {block.id}, data potentially terse or malformed. Skipping block.")
                    break # Stop trying to parse more blocks from this packet if one is bad

                # Example of reading a variable length string (e.g. NameValue)
                # This requires knowing the structure (e.g. if it's null terminated or length prefixed)
                # For NameValue, it's often null-terminated.
                if offset < initial_offset + length:
                    name_value_bytes, read_len = helpers.read_null_terminated_string_bytes(buffer, offset)
                    if read_len > 0 :
                         block.name_value_bytes = name_value_bytes
                         block.parse_name_value()
                         offset += read_len

                # TextureEntry: variable, length-prefixed (often 2 bytes for length)
                if offset + 2 <= initial_offset + length:
                    te_len = helpers.bytes_to_uint16(buffer, offset) # Assuming u16 length prefix
                    offset += 2
                    if offset + te_len <= initial_offset + length:
                        block.texture_entry_bytes = buffer[offset : offset + te_len]
                        offset += te_len
                    else: logger.warning(f"TE length {te_len} exceeds packet for prim {block.id}")

                self.object_data_blocks.append(block)
                logger.debug(f"Parsed ObjectDataBlock (simplified): ID={block.id}, Name='{block.name}'")
            except Exception as e:
                logger.error(f"Error parsing an ObjectDataBlock in ObjectUpdate: {e}. Data remaining: { (initial_offset + length) - offset } bytes.")
                break # Stop parsing if an error occurs in one block
        return self
    def to_bytes(self)->bytes: logger.warning("Client doesn't send ObjectUpdatePacket."); return b''


# --- RequestMultipleObjectsPacket (Client -> Server) ---
@dataclasses.dataclass
class RequestMultipleObjectsObjectDataBlock:
    ID: int # u32, LocalID of the object to request
    CacheMissType: int = 0 # u8, usually 0 (Prim) or 1 (Texture)

class RequestMultipleObjectsPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, local_ids: list[int],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.RequestMultipleObjects, header if header else PacketHeader())
        self.agent_id = agent_id
        self.session_id = session_id
        self.object_requests: list[RequestMultipleObjectsObjectDataBlock] = []
        for local_id in local_ids:
            self.object_requests.append(RequestMultipleObjectsObjectDataBlock(ID=local_id))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes())
        # ObjectData Blocks
        count = len(self.object_requests)
        data.append(count & 0xFF) # Count byte
        for req_block in self.object_requests:
            data.extend(helpers.uint32_to_bytes(req_block.ID))
            data.append(req_block.CacheMissType & 0xFF)
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive RequestMultipleObjectsPacket."); return self


# --- ObjectUpdateCachedPacket (Server -> Client) ---
@dataclasses.dataclass
class ObjectUpdateCachedDataBlock:
    ID: int # u32, LocalID
    UpdateFlags: int # u32, SL UpdateType enum

class ObjectUpdateCachedPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectUpdateCached, header if header else PacketHeader())
        self.agent_id_data_block_placeholder: CustomUUID = CustomUUID.ZERO # If AgentData is part of it
        self.object_data_blocks: list[ObjectUpdateCachedDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset
        # AgentData block (AgentID, SessionID) - C# has this.
        # self.agent_id_data_block_placeholder = CustomUUID(buffer, offset); offset += 16
        # CustomUUID(buffer, offset); offset += 16 # SessionID, not stored directly if not needed
        # For now, assuming AgentData is NOT part of this specific packet's distinct payload blocks
        # based on some interpretations where it's only ObjectData array.
        # If AgentData is present, the offsets below need adjustment.

        # ObjectData blocks
        while offset < initial_offset + length:
            if initial_offset + length - offset < 8: break # Not enough for ID + UpdateFlags
            obj_id = helpers.bytes_to_uint32(buffer, offset); offset += 4
            update_flags = helpers.bytes_to_uint32(buffer, offset); offset += 4
            self.object_data_blocks.append(ObjectUpdateCachedDataBlock(ID=obj_id, UpdateFlags=update_flags))
        return self
    def to_bytes(self)->bytes: logger.warning("Client doesn't send ObjectUpdateCachedPacket."); return b''


# --- Object Select/Deselect/Link/Delink Packets (Client -> Server) ---

@dataclasses.dataclass
class ObjectInteractionAgentDataBlock: # Common for these packets
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class ObjectInteractionObjectDataBlock: # Common for these packets
    ObjectLocalID: int # u32

class ObjectSelectPacket(Packet):
    """Client sends this to select one or more objects."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, local_ids: list[int],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectSelect, header if header else PacketHeader())
        self.agent_data = ObjectInteractionAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectInteractionObjectDataBlock] = \
            [ObjectInteractionObjectDataBlock(ObjectLocalID=lid) for lid in local_ids]
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData (array)
        data.append(len(self.object_data_blocks) & 0xFF) # Count byte
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive ObjectSelectPacket."); return self


class ObjectDeselectPacket(Packet):
    """Client sends this to deselect one or more objects."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, local_ids: list[int],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectDeselect, header if header else PacketHeader())
        self.agent_data = ObjectInteractionAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectInteractionObjectDataBlock] = \
            [ObjectInteractionObjectDataBlock(ObjectLocalID=lid) for lid in local_ids]
        self.header.reliable = True

    def to_bytes(self) -> bytes: # Structure is identical to ObjectSelect
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive ObjectDeselectPacket."); return self


class ObjectLinkPacket(Packet):
    """Client sends this to link multiple objects."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, local_ids: list[int],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectLink, header if header else PacketHeader())
        if not local_ids or len(local_ids) < 2:
            raise ValueError("ObjectLinkPacket requires at least two local_ids (root and child).")
        self.agent_data = ObjectInteractionAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectInteractionObjectDataBlock] = \
            [ObjectInteractionObjectDataBlock(ObjectLocalID=lid) for lid in local_ids]
        self.header.reliable = True

    def to_bytes(self) -> bytes: # Structure identical to ObjectSelect
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive ObjectLinkPacket."); return self


class ObjectDelinkPacket(Packet):
    """Client sends this to delink objects in a linkset."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, local_ids: list[int], # Prims to remove from linkset
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectDelink, header if header else PacketHeader())
        if not local_ids:
            raise ValueError("ObjectDelinkPacket requires at least one local_id.")
        self.agent_data = ObjectInteractionAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectInteractionObjectDataBlock] = \
            [ObjectInteractionObjectDataBlock(ObjectLocalID=lid) for lid in local_ids]
        self.header.reliable = True

    def to_bytes(self) -> bytes: # Structure identical to ObjectSelect
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive ObjectDelinkPacket."); return self


# --- KillObjectPacket (Server -> Client) ---
@dataclasses.dataclass
class KillObjectDataBlock: # For KillObjectPacket
    ID: int # u32, LocalID of the object to remove

class KillObjectPacket(Packet):
    """
    Server sends this to tell the client to remove/kill one or more objects.
    In C#, this is often called KillObjects and handles an array of object IDs.
    """
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.KillObject, header if header else PacketHeader())
        self.object_data_blocks: list[KillObjectDataBlock] = [] # List of LocalIDs to kill

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset

        # The packet structure for KillObject (or KillObjects) indicates a count
        # of objects, followed by that many ObjectData blocks, each just containing an ID.
        # However, C# KillObject (singular) has just one ObjectData block with one ID.
        # KillObjects (plural) has a count and then multiple ObjectData blocks.
        # The PacketType.KillObject (0x0B) corresponds to KillObjects (plural).

        if length < 1: # At least one byte for count
            logger.warning("KillObjectPacket body too short for count.")
            return self

        num_objects = buffer[offset]; offset += 1

        for _ in range(num_objects):
            if offset + 4 > initial_offset + length: # Check for enough data for an ID
                logger.warning("KillObjectPacket: Data truncated while reading object IDs.")
                break
            local_id = helpers.bytes_to_uint32(buffer, offset); offset += 4
            self.object_data_blocks.append(KillObjectDataBlock(ID=local_id))

        logger.debug(f"Parsed KillObjectPacket, {len(self.object_data_blocks)} objects to remove.")
        return self

    def to_bytes(self) -> bytes:
        logger.warning("KillObjectPacket.to_bytes not implemented (server sends this).")
        return b''


# --- ImprovedTerseObjectUpdatePacket (Server -> Client) ---
@dataclasses.dataclass
class ImprovedTerseObjectDataBlock: # For ImprovedTerseObjectUpdatePacket
    local_id: int = 0 # u32, read from packet header for each block
    update_type: int = 0 # u8, indicates which fields are present / how they are packed
    data: bytes = b'' # The actual bit-packed or raw data for this object
    texture_entry_bytes: bytes | None = None # Optional full TE if UpdateType indicates it

    # Decoded fields (populated by ObjectManager based on update_type and data)
    # Example:
    # position: Vector3 | None = None
    # rotation: Quaternion | None = None
    # velocity: Vector3 | None = None
    # ... etc.


class ImprovedTerseObjectUpdatePacket(Packet):
    """
    Contains updates for multiple objects in a highly compressed, bit-packed format.
    This is a very complex packet. This implementation will focus on the outer structure
    and a placeholder for decoding the actual 'data' part of each block.
    """
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ImprovedTerseObjectUpdate, header if header else PacketHeader())
        self.region_handle: int = 0 # u64
        self.time_dilation: int = 0 # u16 (scaled to float: /65535.0)
        self.object_data_blocks: list[ImprovedTerseObjectDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset

        # RegionData block
        self.region_handle = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.time_dilation = helpers.bytes_to_uint16(buffer, offset); offset += 2

        # ObjectData blocks (loop until end of packet)
        idx = 0 # For debugging block count
        while offset < initial_offset + length:
            # Each block starts with:
            # LocalID (4 bytes)
            # UpdateType (1 byte)
            # Data Length (1 byte if < 128, else 2 bytes if MSB of first byte is set)
            if initial_offset + length - offset < 4 + 1 + 1: # Min size for block header
                logger.warning(f"ImprovedTerse: Not enough data for next block header. Remaining: {initial_offset + length - offset}")
                break

            local_id = helpers.bytes_to_uint32(buffer, offset); offset += 4
            update_type = buffer[offset]; offset += 1

            data_len = buffer[offset]; offset += 1
            if data_len & 0x80: # Check MSB for two-byte length
                if offset >= initial_offset + length: # Need another byte for length
                    logger.error(f"ImprovedTerse: Truncated two-byte data length for LocalID {local_id}.")
                    break
                data_len = ((data_len & 0x7F) << 8) | buffer[offset]
                offset += 1

            if offset + data_len > initial_offset + length:
                logger.error(f"ImprovedTerse: Data length {data_len} for LocalID {local_id} exceeds packet bounds.")
                break # Corrupted or truncated packet

            object_data_payload = buffer[offset : offset + data_len]
            offset += data_len

            block = ImprovedTerseObjectDataBlock(local_id=local_id, update_type=update_type, data=object_data_payload)

            # Check for appended TextureEntry (UpdateType 0x10 in C# means TE follows)
            # C# UpdateType enum: PrimFlags = 0x01, Texture = 0x02, ... , TextureAnim = 0x08, Data = 0x09, Full = 0x10
            # The UpdateType byte here is different from the UpdateFlags in ObjectUpdate.
            # It directly signals the type of data in the terse block.
            # If (update_type & 0x10) or (update_type == 9 with TE flag in it), then TE follows.
            # This logic is complex and needs to match C# precisely.
            # For now, assume TE is only present if a specific UpdateType signals it.
            # Example: if update_type == 0x10 (Full update in terse form, may include TE)
            if update_type == 0x10: # Placeholder for "FullUpdate" type that includes TE
                if offset + 2 <= initial_offset + length: # Check for TE length prefix
                    te_len = helpers.bytes_to_uint16(buffer, offset); offset += 2
                    if offset + te_len <= initial_offset + length:
                        block.texture_entry_bytes = buffer[offset : offset + te_len]
                        offset += te_len
                    else: logger.warning(f"ImprovedTerse: TE length {te_len} for LocalID {local_id} exceeds packet bounds.")
                # else: logger.debug(f"ImprovedTerse: No TE length found for LocalID {local_id} despite UpdateType suggesting it.")


            self.object_data_blocks.append(block)
            idx += 1

        logger.debug(f"Parsed {idx} blocks in ImprovedTerseObjectUpdatePacket.")
        return self

    def to_bytes(self) -> bytes:
        logger.warning("ImprovedTerseObjectUpdatePacket.to_bytes not implemented (server sends this).")
        return b''


# --- Object Properties Request and Data Packets ---

@dataclasses.dataclass
class RequestObjectPropertiesFamilyAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class RequestObjectPropertiesFamilyObjectDataBlock:
    RequestFlags: int # u32, often 0 for full properties
    ObjectUUID: CustomUUID

class RequestObjectPropertiesFamilyPacket(Packet): # Client -> Server
    """Requests properties for an object and its linkset (family)."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_uuid: CustomUUID, request_flags: int = 0,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.RequestObjectPropertiesFamily, header if header else PacketHeader())
        self.agent_data = RequestObjectPropertiesFamilyAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        # This packet has one ObjectData block in C# for the main UUID
        self.object_data = RequestObjectPropertiesFamilyObjectDataBlock(RequestFlags=request_flags, ObjectUUID=object_uuid)
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData
        data.extend(helpers.uint32_to_bytes(self.object_data.RequestFlags))
        data.extend(self.object_data.ObjectUUID.get_bytes())
        return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive ROPFamilyPkt."); return self


@dataclasses.dataclass
class ObjectPropertiesPacketDataBlock: # Used by ObjectPropertiesFamilyPacket and ObjectPropertiesPacket
    ObjectID: CustomUUID = CustomUUID.ZERO
    OwnerID: CustomUUID = CustomUUID.ZERO
    CreatorID: CustomUUID = CustomUUID.ZERO
    GroupID: CustomUUID = CustomUUID.ZERO
    BaseMask: int = 0 # u32 (PermissionMask)
    OwnerMask: int = 0 # u32
    GroupMask: int = 0 # u32
    EveryoneMask: int = 0 # u32
    NextOwnerMask: int = 0 # u32
    OwnershipCost: int = 0 # s32
    SalePrice: int = 0 # s32
    SaleType: int = 0 # u8 (SaleType enum)
    Category: int = 0 # u32 (InventoryCategory, not directly used often)
    LastOwnerID: CustomUUID = CustomUUID.ZERO
    Name: bytes = b''         # Variable, null-terminated (UTF-8)
    Description: bytes = b''  # Variable, null-terminated (UTF-8)
    TouchText: bytes = b''    # Variable, null-terminated (UTF-8)
    SitText: bytes = b''      # Variable, null-terminated (UTF-8)
    # GroupOwned: bool (derived from GroupID != ZERO and specific OwnerID patterns)

    @property
    def name_str(self) -> str: return self.Name.decode(errors='replace')
    @property
    def description_str(self) -> str: return self.Description.decode(errors='replace')
    @property
    def touch_text_str(self) -> str: return self.TouchText.decode(errors='replace')
    @property
    def sit_text_str(self) -> str: return self.SitText.decode(errors='replace')


class ObjectPropertiesFamilyPacket(Packet): # Server -> Client
    """
    Contains properties for one or more objects in a linkset (family).
    This corresponds to C# ObjectPropertiesFamilyPacket (Type 0x3F).
    """
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectPropertiesFamily, header if header else PacketHeader())
        self.requestor_id: CustomUUID = CustomUUID.ZERO # AgentID of who requested
        self.object_id: CustomUUID = CustomUUID.ZERO    # UUID of the root prim of the linkset
        self.type: int = 0 # u8, actually PrimType enum in C# (not PCode) - e.g. tree, grass
                           # This might need a new PrimType enum if different from PCode.
                           # For now, store as int.
        self.properties_blocks: list[ObjectPropertiesPacketDataBlock] = [] # One for each prim in linkset

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset
        # RequestorData
        self.requestor_id = CustomUUID(buffer, offset); offset += 16
        # ObjectData (for the root/main object of the family)
        self.object_id = CustomUUID(buffer, offset); offset += 16
        self.type = buffer[offset]; offset += 1 # PrimType/Category

        # Number of objects in this packet (usually 1 for the root, then others if part of selection)
        # C# ObjectPropertiesFamilyPacket has a nested array of ObjectData blocks.
        # The packet format for ObjectPropertiesFamily is complex.
        # It seems to contain one main ObjectData block, and the "family" aspect might be
        # how the client interprets it or if multiple such packets are sent for a linkset.
        # For now, assume it sends one ObjectPropertiesPacketDataBlock per packet.
        # This needs verification against C# parsing.

        # If it's like ViewerEffect, it has a count for sub-blocks.
        # For ObjectPropertiesFamily, C# parses one ObjectData block directly.
        # Let's assume one block for now.
        if offset < initial_offset + length:
            prop_block = ObjectPropertiesPacketDataBlock()
            prop_block.ObjectID = self.object_id # The main ObjectID is for this block

            prop_block.OwnerID = CustomUUID(buffer, offset); offset += 16
            prop_block.CreatorID = CustomUUID(buffer, offset); offset += 16
            prop_block.GroupID = CustomUUID(buffer, offset); offset += 16
            prop_block.BaseMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.OwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.GroupMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.EveryoneMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.NextOwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.OwnershipCost = helpers.bytes_to_int32(buffer, offset); offset += 4
            prop_block.SalePrice = helpers.bytes_to_int32(buffer, offset); offset += 4
            prop_block.SaleType = buffer[offset]; offset += 1
            prop_block.Category = helpers.bytes_to_uint32(buffer, offset); offset += 4 # Not InventoryCategory, but different
            prop_block.LastOwnerID = CustomUUID(buffer, offset); offset += 16

            prop_block.Name, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.Description, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.TouchText, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.SitText, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read

            self.properties_blocks.append(prop_block)
        return self
    def to_bytes(self)->bytes: logger.warning("Client doesn't send OPFamilyPkt."); return b''


class ObjectPropertiesPacket(Packet): # Server -> Client
    """
    Contains properties for a single object.
    This corresponds to C# ObjectPropertiesPacket (Type 0x5A).
    It contains an array of ObjectData blocks, but typically only one for this packet type.
    """
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectProperties, header if header else PacketHeader())
        self.object_data_blocks: list[ObjectPropertiesPacketDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # ObjectData block array
        num_blocks = buffer[offset]; offset += 1
        for _ in range(num_blocks):
            if offset >= length: break # Safety break
            prop_block = ObjectPropertiesPacketDataBlock()
            # This parsing logic is identical to the one in ObjectPropertiesFamilyPacket's block
            # It should be refactored into a helper or on ObjectPropertiesPacketDataBlock itself.
            prop_block.ObjectID = CustomUUID(buffer, offset); offset += 16 # This is the key difference
            prop_block.OwnerID = CustomUUID(buffer, offset); offset += 16
            prop_block.CreatorID = CustomUUID(buffer, offset); offset += 16
            prop_block.GroupID = CustomUUID(buffer, offset); offset += 16
            prop_block.BaseMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.OwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.GroupMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.EveryoneMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.NextOwnerMask = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.OwnershipCost = helpers.bytes_to_int32(buffer, offset); offset += 4
            prop_block.SalePrice = helpers.bytes_to_int32(buffer, offset); offset += 4
            prop_block.SaleType = buffer[offset]; offset += 1
            prop_block.Category = helpers.bytes_to_uint32(buffer, offset); offset += 4
            prop_block.LastOwnerID = CustomUUID(buffer, offset); offset += 16
            prop_block.Name, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.Description, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.TouchText, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            prop_block.SitText, read = helpers.read_null_terminated_string_bytes(buffer,offset); offset+=read
            self.object_data_blocks.append(prop_block)
        return self
    def to_bytes(self)->bytes: logger.warning("Client doesn't send OPPkt."); return b''


# --- Object Manipulation Packets (Client -> Server) ---

@dataclasses.dataclass
class ObjectManipulationAgentDataBlock: # Common for Move, Scale, Rotate
    AgentID: CustomUUID
    SessionID: CustomUUID

# --- ObjectMovePacket ---
@dataclasses.dataclass
class ObjectMoveDataBlock:
    ObjectLocalID: int # u32
    Position: Vector3

class ObjectMovePacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_moves: list[tuple[int, Vector3]],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectMove, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectMoveDataBlock] = []
        for local_id, position in object_moves:
            self.object_data_blocks.append(ObjectMoveDataBlock(ObjectLocalID=local_id, Position=position))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData Blocks
        data.append(len(self.object_data_blocks) & 0xFF) # Count byte
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.extend(struct.pack('<fff', block.Position.X, block.Position.Y, block.Position.Z))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectMovePacket.")
        return self

# --- ObjectScalePacket ---
@dataclasses.dataclass
class ObjectScaleDataBlock:
    ObjectLocalID: int # u32
    Scale: Vector3

class ObjectScalePacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_scales: list[tuple[int, Vector3]],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectScale, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectScaleDataBlock] = []
        for local_id, scale in object_scales:
            self.object_data_blocks.append(ObjectScaleDataBlock(ObjectLocalID=local_id, Scale=scale))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData Blocks
        data.append(len(self.object_data_blocks) & 0xFF) # Count byte
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.extend(struct.pack('<fff', block.Scale.X, block.Scale.Y, block.Scale.Z))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectScalePacket.")
        return self

# --- ObjectRotationPacket ---
@dataclasses.dataclass
class ObjectRotationDataBlock:
    ObjectLocalID: int # u32
    Rotation: Quaternion

class ObjectRotationPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_rotations: list[tuple[int, Quaternion]],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectRotation, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectRotationDataBlock] = []
        for local_id, rotation in object_rotations:
            self.object_data_blocks.append(ObjectRotationDataBlock(ObjectLocalID=local_id, Rotation=rotation))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData Blocks
        data.append(len(self.object_data_blocks) & 0xFF) # Count byte
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            # Quaternions are often sent as X, Y, Z, W with Vector3 normalization for W component,
            # or directly as 4 floats. Assuming 4 floats for now.
            data.extend(struct.pack('<ffff', block.Rotation.X, block.Rotation.Y, block.Rotation.Z, block.Rotation.W))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectRotationPacket.")
        return self


# --- Object Name, Description, Text, ClickAction Packets (Client -> Server) ---

from pylibremetaverse.types.enums import AddFlags # Added for ObjectAddPacket
# ObjectManipulationAgentDataBlock is already defined and can be reused.

# --- ObjectAddPacket (Client -> Server) ---
class ObjectAddPacket(Packet):
    def __init__(self,
                 agent_id: CustomUUID,
                 session_id: CustomUUID,
                 pcode: PCode,
                 material: Material,
                 add_flags: AddFlags,
                 path_params: dict, # See C# ObjectAddPacket.PathBlock for keys
                 profile_params: dict, # See C# ObjectAddPacket.ProfileBlock for keys
                 position: Vector3, # World position or RayEnd
                 scale: Vector3,
                 rotation: Quaternion,
                 texture_entry_bytes: bytes, # Max 1000 bytes (TEXTURE_ENTRY_MAX_SIZE)
                 group_id: CustomUUID = CustomUUID.ZERO, # Group to own new prim
                 state: int = 0, # Attachment point if AddFlags.ATTACH_TO_ROOT or specific attachment
                 bypass_raycast: bool = True,
                 ray_start: Vector3 | None = None, # Agent position if None
                 ray_end: Vector3 | None = None,   # Calculated if None
                 ray_target_id: CustomUUID = CustomUUID.ZERO,
                 ray_end_is_intersection: bool = False,
                 header: PacketHeader | None = None):

        super().__init__(PacketType.ObjectAdd, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)

        # ObjectData Block fields (directly part of this packet)
        self.pcode = pcode
        self.material = material
        self.add_flags = add_flags

        # Path parameters
        self.path_curve = path_params.get('curve', PathCurve.LINE)
        self.path_begin = path_params.get('begin', 0.0)
        self.path_end = path_params.get('end', 1.0)
        self.path_scale_x = path_params.get('scale_x', 1.0)
        self.path_scale_y = path_params.get('scale_y', 1.0)
        self.path_shear_x = path_params.get('shear_x', 0.0)
        self.path_shear_y = path_params.get('shear_y', 0.0)
        self.path_twist = path_params.get('twist', 0.0)
        self.path_twist_begin = path_params.get('twist_begin', 0.0)
        self.path_radius_offset = path_params.get('radius_offset', 0.0)
        self.path_taper_x = path_params.get('taper_x', 0.0)
        self.path_taper_y = path_params.get('taper_y', 0.0)
        self.path_revolutions = path_params.get('revolutions', 1.0)
        self.path_skew = path_params.get('skew', 0.0)

        # Profile parameters
        self.profile_curve = profile_params.get('curve', ProfileCurve.SQUARE)
        self.profile_begin = profile_params.get('begin', 0.0)
        self.profile_end = profile_params.get('end', 1.0)
        self.profile_hollow = profile_params.get('hollow', 0.0) # Can be combined with HoleType

        self.position = position
        self.scale = scale
        self.rotation = rotation
        self.texture_entry_bytes = texture_entry_bytes
        self.group_id = group_id
        self.state = state # Attachment point if relevant

        self.bypass_raycast = bypass_raycast
        self.ray_start = ray_start if ray_start is not None else Vector3.ZERO # Placeholder, ObjectManager will set
        self.ray_end = ray_end if ray_end is not None else position # If bypass_raycast, position is RayEnd
        self.ray_target_id = ray_target_id
        self.ray_end_is_intersection = ray_end_is_intersection

        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())

        # ObjectData fields
        data.append(self.pcode.value & 0xFF)
        data.append(self.material.value & 0xFF)
        data.extend(helpers.uint32_to_bytes(self.add_flags.value))

        data.append(self.path_curve.value & 0xFF)
        data.extend(helpers.uint16_to_bytes(helpers.float_to_uint16_packed(self.path_begin, 0.0, 1.0)))
        data.extend(helpers.uint16_to_bytes(helpers.float_to_uint16_packed(self.path_end, 0.0, 1.0)))
        data.append(helpers.float_to_byte_packed(self.path_scale_x, -1.0, 1.0))
        data.append(helpers.float_to_byte_packed(self.path_scale_y, -1.0, 1.0))
        data.append(helpers.float_to_byte_packed(self.path_shear_x, -1.0, 1.0)) # C# uses 0-1 for shear, then scale to byte
        data.append(helpers.float_to_byte_packed(self.path_shear_y, -1.0, 1.0)) # This might need adjustment if C# scale is different
        data.append(helpers.scale_float_to_sbyte(self.path_twist, -1.0, 1.0))
        data.append(helpers.scale_float_to_sbyte(self.path_twist_begin, -1.0, 1.0))
        data.append(helpers.scale_float_to_sbyte(self.path_radius_offset, -1.0, 1.0))
        data.append(helpers.scale_float_to_sbyte(self.path_taper_x, -1.0, 1.0))
        data.append(helpers.scale_float_to_sbyte(self.path_taper_y, -1.0, 1.0))
        data.append(helpers.float_to_byte_packed(self.path_revolutions, 0.0, 4.0)) # Max 4.0 revolutions
        data.append(helpers.scale_float_to_sbyte(self.path_skew, -1.0, 1.0))

        data.append(self.profile_curve.value & 0xFF)
        data.extend(helpers.uint16_to_bytes(helpers.float_to_uint16_packed(self.profile_begin, 0.0, 1.0)))
        data.extend(helpers.uint16_to_bytes(helpers.float_to_uint16_packed(self.profile_end, 0.0, 1.0)))
        # ProfileHollow: C# uses a 16bit value where high byte is HoleType, low byte is hollow amount (0-255 for 0-100%)
        # For simplicity, sending hollow as a ushort for now, matching float_to_uint16_packed.
        # A more precise implementation would combine HoleType.
        data.extend(helpers.uint16_to_bytes(helpers.float_to_uint16_packed(self.profile_hollow, 0.0, 1.0)))

        data.extend(struct.pack('<fff', self.scale.X, self.scale.Y, self.scale.Z))
        data.extend(struct.pack('<ffff', self.rotation.X, self.rotation.Y, self.rotation.Z, self.rotation.W))
        data.extend(struct.pack('<fff', self.position.X, self.position.Y, self.position.Z))

        data.append(self.state & 0xFF) # Attachment point or 0
        data.extend(self.group_id.get_bytes())

        # TextureEntry for ObjectAddPacket is specifically 17 bytes:
        # DefaultTexture (16 bytes UUID) + MediaFlags (1 byte)
        te_bytes = self.texture_entry_bytes
        if len(te_bytes) == 17:
            data.extend(te_bytes)
        elif len(te_bytes) > 17:
            logger.warning(f"ObjectAddPacket: TextureEntry too long ({len(te_bytes)}), using first 17 bytes.")
            data.extend(te_bytes[:17])
        else: # len < 17
            logger.error(f"ObjectAddPacket: TextureEntry is too short ({len(te_bytes)}), expected 17 bytes. Padding with zeros.")
            data.extend(te_bytes)
            data.extend(bytes(17 - len(te_bytes))) # Pad with zeros to 17 bytes

        # Raycast block
        data.append(1 if self.bypass_raycast else 0)
        data.extend(struct.pack('<fff', self.ray_start.X, self.ray_start.Y, self.ray_start.Z))
        data.extend(struct.pack('<fff', self.ray_end.X, self.ray_end.Y, self.ray_end.Z))
        data.extend(self.ray_target_id.get_bytes())
        data.append(1 if self.ray_end_is_intersection else 0)

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectAddPacket.")
        return self


# --- ObjectNamePacket ---
@dataclasses.dataclass
class ObjectNameDataBlock:
    ObjectLocalID: int # u32
    Name: bytes # UTF-8 encoded, null-terminated string

class ObjectNamePacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_names: list[tuple[int, str]], # list of (local_id, name_str)
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectName, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectNameDataBlock] = []
        for local_id, name_str in object_names:
            # Name is limited in length by server (e.g., 63 bytes)
            name_bytes = name_str.encode('utf-8')[:63] + b'\0'
            self.object_data_blocks.append(ObjectNameDataBlock(ObjectLocalID=local_id, Name=name_bytes))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData Blocks
        data.append(len(self.object_data_blocks) & 0xFF) # Count byte
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.extend(block.Name) # Already null-terminated
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectNamePacket.")
        return self

# --- ObjectDescriptionPacket ---
@dataclasses.dataclass
class ObjectDescriptionDataBlock:
    ObjectLocalID: int # u32
    Description: bytes # UTF-8 encoded, null-terminated string

class ObjectDescriptionPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_descriptions: list[tuple[int, str]], # list of (local_id, desc_str)
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectDescription, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectDescriptionDataBlock] = []
        for local_id, desc_str in object_descriptions:
            # Description is limited (e.g., 127 bytes)
            desc_bytes = desc_str.encode('utf-8')[:127] + b'\0'
            self.object_data_blocks.append(ObjectDescriptionDataBlock(ObjectLocalID=local_id, Description=desc_bytes))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.extend(block.Description)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectDescriptionPacket.")
        return self

# --- ObjectTextPacket ---
@dataclasses.dataclass
class ObjectTextDataBlock:
    ObjectLocalID: int # u32
    Text: bytes # UTF-8 encoded, null-terminated string (hover text)

class ObjectTextPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_texts: list[tuple[int, str]], # list of (local_id, text_str)
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectText, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectTextDataBlock] = []
        for local_id, text_str in object_texts:
            # Text is limited (e.g., 255 bytes)
            text_bytes = text_str.encode('utf-8')[:254] + b'\0' # Ensure null termination within limit
            self.object_data_blocks.append(ObjectTextDataBlock(ObjectLocalID=local_id, Text=text_bytes))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.extend(block.Text)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectTextPacket.")
        return self

# --- ObjectClickActionPacket ---
@dataclasses.dataclass
class ObjectClickActionDataBlock:
    ObjectLocalID: int # u32
    ClickAction: int # u8, from ClickAction enum

class ObjectClickActionPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_click_actions: list[tuple[int, ClickAction]], # list of (local_id, click_action_enum)
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectClickAction, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data_blocks: list[ObjectClickActionDataBlock] = []
        for local_id, click_action_enum in object_click_actions:
            self.object_data_blocks.append(ObjectClickActionDataBlock(ObjectLocalID=local_id, ClickAction=click_action_enum.value))
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        data.append(len(self.object_data_blocks) & 0xFF)
        for block in self.object_data_blocks:
            data.extend(helpers.uint32_to_bytes(block.ObjectLocalID))
            data.append(block.ClickAction & 0xFF)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectClickActionPacket.")
        return self

# --- ObjectGrabPacket (Client -> Server) ---
@dataclasses.dataclass
class ObjectGrabObjectDataBlock:
    LocalID: int # u32
    GrabOffset: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    # Potentially GrabPosition, SurfaceInfoBlock etc. if more detail needed
    # For a simple touch, LocalID and a zero offset might suffice.

class ObjectGrabPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 local_id: int, grab_offset: Vector3 = Vector3.ZERO,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectGrab, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id) # Reusing common block
        self.object_data = ObjectGrabObjectDataBlock(LocalID=local_id, GrabOffset=grab_offset)
        # For a full implementation, one or more SurfaceInfo blocks might be here.
        # SurfaceInfo { FaceIndex (s32), Position (Vector3), Normal (Vector3), Binormal (Vector3), TexCoord (Vector2), Stride (s32), VertexIndex (s32) }
        # For now, simplifying to not include SurfaceInfo array.
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData
        data.extend(helpers.uint32_to_bytes(self.object_data.LocalID))
        data.extend(struct.pack('<fff', self.object_data.GrabOffset.X, self.object_data.GrabOffset.Y, self.object_data.GrabOffset.Z))
        # SurfaceInfo array would follow (count byte + blocks)
        data.append(0) # Assuming 0 SurfaceInfo blocks for simple touch
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectGrabPacket.")
        return self

# --- ObjectDeGrabPacket (Client -> Server) ---
@dataclasses.dataclass
class ObjectDeGrabObjectDataBlock:
    LocalID: int # u32
    # Potentially SurfaceInfoBlock if degrab needs to specify where it was released on surface.

class ObjectDeGrabPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 local_id: int,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ObjectDeGrab, header if header else PacketHeader())
        self.agent_data = ObjectManipulationAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.object_data = ObjectDeGrabObjectDataBlock(LocalID=local_id)
        # SurfaceInfo array might follow here too.
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ObjectData
        data.extend(helpers.uint32_to_bytes(self.object_data.LocalID))
        # SurfaceInfo array would follow (count byte + blocks)
        data.append(0) # Assuming 0 SurfaceInfo blocks for simple touch
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ObjectDeGrabPacket.")
        return self
