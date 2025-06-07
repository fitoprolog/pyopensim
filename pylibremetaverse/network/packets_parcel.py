import logging
import struct
import dataclasses
from datetime import datetime, timezone
from typing import List # Added for type hinting

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.enums import AssetType, ParcelFlags, ParcelCategory, ParcelStatus, PacketType
from pylibremetaverse.types.parcel_defs import ParcelPrimOwnerData, ParcelACLFlags # Added imports
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader

logger = logging.getLogger(__name__)

# --- ParcelPropertiesRequestPacket (Client -> Server) ---
@dataclasses.dataclass
class ParcelPropertiesRequestAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class ParcelPropertiesRequestParcelDataBlock:
    SequenceID: int = 0 # int32, client sets, server echoes
    West: float = 0.0
    South: float = 0.0
    East: float = 0.0
    North: float = 0.0
    GetSelected: bool = False # True to get properties of currently selected parcel
    SnapSelection: bool = False # True to snap the returned parcel ID (SnapKey) to the center of the parcel

class ParcelPropertiesRequestPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 position_coord: Vector3, sequence_id: int = 0,
                 get_selected: bool = False, snap_selection: bool = False,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ParcelPropertiesRequest, header if header else PacketHeader())
        self.agent_data = ParcelPropertiesRequestAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        # For a request at a specific coordinate, W, S, E, N are all set to that coordinate's
        # containing parcel. The server figures out the parcel from one point.
        # Using the same value for W/E and S/N effectively targets a point.
        self.parcel_data = ParcelPropertiesRequestParcelDataBlock(
            SequenceID=sequence_id,
            West=position_coord.X, South=position_coord.Y,
            East=position_coord.X, North=position_coord.Y, # Server uses these to find containing parcel
            GetSelected=get_selected, SnapSelection=snap_selection
        )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentDataBlock
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # ParcelDataBlock
        pd = self.parcel_data
        data.extend(helpers.int32_to_bytes(pd.SequenceID))
        data.extend(struct.pack('<f', pd.West))
        data.extend(struct.pack('<f', pd.South))
        data.extend(struct.pack('<f', pd.East))
        data.extend(struct.pack('<f', pd.North))
        data.append(1 if pd.GetSelected else 0)
        data.append(1 if pd.SnapSelection else 0)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ParcelPropertiesRequestPacket.")
        return self


# --- ParcelPropertiesPacket (Server -> Client) ---
@dataclasses.dataclass
class ParcelPropertiesAgentDataBlock: # Matches C# AgentData
    AgentID: CustomUUID # Our AgentID
    # SessionID: CustomUUID # Not explicitly in C# ParcelPropertiesPacket.AgentData, but often part of wrapper

