import logging
import struct

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.enums import TeleportFlags
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

# --- Outgoing Teleport Request Packets ---

class TeleportLandmarkRequestPacket(Packet):
    """Requests teleport to a landmark."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, landmark_id: CustomUUID,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportLandmarkRequest, header if header else PacketHeader())
        self.agent_id = agent_id
        self.session_id = session_id
        self.landmark_id = landmark_id # This is Info.LandmarkID in C#
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData block
        data.extend(self.agent_id.get_bytes())    # 16 bytes
        data.extend(self.session_id.get_bytes())  # 16 bytes
        # Info block
        data.extend(self.landmark_id.get_bytes()) # 16 bytes (LandmarkID)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("TeleportLandmarkRequestPacket.from_bytes_body should not be called on client.")
        return self


class TeleportLocationRequestPacket(Packet):
    """Requests teleport to a specific location (region handle, position, lookat)."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 region_handle: int, position: Vector3, look_at: Vector3,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportLocationRequest, header if header else PacketHeader())
        self.agent_id = agent_id
        self.session_id = session_id
        self.region_handle = region_handle # u64
        self.position = position # Vector3 (12 bytes)
        self.look_at = look_at   # Vector3 (12 bytes)
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData block
        data.extend(self.agent_id.get_bytes())    # 16
        data.extend(self.session_id.get_bytes())  # 16
        # Info block
        data.extend(helpers.uint64_to_bytes(self.region_handle)) # 8
        data.extend(struct.pack('<fff', self.position.X, self.position.Y, self.position.Z)) # 12
        data.extend(struct.pack('<fff', self.look_at.X, self.look_at.Y, self.look_at.Z))    # 12
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("TeleportLocationRequestPacket.from_bytes_body should not be called on client.")
        return self

class TeleportCancelPacket(Packet):
    """Sent by client to cancel an ongoing teleport, or received if server cancels."""
    def __init__(self, agent_id: CustomUUID | None = None, session_id: CustomUUID | None = None,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportCancel, header if header else PacketHeader())
        self.agent_id = agent_id # Only needed for sending
        self.session_id = session_id # Only needed for sending
        # This packet is often just a header, but if it has Agent/Session, it's for context.
        # C# version has an Info block with AgentID/SessionID, but it's often empty from server.
        self.header.reliable = True # Should be reliable if client sends to cancel.

    def to_bytes(self) -> bytes: # When client sends to cancel
        if self.agent_id and self.session_id:
            data = bytearray()
            data.extend(self.agent_id.get_bytes())
            data.extend(self.session_id.get_bytes())
            return bytes(data)
        return b'' # Empty body if server sends it or no specific agent/session context

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # Server might send this with no body, or with Agent/Session.
        if length >= 32: # AgentID + SessionID
            self.agent_id = CustomUUID(buffer, offset); offset += 16
            self.session_id = CustomUUID(buffer, offset)
        else: # Assume no specific agent/session data if body is short
            self.agent_id = CustomUUID.ZERO
            self.session_id = CustomUUID.ZERO
        logger.info(f"Parsed TeleportCancelPacket. Agent: {self.agent_id}, Session: {self.session_id}")
        return self


# --- Incoming Teleport Status Packets (Primarily for Deserialization) ---

class TeleportStartPacket(Packet):
    """Server indicates teleport is starting."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportStart, header if header else PacketHeader())
        self.teleport_flags: TeleportFlags = TeleportFlags.NONE # u32

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < 4: raise ValueError("TeleportStart body too short.")
        self.teleport_flags = TeleportFlags(helpers.bytes_to_uint32(buffer, offset))
        return self
    def to_bytes(self) -> bytes: logger.warning("Client does not send TeleportStart."); return b''

class TeleportProgressPacket(Packet):
    """Server sends progress updates during teleport."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportProgress, header if header else PacketHeader())
        self.message: bytes = b'' # Variable null-terminated string
        self.teleport_flags: TeleportFlags = TeleportFlags.NONE # u32
        self.agent_id: CustomUUID = CustomUUID.ZERO # AgentData block

    @property
    def message_str(self) -> str: return self.message.decode('utf-8', errors='replace')

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # AgentData block (AgentID)
        if length < 16 + 1: raise ValueError("TeleportProgress body too short for AgentID.")
        self.agent_id = CustomUUID(buffer, offset); offset += 16

        # Message block (Message, TeleportFlags)
        # Message is variable length, null-terminated
        msg_end = buffer.find(b'\x00', offset)
        if msg_end == -1 or msg_end > offset + 255 : # Sanity limit for message length
            logger.warning("No null terminator for message in TeleportProgress or too long.")
            # Decide how to handle - error, or take portion?
            # For now, assume it's at least up to flags.
            # If message is truly variable and flags are after, need careful parsing.
            # C# struct: AgentID, Message (string), TeleportFlags (uint)
            # Assuming message is null-terminated before flags.
            self.message = buffer[offset : min(offset + 255, length - 4)] # Take up to 255 or before flags
            offset += len(self.message) + 1 # Advance past message and its null
        else:
            self.message = buffer[offset:msg_end]; offset = msg_end + 1

        if offset + 4 > length: raise ValueError("TeleportProgress body too short for TeleportFlags.")
        self.teleport_flags = TeleportFlags(helpers.bytes_to_uint32(buffer, offset))
        return self
    def to_bytes(self) -> bytes: logger.warning("Client does not send TeleportProgress."); return b''

