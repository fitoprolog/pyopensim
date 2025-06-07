import logging
import struct
import dataclasses

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import ScriptPermission # For ScriptQuestionPacket
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

# --- ScriptDialogPacket (Server -> Client) ---
class ScriptDialogPacket(Packet):
    """Received from server, presents a dialog from a script to the user."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ScriptDialog, header if header else PacketHeader())
        self.object_id: CustomUUID = CustomUUID.ZERO
        self.object_name: bytes = b''
        self.image_id: CustomUUID = CustomUUID.ZERO
        self.chat_channel: int = 0 # s32
        self.first_name: bytes = b'' # Owner's first name
        self.last_name: bytes = b''  # Owner's last name
        self.message: bytes = b''    # Dialog message
        self.button_labels: list[bytes] = [] # Array of button labels

    @property
    def object_name_str(self) -> str: return self.object_name.decode('utf-8', errors='replace')
    @property
    def first_name_str(self) -> str: return self.first_name.decode('utf-8', errors='replace')
    @property
    def last_name_str(self) -> str: return self.last_name.decode('utf-8', errors='replace')
    @property
    def message_str(self) -> str: return self.message.decode('utf-8', errors='replace')
    @property
    def button_labels_str(self) -> list[str]: return [b.decode('utf-8', errors='replace') for b in self.button_labels]

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        initial_offset = offset
        # ObjectData block
        self.object_id = CustomUUID(buffer, offset); offset += 16
        self.object_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.object_name) + 1
        self.image_id = CustomUUID(buffer, offset); offset += 16
        self.chat_channel = helpers.bytes_to_int32(buffer, offset); offset += 4

        # Data block
        self.first_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.first_name) + 1
        self.last_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.last_name) + 1
        self.message = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.message) + 1

        # ButtonLabel array
        if offset < initial_offset + length:
            num_buttons = buffer[offset]; offset += 1
            for _ in range(num_buttons):
                if offset >= initial_offset + length: break # Bounds check
                label = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8')
                self.button_labels.append(label)
                offset += len(label) + 1
        return self

    def to_bytes(self) -> bytes: # Client doesn't send this
        logger.warning("ScriptDialogPacket.to_bytes() not implemented (server sends this).")
        return b''

# --- ScriptDialogReplyPacket (Client -> Server) ---
class ScriptDialogReplyPacket(Packet):
    """Client sends this in response to a ScriptDialogPacket."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 object_id: CustomUUID, chat_channel: int,
                 button_index: int, button_label: str,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ScriptDialogReply, header if header else PacketHeader())
        self.agent_id = agent_id
        self.session_id = session_id
        self.object_id = object_id
        self.chat_channel = chat_channel # s32
        self.button_index = button_index # s32
        self.button_label_bytes = button_label.encode('utf-8') # Variable, null-terminated
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes())
        # Data
        data.extend(self.object_id.get_bytes())
        data.extend(helpers.int32_to_bytes(self.chat_channel))
        data.extend(helpers.int32_to_bytes(self.button_index))

        label_bytes = self.button_label_bytes
        if len(label_bytes) > 254: label_bytes = label_bytes[:254] # Max length for button label
        data.extend(label_bytes)
        data.append(0) # Null terminator
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("ScriptDialogReplyPacket.from_bytes_body should not be called on client.")
        return self