@dataclasses.dataclass
class ParcelPropertiesParcelDataBlock: # Matches C# ParcelData
    RequestResult: int = 0 # int32, result of the request (e.g., 0 for success)
    SequenceID: int = 0    # int32, echoed from request
    SnapKey: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # GlobalID of the parcel
    LocalID: int = 0       # int32
    OwnerID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    IsGroupOwned: bool = False # u8
    Name: bytes = b''          # Max 128 bytes, null-terminated
    Desc: bytes = b''          # Max 255 bytes, null-terminated
    ActualArea: int = 0    # int32
    BillableArea: int = 0  # int32
    Flags: int = 0         # uint32 (ParcelFlags)
    GlobalX: float = 0.0   # float
    GlobalY: float = 0.0   # float
    GlobalZ: float = 0.0   # float (height of parcel surface at SW corner)
    SimName: bytes = b''       # Max 64 bytes, null-terminated
    SnapshotID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    MediaURL: bytes = b''      # Max 255 bytes, null-terminated
    MusicURL: bytes = b''      # Max 255 bytes, null-terminated
    PassHours: float = 0.0 # float
    PassPrice: int = 0     # int32
    SalePrice: int = 0     # int32
    AuctionID: int = 0     # uint32
    Category: int = 0      # u8 (ParcelCategory)
    Status: int = 0        # sbyte (ParcelStatus) - check C# for actual type and values
    LandingType: int = 0   # u8
    AuthBuyerID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    MediaDesc: bytes = b''     # Max 255 bytes
    MediaWidth: int = 0    # int16
    MediaHeight: int = 0   # int16
    MediaLoop: bool = False    # u8
    MediaType: bytes = b''     # Max 32 bytes (MIME type)
    ObscureMusicURL: bytes = b'' # Max 255 bytes
    # ObscureMediaURL: bytes = b'' # Max 255 bytes - This seems to be a typo from some sources, OpenMetaverse has ObscureMusicURL but not ObscureMediaURL directly in ParcelData.
    SeeOtherCleanTime: int = 0 # int32 (unused by modern viewers)
    RegionUUID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Added, from C# ParcelData

    # ParcelPrimOwnersData
    PrimOwners: list[ParcelPrimOwnerData] = dataclasses.field(default_factory=list)


    # Helper properties for string conversion
    @property
    def name_str(self) -> str: return helpers.bytes_to_string(self.Name)
    @property
    def description_str(self) -> str: return helpers.bytes_to_string(self.Desc)
    @property
    def sim_name_str(self) -> str: return helpers.bytes_to_string(self.SimName)
    @property
    def media_url_str(self) -> str: return helpers.bytes_to_string(self.MediaURL)
    @property
    def music_url_str(self) -> str: return helpers.bytes_to_string(self.MusicURL)
    @property
    def media_desc_str(self) -> str: return helpers.bytes_to_string(self.MediaDesc)
    @property
    def media_type_str(self) -> str: return helpers.bytes_to_string(self.MediaType)
    @property
    def obscure_music_url_str(self) -> str: return helpers.bytes_to_string(self.ObscureMusicURL)
    # def obscure_media_url_str(self) -> str: return helpers.bytes_to_string(self.ObscureMediaURL)