class TeleportFailedPacket(Packet):
    """Server indicates teleport failed."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportFailed, header if header else PacketHeader())
        self.reason: bytes = b'' # Variable null-terminated string
        self.agent_id: CustomUUID = CustomUUID.ZERO # In AgentData block
        self.alert_flags: int = 0 # u32, in Info block. C# AlertFlags enum.
        # For now, just store reason. AgentID might be in AgentData block.

    @property
    def reason_str(self) -> str: return self.reason.decode('utf-8', errors='replace')

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # AgentData block (AgentID)
        if length < 16 + 1: raise ValueError("TeleportFailed body too short for AgentID.")
        self.agent_id = CustomUUID(buffer, offset); offset += 16

        # Info block (Reason string, AlertFlags u32)
        # Reason is variable length, null-terminated
        reason_end = buffer.find(b'\x00', offset)
        if reason_end == -1 or reason_end > offset + 255: # Sanity limit
            self.reason = buffer[offset : min(offset + 255, length - 4)]
            offset += len(self.reason) +1
        else:
            self.reason = buffer[offset:reason_end]; offset = reason_end + 1

        if offset + 4 <= length : # Check if AlertFlags are present
             self.alert_flags = helpers.bytes_to_uint32(buffer, offset)
        else: self.alert_flags = 0 # Default if not present

        return self
    def to_bytes(self) -> bytes: logger.warning("Client does not send TeleportFailed."); return b''

class TeleportFinishPacket(Packet):
    """Server signals completion of teleport and provides new sim details."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportFinish, header if header else PacketHeader())
        self.agent_id: CustomUUID = CustomUUID.ZERO
        self.region_handle: int = 0 # u64
        self.sim_ip_uint32: int = 0 # u32, network byte order (big endian)
        self.sim_port: int = 0 # u16, network byte order
        self.location_id: int = 0 # u32, for local teleports
        self.teleport_flags: TeleportFlags = TeleportFlags.NONE # u32
        self.seed_capability: bytes = b'' # Variable, max 255 + null
        self.region_size_x: int = 256 # u32, default if not in packet
        self.region_size_y: int = 256 # u32, default if not in packet

    @property
    def sim_ip_str(self) -> str: return helpers.bytes_to_ip_address(helpers.uint32_to_bytes_big_endian(self.sim_ip_uint32)).__str__()

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # AgentID(16) + RegionHandle(8) + LocationID(4) + SimIP(4) + SimPort(2) + TeleportFlags(4)
        # + SeedCapability (var) + SimAccess (1, optional) + RegionSizeX (4, optional) + RegionSizeY (4, optional)
        # Min approx: 16+8+4+4+2+4 = 38 bytes, + SeedCap (min 1 byte for null term) = 39
        min_len = 38
        if length < min_len: raise ValueError(f"TeleportFinish body too short: {length}")

        self.agent_id = CustomUUID(buffer, offset); offset += 16
        self.region_handle = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.location_id = helpers.bytes_to_uint32(buffer, offset); offset += 4 # Often 0 for inter-sim
        self.sim_ip_uint32 = helpers.bytes_to_uint32_big_endian(buffer, offset); offset += 4 # Big Endian for IP
        self.sim_port = helpers.bytes_to_uint16_big_endian(buffer, offset); offset += 2 # Big Endian for port
        self.teleport_flags = TeleportFlags(helpers.bytes_to_uint32(buffer, offset)); offset += 4

        # SeedCapability (variable string, null-terminated)
        seed_cap_end = buffer.find(b'\x00', offset)
        if seed_cap_end != -1:
            self.seed_capability = buffer[offset:seed_cap_end]
            offset = seed_cap_end + 1
        else: # Should have a null terminator, even if empty string
            logger.warning("TeleportFinish: No null terminator for SeedCapability.")
            self.seed_capability = b''
            # Try to advance offset past where a null would be if it's just missing from short packet
            if offset < length : offset +=1


        # Optional RegionSizeX and RegionSizeY (added in later versions of protocol)
        if offset + 4 <= length: # Check for RegionSizeX
            self.region_size_x = helpers.bytes_to_uint32(buffer, offset); offset += 4
        if offset + 4 <= length: # Check for RegionSizeY
            self.region_size_y = helpers.bytes_to_uint32(buffer, offset); offset += 4

        return self
    def to_bytes(self) -> bytes: logger.warning("Client does not send TeleportFinish."); return b''

