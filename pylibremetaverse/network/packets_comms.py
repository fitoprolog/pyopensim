import logging
import struct
import time # For timestamp
import dataclasses # For nested blocks

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.enums import ChatType, ChatSourceType, ChatAudibleLevel, InstantMessageDialog, InstantMessageOnline # Added IM enums
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

class ChatFromSimulatorPacket(Packet):
    """Packet received from the simulator containing a chat message."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ChatFromSimulator, header if header else PacketHeader())
        self.from_name: bytes = b'' # Name of the sender (UTF-8 encoded)
        self.source_id: CustomUUID = CustomUUID.ZERO # AgentID or ObjectID of sender
        self.owner_id: CustomUUID = CustomUUID.ZERO # Owner of the source object, if SourceType is OBJECT
        self.source_type: ChatSourceType = ChatSourceType.SYSTEM
        self.chat_type: ChatType = ChatType.NORMAL
        self.audible_level: ChatAudibleLevel = ChatAudibleLevel.FULLY
        self.position: Vector3 = Vector3.ZERO # Position of the chat source
        self.message: bytes = b'' # Chat message (UTF-8 encoded)
        # Extra fields from C# for completeness, might not always be used by client directly
        self.from_group_id: CustomUUID = CustomUUID.ZERO # Group ID if chat is from group

    @property
    def from_name_str(self) -> str:
        return self.from_name.decode('utf-8', errors='replace')

    @property
    def message_str(self) -> str:
        return self.message.decode('utf-8', errors='replace')

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        """Deserializes the packet body."""
        # Minimum length: FromName(1, null) + SourceID(16) + OwnerID(16) + SourceType(1) +
        # ChatType(1) + AudibleLevel(1) + Position(12) + Message(1, null) = ~50 bytes
        # FromName (variable, null-terminated string, max ~60 per some viewers)
        name_end = buffer.find(b'\x00', offset)
        if name_end == -1: raise ValueError("ChatFromSimulator: No null terminator for FromName.")
        self.from_name = buffer[offset:name_end]; offset = name_end + 1

        self.source_id = CustomUUID(buffer, offset); offset += 16
        self.owner_id = CustomUUID(buffer, offset); offset += 16

        try:
            self.source_type = ChatSourceType(buffer[offset]); offset += 1
            self.chat_type = ChatType(buffer[offset]); offset += 1
            # AudibleLevel is signed byte in C#, handle potential negative if Python enum doesn't
            audible_val = struct.unpack_from('b', buffer, offset)[0]; offset += 1
            self.audible_level = ChatAudibleLevel(audible_val)
        except ValueError as e: # Invalid enum value
            logger.warning(f"ChatFromSimulator: Invalid enum value during parsing: {e}. Using defaults.")
            # Defaults are already set in __init__

        self.position = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12

        # Message (variable, two-byte length prefix in some versions, but often null-terminated or to end of packet)
        # C# ChatFromSimulatorPacket reads it as a null-terminated string up to 1023 bytes.
        # If there's a FromGroupID, it's after the message.
        # For simplicity, assume message is the rest of the packet up to a null or fixed limit.
        # This part needs to be robust against different message encodings/lengths.

        # Find where message content actually ends. It might be null-terminated,
        # or followed by FromGroupID (16 bytes) if present.
        # A common pattern is that the message is null-terminated.
        msg_end = -1
        # Max message length can be ~1023. Search within remaining packet length.
        # remaining_len = length - (offset - initial_offset_of_body)
        search_msg_end_limit = offset + min(length - (offset - (self.header.SIZE if hasattr(self.header,'SIZE') else 4) ), 1024)

        # Search for null terminator for the message
        temp_msg_end = buffer.find(b'\x00', offset, search_msg_end_limit)

        # Check if FromGroupID (16 bytes) might exist after message + null
        # This is heuristic. A clearer packet spec or length field for message would be better.
        potential_groupid_offset = (temp_msg_end + 1) if temp_msg_end != -1 else offset
        if length - potential_groupid_offset >= 16: # Enough space for FromGroupID
             # If message was not null terminated but there's space for GroupID, assume msg ends before it.
             if temp_msg_end == -1 : temp_msg_end = potential_groupid_offset
             # (This logic is tricky; if message has no null and GroupID follows, need to define boundary)
             # For now, prioritize null termination. If no null, and GroupID fits, assume message ends there.

        if temp_msg_end != -1:
            self.message = buffer[offset:temp_msg_end]
            offset = temp_msg_end + 1
        else: # No null, take up to a limit or what's left before potential GroupID
            # This part is very heuristic without explicit length field for message
            limit = length - ( (offset - (self.header.SIZE if hasattr(self.header,'SIZE') else 4)) + 16) if (length - (offset - (self.header.SIZE if hasattr(self.header,'SIZE') else 4)) >= 16) else length - (offset-(self.header.SIZE if hasattr(self.header,'SIZE') else 4))
            self.message = buffer[offset : offset + limit]
            offset += limit

        # FromGroupID (optional, check if there's enough space left)
        if offset + 16 <= length: # Check if buffer has enough bytes for FromGroupID
            self.from_group_id = CustomUUID(buffer, offset); offset += 16
        else:
            self.from_group_id = CustomUUID.ZERO # Not present or truncated

        return self

    def to_bytes(self) -> bytes: # Client doesn't send this
        logger.warning("ChatFromSimulatorPacket.to_bytes() not implemented (server sends this).")
        return b''

    def __repr__(self):
        return (f"<ChatFromSimulator From='{self.from_name_str}' Type='{self.chat_type.name}' "
                f"Msg='{self.message_str[:30]}...' Seq={self.header.sequence}>")


# --- ImprovedInstantMessagePacket ---
@dataclasses.dataclass
class IMContainerBlock: # Helper, not a direct packet block but groups some fields
    from_agent_id: CustomUUID = CustomUUID.ZERO

@dataclasses.dataclass
class IMMessageBlock: # Corresponds to MessageBlock in C#
    from_group: bool = False # u8, actually a boolean
    dialog: InstantMessageDialog = InstantMessageDialog.MessageFromAgent # u8
    # from_agent_name: bytes = b'' # Variable, null-terminated string up to 1024 (UTF-8)
    im_session_id: CustomUUID = CustomUUID.ZERO # UUID
    message: bytes = b'' # Variable, null-terminated string up to 1024 (UTF-8)
    offline: InstantMessageOnline = InstantMessageOnline.Online # u8
    parent_estate_id: int = 0 # u32
    position: Vector3 = Vector3.ZERO # Vector3
    region_id: CustomUUID = CustomUUID.ZERO # UUID
    timestamp: int = 0 # u32 (seconds since epoch)
    to_agent_id: CustomUUID = CustomUUID.ZERO # UUID
    binary_bucket: bytes = b'' # Variable, u16 length prefix, max 10240
    # These are part of the MessageBlock in C#
    from_agent_name_bytes: bytes = b'' # Separate from from_agent_name for raw bytes

    @property
    def from_agent_name(self) -> str: return self.from_agent_name_bytes.decode('utf-8', errors='replace')
    @property
    def message_str(self) -> str: return self.message.decode('utf-8', errors='replace')


class ImprovedInstantMessagePacket(Packet):
    """Handles sending and receiving Instant Messages."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ImprovedInstantMessage, header if header else PacketHeader())
        # AgentData block (only FromAgentID for this packet type)
        self.agent_data = IMContainerBlock() # Simplified container for FromAgentID for consistency
        # MessageBlock
        self.message_block = IMMessageBlock()

    def to_bytes(self) -> bytes:
        """Serializes the packet body for sending an IM."""
        data = bytearray()
        # AgentData Block (only FromAgentID)
        data.extend(self.agent_data.from_agent_id.get_bytes()) # 16 bytes

        # MessageBlock
        # FromAgentName (UTF-8, null-terminated)
        from_name_bytes = self.message_block.from_agent_name.encode('utf-8')[:1023] # Max 1023 + null
        data.extend(from_name_bytes); data.append(0)

        data.append(1 if self.message_block.from_group else 0) # FromGroup (u8)
        data.append(self.message_block.dialog.value & 0xFF) # Dialog (u8)
        data.extend(self.message_block.im_session_id.get_bytes()) # IMSessionID (16)

        # Message (UTF-8, null-terminated)
        msg_bytes = self.message_block.message_str.encode('utf-8')[:1023]
        data.extend(msg_bytes); data.append(0)

        data.append(self.message_block.offline.value & 0xFF) # Offline (u8)
        data.extend(helpers.uint32_to_bytes(self.message_block.parent_estate_id)) # ParentEstateID (u32)
        data.extend(struct.pack('<fff', self.message_block.position.X, self.message_block.position.Y, self.message_block.position.Z)) # Position (12)
        data.extend(self.message_block.region_id.get_bytes()) # RegionID (16)
        data.extend(helpers.uint32_to_bytes(self.message_block.timestamp)) # Timestamp (u32)
        data.extend(self.message_block.to_agent_id.get_bytes()) # ToAgentID (16)

        # BinaryBucket (u16 length prefix + data)
        bucket_len = len(self.message_block.binary_bucket)
        if bucket_len > 10240: bucket_len = 10240 # Max length
        data.extend(helpers.uint16_to_bytes(bucket_len)) # Length prefix
        data.extend(self.message_block.binary_bucket[:bucket_len]) # Actual data

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        """Deserializes the packet body for a received IM."""
        initial_offset = offset
        # AgentData Block
        self.agent_data.from_agent_id = CustomUUID(buffer, offset); offset += 16

        # MessageBlock
        # FromAgentName
        name_end = buffer.find(b'\x00', offset)
        if name_end == -1: raise ValueError("IM: No null for FromAgentName")
        self.message_block.from_agent_name_bytes = buffer[offset:name_end]; offset = name_end + 1

        self.message_block.from_group = (buffer[offset] != 0); offset += 1
        try:
            self.message_block.dialog = InstantMessageDialog(buffer[offset]); offset += 1
        except ValueError: self.message_block.dialog = InstantMessageDialog.MessageFromAgent; offset +=1; logger.warning("Invalid IMDialog")

        self.message_block.im_session_id = CustomUUID(buffer, offset); offset += 16

        # Message
        msg_end = buffer.find(b'\x00', offset)
        if msg_end == -1: raise ValueError("IM: No null for Message")
        self.message_block.message = buffer[offset:msg_end]; offset = msg_end + 1

        try:
            self.message_block.offline = InstantMessageOnline(buffer[offset]); offset += 1
        except ValueError: self.message_block.offline = InstantMessageOnline.Unknown; offset +=1; logger.warning("Invalid IMOnline")

        self.message_block.parent_estate_id = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.message_block.position = Vector3(*struct.unpack_from('<fff', buffer, offset)); offset += 12
        self.message_block.region_id = CustomUUID(buffer, offset); offset += 16
        self.message_block.timestamp = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.message_block.to_agent_id = CustomUUID(buffer, offset); offset += 16

        # BinaryBucket
        if offset + 2 <= initial_offset + length:
            bucket_len = helpers.bytes_to_uint16(buffer, offset); offset += 2
            if offset + bucket_len <= initial_offset + length:
                self.message_block.binary_bucket = buffer[offset : offset + bucket_len]
                offset += bucket_len
            else: logger.warning("IM BinaryBucket length exceeds packet bounds.")
        else: logger.warning("IM packet too short for BinaryBucket length.")
        return self

    def __repr__(self):
        return (f"<ImprovedInstantMessagePacket From='{self.message_block.from_agent_name}' To='{self.message_block.to_agent_id}' "
                f"Dialog='{self.message_block.dialog.name}' Msg='{self.message_block.message_str[:20]}...' Seq={self.header.sequence}>")