class ParcelPropertiesPacket(Packet): # Server -> Client
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ParcelProperties, header if header else PacketHeader())
        # AgentData is not explicitly part of ParcelProperties's main structure in C#,
        # but the packet is sent to a specific agent. We'll parse it if it's there for context.
        self.agent_data_placeholder = ParcelPropertiesAgentDataBlock(AgentID=CustomUUID.ZERO) # Placeholder
        self.parcel_data = ParcelPropertiesParcelDataBlock() # Single block for this packet type

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "ParcelPropertiesPacket":
        initial_offset = offset
        pd = self.parcel_data

        # AgentData (AgentID is part of the packet structure in some interpretations, let's assume it is)
        # self.agent_data_placeholder.AgentID = CustomUUID(buffer, offset); offset += 16
        # For ParcelProperties, C# does not have AgentData block in the packet body itself.
        # It's implied by the recipient. The ParcelData block starts immediately.

        pd.RequestResult = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.SequenceID = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.SnapKey = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        pd.LocalID = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.OwnerID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        pd.IsGroupOwned = buffer[offset] != 0; offset += 1

        pd.Name, read = helpers.read_sized_string_bytes(buffer, offset, 128); offset += read
        pd.Desc, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read

        pd.ActualArea = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.BillableArea = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.Flags = helpers.bytes_to_uint32(buffer, offset); offset += 4 # ParcelFlags

        pd.GlobalX = helpers.bytes_to_float(buffer, offset); offset += 4
        pd.GlobalY = helpers.bytes_to_float(buffer, offset); offset += 4
        pd.GlobalZ = helpers.bytes_to_float(buffer, offset); offset += 4

        pd.SimName, read = helpers.read_sized_string_bytes(buffer, offset, 64); offset += read
        pd.SnapshotID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        pd.MediaURL, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read
        pd.MusicURL, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read

        pd.PassHours = helpers.bytes_to_float(buffer, offset); offset += 4
        pd.PassPrice = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.SalePrice = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.AuctionID = helpers.bytes_to_uint32(buffer, offset); offset += 4

        pd.Category = buffer[offset]; offset += 1 # u8
        pd.Status = struct.unpack_from('<b', buffer, offset)[0]; offset += 1 # sbyte
        pd.LandingType = buffer[offset]; offset += 1 # u8
        pd.AuthBuyerID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        pd.MediaDesc, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read
        pd.MediaWidth = helpers.bytes_to_int16(buffer, offset); offset += 2
        pd.MediaHeight = helpers.bytes_to_int16(buffer, offset); offset += 2
        pd.MediaLoop = buffer[offset] != 0; offset += 1
        pd.MediaType, read = helpers.read_sized_string_bytes(buffer, offset, 32); offset += read

        pd.ObscureMusicURL, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read
        # pd.ObscureMediaURL, read = helpers.read_sized_string_bytes(buffer, offset, 255); offset += read # See note above

        pd.SeeOtherCleanTime = helpers.bytes_to_int32(buffer, offset); offset += 4
        pd.RegionUUID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # Parse ParcelPrimOwnersData
        prim_owner_count = buffer[offset]; offset += 1 # Count is 1 byte
        pd.PrimOwners = []
        for _ in range(prim_owner_count):
            owner_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            count = helpers.bytes_to_int32(buffer, offset); offset += 4
            pd.PrimOwners.append(ParcelPrimOwnerData(owner_id=owner_id, count=count))

        # logger.debug(f"ParcelPropertiesPacket parsed. Read {offset - initial_offset} bytes, expected {length}.")
        # if offset - initial_offset != length:
        #     logger.warning(f"ParcelPropertiesPacket: Mismatch in expected length. Read {offset - initial_offset}, expected {length}")
        return self

    def to_bytes(self) -> bytes:
        logger.warning("Client does not send ParcelPropertiesPacket.")
        return b''

if __name__ == '__main__':
    print("Testing Parcel Packets...")
    agent_id_test = CustomUUID.random()
    session_id_test = CustomUUID.random()
    pos_test = Vector3(128.0, 64.0, 72.0)

    req_pkt = ParcelPropertiesRequestPacket(agent_id_test, session_id_test, pos_test, sequence_id=123)
    req_bytes = req_pkt.to_bytes()
    print(f"ParcelPropertiesRequestPacket: {len(req_bytes)} bytes. Hex: {req_bytes.hex()}")
    # Expected: 16+16 (AgentData) + 4 (SeqID) + 4*4 (Floats) + 1 (GetSelected) + 1 (SnapSelection) = 32 + 4 + 16 + 2 = 54 bytes
    assert len(req_bytes) == 54

    # Conceptual test for ParcelPropertiesPacket (server -> client)
    # No direct to_bytes test as client doesn't send it.
    # Example construction for from_bytes testing would be complex.
    prop_pkt = ParcelPropertiesPacket()
    # prop_pkt.from_bytes_body(...) -> needs sample byte data
    print("ParcelPropertiesPacket structure defined.")
    print("Parcel packet tests conceptualized.")


# --- ParcelAccessListRequestPacket (Client -> Server) ---
@dataclasses.dataclass
class ParcelAccessListRequestAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class ParcelAccessListRequestDataBlock:
    SequenceID: int    # int32
    Flags: int         # uint32 (typically 0 for all, 1 for group, 2 for allowed, 4 for banned)
    ParcelLocalID: int # int32

class ParcelAccessListRequestPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 parcel_local_id: int, sequence_id: int = 0, request_flags: int = 0,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ParcelAccessListRequest, header if header else PacketHeader())
        self.agent_data = ParcelAccessListRequestAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.data_block = ParcelAccessListRequestDataBlock(
            SequenceID=sequence_id, Flags=request_flags, ParcelLocalID=parcel_local_id
        )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentDataBlock
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # DataBlock
        db = self.data_block
        data.extend(helpers.int32_to_bytes(db.SequenceID))
        data.extend(helpers.uint32_to_bytes(db.Flags))
        data.extend(helpers.int32_to_bytes(db.ParcelLocalID))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ParcelAccessListRequestPacket.")
        return self

# --- ParcelAccessListReplyPacket (Server -> Client) ---
@dataclasses.dataclass
class ParcelAccessListReplyAgentDataBlock: # Typically our own agent info
    AgentID: CustomUUID
    SessionID: CustomUUID # Though often not strictly part of this packet's core data in some viewers

@dataclasses.dataclass
class ParcelAccessListReplyDataBlock:
    SequenceID: int
    Flags: int # uint32, echoed from request or server state
    ParcelLocalID: int
    TransactionID: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Often zero

@dataclasses.dataclass
class ParcelAccessListReplyAccessDataBlock: # Repeated block for each entry
    ID: CustomUUID      # Agent or Group UUID
    Time: int           # int32, often legacy (0)
    AccessFlags: int    # uint32 (ParcelACLFlags)

class ParcelAccessListReplyPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ParcelAccessListReply, header if header else PacketHeader())
        self.agent_data = ParcelAccessListReplyAgentDataBlock(AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO)
        self.data_block = ParcelAccessListReplyDataBlock(SequenceID=0, Flags=0, ParcelLocalID=0)
        self.access_data_blocks: List[ParcelAccessListReplyAccessDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "ParcelAccessListReplyPacket":
        # AgentDataBlock
        self.agent_data.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.SessionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # DataBlock
        db = self.data_block
        db.SequenceID = helpers.bytes_to_int32(buffer, offset); offset += 4
        db.Flags = helpers.bytes_to_uint32(buffer, offset); offset += 4
        db.ParcelLocalID = helpers.bytes_to_int32(buffer, offset); offset += 4
        db.TransactionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # AccessDataBlocks (Array)
        # The count of AccessDataBlocks is determined by the remaining length of the packet
        # Each AccessDataBlock is UUID (16) + Time (4) + AccessFlags (4) = 24 bytes
        access_block_size = 24
        num_access_blocks = 0
        if (length - (offset - 0)) > 0 : # Check if there's remaining data for access blocks
            # The number of blocks is usually prefixed by a byte or derived from total length.
            # Assuming it's derived from total length for now as per some packet formats.
            # If a count byte is present, it needs to be read first.
            # Let's assume the problem description implies it's derived from remaining length.
             remaining_length = length - (16+16+4+4+4+16) # agent_id, session_id, seq, flags, localid, transid
             if remaining_length % access_block_size == 0:
                 num_access_blocks = remaining_length // access_block_size
             else:
                 logger.warning(f"ParcelAccessListReply: Unexpected remaining length {remaining_length} for access blocks.")
                 # Potentially, there's a count byte. For now, we'll proceed if it's a clean division.
                 # If not, this will likely lead to errors or incomplete parsing.
                 # A more robust parser would check a count field if the protocol specifies one.
                 # For now, we'll assume no explicit count field and rely on packet length.

        self.access_data_blocks = []
        for _ in range(num_access_blocks):
            if offset + access_block_size > len(buffer): # Boundary check
                logger.error("ParcelAccessListReply: Buffer overrun while parsing access data blocks.")
                break
            acc_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            acc_time = helpers.bytes_to_int32(buffer, offset); offset += 4
            acc_flags = helpers.bytes_to_uint32(buffer, offset); offset += 4
            self.access_data_blocks.append(
                ParcelAccessListReplyAccessDataBlock(ID=acc_id, Time=acc_time, AccessFlags=acc_flags)
            )

        return self

    def to_bytes(self) -> bytes:
        logger.warning("Client does not send ParcelAccessListReplyPacket.")
        return b''