class TeleportLocalPacket(Packet): # Server sends this for in-sim teleports (TP Lure Request)
    """Server signals a local (within-sim) teleport or TP lure."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TeleportLocal, header if header else PacketHeader())
        self.location_id: int = 0 # u32
        self.position: Vector3 = Vector3.ZERO
        self.look_at: Vector3 = Vector3.ZERO
        self.teleport_flags: TeleportFlags = TeleportFlags.NONE # u32

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # LocationID(4) + Position(12) + LookAt(12) + TeleportFlags(4) = 32 bytes
        if length < 32: raise ValueError("TeleportLocal body too short.")
        self.location_id = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.position = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12
        self.look_at = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12
        self.teleport_flags = TeleportFlags(helpers.bytes_to_uint32(buffer, offset))
        return self
    def to_bytes(self) -> bytes: logger.warning("Client does not send TeleportLocal this way."); return b''


@dataclasses.dataclass
class StartLureDataAgentDataBlock: # Simplified, matches C# structure for this packet
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class StartLureDataInfoBlock: # Simplified
    LureType: int # Actually a byte in C#
    Message: bytes # UTF-8 encoded, null-terminated

@dataclasses.dataclass
class StartLureDataTargetDataBlock: # Simplified
    TargetID: CustomUUID


class StartLurePacket(Packet):
    """Client sends this to offer a teleport lure to another agent."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 lure_type: int, message: str, target_id: CustomUUID,
                 header: PacketHeader | None = None):
        # On-wire ID 0xFFFFFF35 (Low Freq, ID 0x35 / 53)
        super().__init__(PacketType.StartLure, header if header else PacketHeader())
        self.agent_data = StartLureDataAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.info = StartLureDataInfoBlock(LureType=lure_type, Message=message.encode('utf-8'))
        # TargetData is an array in C#, but for a single lure, it's one target.
        self.target_data: list[StartLureDataTargetDataBlock] = [StartLureDataTargetDataBlock(TargetID=target_id)]
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # Info
        data.append(self.info.LureType & 0xFF) # LureType is u8

        msg_bytes = self.info.Message # Already bytes
        if len(msg_bytes) > 1023: msg_bytes = msg_bytes[:1023] # Max length
        data.extend(msg_bytes)
        data.append(0) # Null terminator for message

        # TargetData Array (count + elements)
        # Assuming only one target for now, as is typical for client sending.
        data.append(len(self.target_data) & 0xFF) # Count of targets (u8)
        for target_block in self.target_data:
            data.extend(target_block.TargetID.get_bytes())

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("StartLurePacket.from_bytes_body should not be called on client.")
        return self


@dataclasses.dataclass
class TeleportLureRequestInfoBlock: # Simplified for client sending
    AgentID: CustomUUID
    SessionID: CustomUUID
    LureID: CustomUUID # This is the IM SessionID of the lure offer
    TeleportFlags: int # Actually u32, use TeleportFlags.value


class TeleportLureRequestPacket(Packet):
    """Client sends this to accept a teleport lure and initiate the teleport."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 lure_id: CustomUUID, teleport_flags: TeleportFlags,
                 header: PacketHeader | None = None):
        # Uses PacketType.TeleportLocal's on-wire ID (0xFFFFFF0F)
        super().__init__(PacketType.TeleportLocal, header if header else PacketHeader())
        self.info = TeleportLureRequestInfoBlock(
            AgentID=agent_id, SessionID=session_id,
            LureID=lure_id, TeleportFlags=teleport_flags.value
        )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # Info Block
        data.extend(self.info.AgentID.get_bytes())
        data.extend(self.info.SessionID.get_bytes())
        data.extend(self.info.LureID.get_bytes())
        data.extend(helpers.uint32_to_bytes(self.info.TeleportFlags))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # This specific structure (client accepting lure) is not typically received by client.
        # The server sends TeleportLocalPacket with a different structure.
        logger.warning("TeleportLureRequestPacket.from_bytes_body (client acceptance structure) not expected from server.")
        # If we needed to parse it, it would be:
        # self.info.AgentID = CustomUUID(buffer, offset); offset += 16
        # self.info.SessionID = CustomUUID(buffer, offset); offset += 16
        # self.info.LureID = CustomUUID(buffer, offset); offset += 16
        # self.info.TeleportFlags = TeleportFlags(helpers.bytes_to_uint32(buffer, offset))
        return self
