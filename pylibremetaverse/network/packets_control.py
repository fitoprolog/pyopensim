import logging
import struct

from .packets_base import Packet, PacketHeader, PacketType, PacketFlags
from pylibremetaverse.types import CustomUUID
from pylibremetaverse.utils import helpers

logger = logging.getLogger(__name__)

class UseCircuitCodePacket(Packet):
    def __init__(self, circuit_code: int, session_id: CustomUUID, agent_id: CustomUUID, header: PacketHeader | None = None):
        super().__init__(PacketType.UseCircuitCode, header if header else PacketHeader())
        self.circuit_code: int = circuit_code
        self.session_id: CustomUUID = session_id
        self.agent_id: CustomUUID = agent_id
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(helpers.uint32_to_bytes(self.circuit_code))
        data.extend(self.session_id.get_bytes())
        data.extend(self.agent_id.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (4 + 16 + 16):
            raise ValueError(f"UseCircuitCodePacket body too short. Expected {4+16+16}, got {length}")
        self.circuit_code = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.session_id = CustomUUID(buffer, offset); offset += 16
        self.agent_id = CustomUUID(buffer, offset)
        return self

    def __repr__(self):
        return (f"<UseCircuitCodePacket Code={self.circuit_code} SessionID={self.session_id} "
                f"AgentID={self.agent_id} Seq={self.header.sequence}>")

class RegionHandshakePacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.RegionHandshake, header if header else PacketHeader())
        self.region_flags: int = 0
        self.sim_access: int = 0
        self.sim_name: bytes = b''
        self.sim_name_str: str = ""
        self.sim_owner: CustomUUID = CustomUUID.ZERO
        self.terrain_base: list[float] = [0.0]*4
        self.terrain_detail: list[float] = [0.0]*4
        self.water_height: float = 0.0
        self.billable_factor: float = 0.0
        self.cache_id: CustomUUID = CustomUUID.ZERO
        self.terrain_start_x: float = 0.0
        self.terrain_start_y: float = 0.0
        self.region_id: CustomUUID = CustomUUID.ZERO

    def to_bytes(self) -> bytes:
        logger.warning("RegionHandshakePacket.to_bytes() not typically implemented (client receives this).")
        return b''

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset
        # Simplified min length check, actual parsing is more robust.
        if length < 86:
             logger.warning(f"RegionHandshakePacket body might be too short. Length: {length}")
             # Fall through and try to parse, errors will be caught by struct or index issues.

        try:
            self.region_flags = helpers.bytes_to_uint32(buffer, offset); offset += 4
            self.sim_access = buffer[offset]; offset += 1

            sim_name_end = -1
            search_limit = min(initial_offset + length, offset + 255)
            for i in range(offset, search_limit):
                if buffer[i] == 0: sim_name_end = i; break

            if sim_name_end != -1:
                self.sim_name = buffer[offset:sim_name_end]
                offset = sim_name_end + 1
            else:
                safe_len = min(search_limit - offset, 32)
                self.sim_name = buffer[offset : offset + safe_len]
                offset += safe_len
                if offset < search_limit and (safe_len > 0 and buffer[offset-1] != 0):
                     logger.warning(f"Sim name might be truncated in RegionHandshake.")
            self.sim_name_str = self.sim_name.decode('utf-8', errors='replace')

            self.sim_owner = CustomUUID(buffer, offset); offset += 16
            self.terrain_base = [helpers.bytes_to_float(buffer, offset + i*4) for i in range(4)]; offset += 16
            self.terrain_detail = [helpers.bytes_to_float(buffer, offset + i*4) for i in range(4)]; offset += 16
            self.water_height = helpers.bytes_to_float(buffer, offset); offset += 4
            self.billable_factor = helpers.bytes_to_float(buffer, offset); offset += 4
            self.cache_id = CustomUUID(buffer, offset); offset += 16
            self.terrain_start_x = helpers.bytes_to_float(buffer, offset); offset += 4
            self.terrain_start_y = helpers.bytes_to_float(buffer, offset); offset += 4
            self.region_id = CustomUUID(buffer, offset); offset += 16

            logger.info(f"Parsed RegionHandshake: Name='{self.sim_name_str}', RegionID={self.region_id}")
        except struct.error as e:
            raise ValueError(f"RegionHandshake struct error: {e}") from e
        except IndexError as e:
            raise ValueError(f"RegionHandshake index error (packet too short?): {e}") from e
        return self

class RegionHandshakeReplyPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, flags: int = 0, header: PacketHeader | None = None):
        super().__init__(PacketType.RegionHandshakeReply, header if header else PacketHeader())
        self.agent_id = agent_id
        self.session_id = session_id
        self.flags = flags
        self.header.reliable = True
    def to_bytes(self) -> bytes:
        data = bytearray(); data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes()); data.extend(helpers.uint32_to_bytes(self.flags))
        return bytes(data)
    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (16+16+4): raise ValueError("Body too short.")
        self.agent_id = CustomUUID(buffer, offset); offset += 16
        self.session_id = CustomUUID(buffer, offset); offset += 16
        self.flags = helpers.bytes_to_uint32(buffer, offset)
        return self

class CompleteAgentMovementPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, circuit_code: int, header: PacketHeader | None = None):
        super().__init__(PacketType.CompleteAgentMovement, header if header else PacketHeader())
        self.agent_id = agent_id; self.session_id = session_id; self.circuit_code = circuit_code
        self.header.reliable = True
    def to_bytes(self) -> bytes:
        data = bytearray(); data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes()); data.extend(helpers.uint32_to_bytes(self.circuit_code))
        return bytes(data)
    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (16+16+4): raise ValueError("Body too short.")
        self.agent_id = CustomUUID(buffer, offset); offset += 16
        self.session_id = CustomUUID(buffer, offset); offset += 16
        self.circuit_code = helpers.bytes_to_uint32(buffer, offset)
        return self

class AgentThrottlePacket(Packet):
    THROTTLE_BUFFER_SIZE = 28
    def __init__(self, throttle_values: bytes | None = None, header: PacketHeader | None = None):
        super().__init__(PacketType.AgentThrottle, header if header else PacketHeader())
        if throttle_values and len(throttle_values) != self.THROTTLE_BUFFER_SIZE:
            raise ValueError(f"Throttle values must be {self.THROTTLE_BUFFER_SIZE} bytes.")
        self.throttle_values: bytes = throttle_values if throttle_values else b'\x00' * self.THROTTLE_BUFFER_SIZE
    def to_bytes(self) -> bytes: return self.throttle_values
    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < self.THROTTLE_BUFFER_SIZE: raise ValueError("Body too short.")
        self.throttle_values = buffer[offset : offset + self.THROTTLE_BUFFER_SIZE]
        return self

class EconomyDataRequestPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.EconomyDataRequest, header if header else PacketHeader())
    def to_bytes(self) -> bytes: return b''
    def from_bytes_body(self, buffer: bytes, offset: int, length: int): return self

class LogoutRequestPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, header: PacketHeader | None = None):
        super().__init__(PacketType.LogoutRequest, header if header else PacketHeader())
        self.agent_id = agent_id; self.session_id = session_id
        self.header.reliable = True
    def to_bytes(self) -> bytes:
        data = bytearray(); data.extend(self.agent_id.get_bytes()); data.extend(self.session_id.get_bytes())
        return bytes(data)
    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (16+16): raise ValueError("Body too short.")
        self.agent_id = CustomUUID(buffer, offset); offset += 16
        self.session_id = CustomUUID(buffer, offset)
        return self

class CloseCircuitPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.CloseCircuit, header if header else PacketHeader())
    def to_bytes(self) -> bytes: return b''
    def from_bytes_body(self, buffer: bytes, offset: int, length: int): return self

class AckPacket(Packet):
    """Packet containing one or more ACKs (PacketAck / MSG_RELIABLE type)."""
    def __init__(self, sequences: list[int] | None = None, header: PacketHeader | None = None):
        super().__init__(PacketType.PacketAck, header if header else PacketHeader())
        self.sequences: list[int] = sequences if sequences is not None else []
        self.header.reliable = False # ACKs are not themselves reliable

    def to_bytes(self) -> bytes:
        if not self.sequences: return b'\x00' # Count byte must exist
        count = len(self.sequences)
        if count > 255:
            logger.warning(f"AckPacket: Too many sequences ({count}), trimming to 255.")
            self.sequences = self.sequences[:255]; count = 255
        data = bytearray(); data.append(count)
        for seq in self.sequences: data.extend(helpers.uint32_to_bytes(seq))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length == 0: self.sequences = []; return self # Should have at least count byte
        count = buffer[offset]; offset += 1
        self.sequences = []
        expected_len = 1 + count * 4
        if length < expected_len:
            logger.error(f"AckPacket body too short. Expected {expected_len}, got {length}. Count: {count}")
            count = (length -1) // 4 # Max possible full ACKs
        for _ in range(count):
            if offset + 4 > length: break
            self.sequences.append(helpers.bytes_to_uint32(buffer, offset)); offset += 4
        return self
    def __repr__(self):
        return f"<AckPacket Count={len(self.sequences)} Seqs={self.sequences[:5]}... Seq={self.header.sequence}>"