# --- ScriptQuestionPacket (Server -> Client) ---
# This packet requests permissions from the agent.
class ScriptQuestionPacket(Packet):
    """Received from server when a script requests permissions."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ScriptQuestion, header if header else PacketHeader())
        self.task_id: CustomUUID = CustomUUID.ZERO # Local ID of the prim containing the script
        self.item_id: CustomUUID = CustomUUID.ZERO # Item ID of the script
        self.object_name: bytes = b''
        self.object_owner_first_name: bytes = b'' # From C# these are separate fields, not one "owner name"
        self.object_owner_last_name: bytes = b''
        self.questions: ScriptPermission = ScriptPermission.NONE # u32 bitfield

    @property
    def object_name_str(self) -> str: return self.object_name.decode('utf-8', errors='replace')
    @property
    def object_owner_name_str(self) -> str: # Combine for convenience
        first = self.object_owner_first_name.decode('utf-8', errors='replace')
        last = self.object_owner_last_name.decode('utf-8', errors='replace')
        return f"{first} {last}".strip()


    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # TaskID(16) + ItemID(16) + ObjectName(var) + ObjectOwnerFirstName(var) + ObjectOwnerLastName(var) + Questions(4)
        min_len = 16 + 16 + 1+1+1+ 4 # Min for strings (1 byte each for null term)
        if length < min_len: raise ValueError(f"ScriptQuestionPacket body too short: {length}")

        self.task_id = CustomUUID(buffer, offset); offset += 16
        self.item_id = CustomUUID(buffer, offset); offset += 16

        self.object_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.object_name) + 1
        # In C#, ObjectOwner is a single string field. Here, split for consistency if other packets do.
        # However, packet definition in C# for ScriptQuestion seems to just have one ObjectName.
        # Let's assume ObjectName is prim name, and ObjectOwnerName is separate.
        # The C# packet has: TaskID, ItemID, ObjectName (string), ObjectOwnerID (UUID), Questions (int)
        # The prompt text implies ObjectOwnerName (string). This needs clarification against a C# definition.
        # For now, using prompt's fields: ObjectName, ObjectOwnerName (split into first/last)
        # This part is speculative based on prompt vs common packet structures.
        # If ObjectOwner is an ID, then names would be looked up.
        # Assuming names are sent directly for now:
        self.object_owner_first_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.object_owner_first_name) + 1
        self.object_owner_last_name = helpers.bytes_to_string(buffer, offset, 0).encode('utf-8'); offset += len(self.object_owner_last_name) + 1

        self.questions = ScriptPermission(helpers.bytes_to_uint32(buffer, offset)); offset += 4
        return self

    def to_bytes(self) -> bytes: # Client doesn't send this
        logger.warning("ScriptQuestionPacket.to_bytes() not implemented (server sends this).")
        return b''

# ScriptAnswerYesPacket: As discussed, this is typically an ImprovedInstantMessagePacket.
# The AgentManager will construct and send an IM with dialog InstantMessageDialog.PermissionNotify
# or similar, and the message body will contain the TaskID, ItemID, and granted permissions.
# No unique packet class needed here if following that pattern.
# The prompt asked for ScriptAnswerYesPacket. If it is a unique packet:
# C# does NOT have a ScriptAnswerYesPacket. It uses an IM.
# If forced to create one, its structure would be:
# AgentData (AgentID, SessionID)
# Data (TaskID, ItemID, QuestionsGranted (u32))
# For now, this will be omitted as it's not standard. AgentManager will use IMs.
# If a different mechanism is confirmed, this can be added.
# The prompt implies this packet is Client -> Server.

# For now, assuming ScriptAnswerYesPacket is NOT a distinct packet type,
# and AgentManager.respond_to_script_permission_request will use IMs.
# If it IS a distinct packet (e.g. ID 0xFFFFFF52), it would be:
# class ScriptAnswerYesPacket(Packet):
#    def __init__(self, agent_id, session_id, task_id, item_id, questions_granted: ScriptPermission, header=None):
#        super().__init__(PacketType.ScriptAnswerYes, header) # Needs ScriptAnswerYes in PacketType
#        # ... store fields ...
#    def to_bytes(self): # ... serialize ...
#        pass
# For this subtask, I will NOT implement ScriptAnswerYesPacket as a unique type.
# AgentManager.respond_to_script_permission_request will be implemented to send an IM.
# The prompt seems to imply it's a unique packet, but this contradicts common SL protocol patterns.
# I will create it as requested by the prompt, assuming it's a specific low-freq packet.
# Let's assume its PacketType would be ScriptAnswer (conceptual, needs ID).
# For now, let's assign a placeholder ID for ScriptAnswerYes in PacketType enum later if needed.
# Given the prompt, I *will* define ScriptAnswerYesPacket.
# It will need a PacketType. Placeholder: ScriptAnswer = 82 (0xFFFFFF52)

class ScriptAnswerYesPacket(Packet):
    """Client sends this to grant permissions requested by a script."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 task_id: CustomUUID, item_id: CustomUUID, questions_granted: ScriptPermission,
                 header: PacketHeader | None = None):
        # Assuming a conceptual PacketType.ScriptAnswerYes exists or will be added
        super().__init__(PacketType.Unhandled, header if header else PacketHeader()) # Replace Unhandled later
        self.agent_id = agent_id
        self.session_id = session_id
        self.task_id = task_id # TaskID from ScriptQuestion
        self.item_id = item_id # ItemID from ScriptQuestion
        self.questions = questions_granted.value # u32, the permissions being granted
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes())
        # Data
        data.extend(self.task_id.get_bytes())
        data.extend(self.item_id.get_bytes())
        data.extend(helpers.uint32_to_bytes(self.questions))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int): # Server doesn't send this
        logger.warning("ScriptAnswerYesPacket.from_bytes_body should not be called on client.")
        return self
