# -*- coding: UTF-8 -*-
"""
Group-related network packets.
"""
import struct
import dataclasses
from typing import List, Tuple

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import PacketType
from pylibremetaverse.types.group_defs import GroupPowers # Assuming GroupPowers is in group_defs
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader # Assuming Packet, PacketHeader are in packets_base

logger = logging.getLogger(__name__) # Assuming standard logging setup

@dataclasses.dataclass
class AgentGroupDataUpdateAgentDataBlock: # Matches C# AgentData block
    AgentID: CustomUUID

@dataclasses.dataclass
class AgentGroupDataUpdateGroupDataBlock: # Matches C# GroupData block (repeated)
    GroupID: CustomUUID
    GroupInsigniaID: CustomUUID
    GroupName_bytes: bytes # Variable, null-terminated
    GroupPowers_val: int   # uint64
    MemberTitle_bytes: bytes # Variable, null-terminated
    AcceptNotices: bool    # bool (1 byte)
    ListInProfile: bool    # bool (1 byte) - This might not be in this specific packet,
                           # often it's part of AgentDataUpdate or a separate GroupMemberDetails packet.
                           # For now, including based on subtask, verify against C# if issues.

    # Helper properties for string conversion
    @property
    def group_name_str(self) -> str:
        return helpers.bytes_to_string_till_null(self.GroupName_bytes)

    @property
    def member_title_str(self) -> str:
        return helpers.bytes_to_string_till_null(self.MemberTitle_bytes)

    @property
    def group_powers(self) -> GroupPowers:
        return GroupPowers(self.GroupPowers_val)


class AgentGroupDataUpdatePacket(Packet):
    """
    Sent by the server to provide the client with a list of groups
    the agent is a member of, along with some summary information for each.
    """
    # PACKET_ID = PacketType.AgentGroupDataUpdate # To be assigned in packets_base.py
    # FREQUENCY = PacketFrequency.Low # Typically low
    # FLAGS = PacketFlags.Reliable # Usually reliable

    def __init__(self, header: PacketHeader | None = None):
        # The actual PacketType ID will be set once defined in packets_base.py
        # For now, using a placeholder. Ensure this is updated.
        super().__init__(PacketType.Unhandled, header if header else PacketHeader()) # Placeholder ID
        self.agent_data_block = AgentGroupDataUpdateAgentDataBlock(AgentID=CustomUUID.ZERO)
        self.group_data_blocks: List[AgentGroupDataUpdateGroupDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "AgentGroupDataUpdatePacket":
        initial_offset = offset

        # AgentDataBlock
        self.agent_data_block.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # GroupDataBlocks (Array)
        # The number of GroupData blocks is typically prefixed by a count byte or derived from remaining length.
        # Let's assume a count byte for this example, as it's common for arrays in these protocols.
        # If it's derived, the logic would be different.

        # According to OpenMetaverse.Packets.AgentGroupDataUpdatePacket.cs,
        # it's one AgentData block, then a count for GroupData blocks.
        if offset + 1 > initial_offset + length: # Check if there's space for count byte
            logger.warning("AgentGroupDataUpdatePacket: Not enough data for group count.")
            return self

        group_data_count = buffer[offset]; offset += 1

        self.group_data_blocks = []
        for _ in range(group_data_count):
            # Boundary check for each block
            # Min size: UUID (16) + UUID (16) + Name (1, null term) + Powers (8) + Title (1, null term) + Accept (1) + ListInProfile (1) = ~44 bytes
            # This is a rough estimate, actual parsing will advance offset.
            if offset + 44 > initial_offset + length: # Rough check
                 logger.warning(f"AgentGroupDataUpdatePacket: Potential buffer overrun parsing group block {_ + 1}/{group_data_count}. Offset: {offset}")
                 break

            group_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            insignia_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

            name_bytes, new_offset = helpers.read_null_terminated_bytes(buffer, offset)
            if new_offset == offset: # Should not happen if string is properly terminated
                logger.warning("AgentGroupDataUpdatePacket: Empty or unterminated GroupName.")
                # Decide how to handle: skip block, use empty name, or stop parsing.
                # For now, assume it might mean end of useful data or malformed packet.
                break
            offset = new_offset

            if offset + 8 > initial_offset + length: break # For GroupPowers_val (uint64)
            group_powers_val = helpers.bytes_to_uint64(buffer, offset); offset += 8

            title_bytes, new_offset = helpers.read_null_terminated_bytes(buffer, offset)
            if new_offset == offset and title_bytes: # Allow empty title, but not if read failed
                 logger.warning("AgentGroupDataUpdatePacket: Unterminated MemberTitle.")
                 break
            offset = new_offset

            if offset + 2 > initial_offset + length: break # For AcceptNotices & ListInProfile
            accept_notices = buffer[offset] != 0; offset += 1
            list_in_profile = buffer[offset] != 0; offset += 1 # As per subtask, verify necessity

            self.group_data_blocks.append(
                AgentGroupDataUpdateGroupDataBlock(
                    GroupID=group_id,
                    GroupInsigniaID=insignia_id,
                    GroupName_bytes=name_bytes,
                    GroupPowers_val=group_powers_val,
                    MemberTitle_bytes=title_bytes,
                    AcceptNotices=accept_notices,
                    ListInProfile=list_in_profile
                )
            )

        if offset - initial_offset != length:
            logger.warning(f"AgentGroupDataUpdatePacket: Parsed {offset - initial_offset} bytes, but expected body length was {length}.")
            # This could indicate a parsing error or an unexpected packet structure.

        return self

    def to_bytes(self) -> bytes:
        # This packet is server-to-client, so to_bytes is less critical for a client library.
        # However, implementing it can be useful for testing or simulating a server.
        data = bytearray()
        # AgentDataBlock
        data.extend(self.agent_data_block.AgentID.get_bytes())

        # GroupDataBlock Count
        data.append(len(self.group_data_blocks) & 0xFF) # Assuming count is 1 byte

        for block in self.group_data_blocks:
            data.extend(block.GroupID.get_bytes())
            data.extend(block.GroupInsigniaID.get_bytes())
            data.extend(block.GroupName_bytes); data.append(0) # Null terminator
            data.extend(helpers.uint64_to_bytes(block.GroupPowers_val))
            data.extend(block.MemberTitle_bytes); data.append(0) # Null terminator
            data.append(1 if block.AcceptNotices else 0)
            data.append(1 if block.ListInProfile else 0)

        return bytes(data)

if __name__ == '__main__':
    # Add conceptual tests here if desired
    print("packets_group.py defined with AgentGroupDataUpdatePacket.")
    # Example:
    # test_packet = AgentGroupDataUpdatePacket()
    # test_packet.agent_data_block.AgentID = CustomUUID.random()
    # gb1 = AgentGroupDataUpdateGroupDataBlock(
    #     GroupID=CustomUUID.random(), GroupInsigniaID=CustomUUID.random(),
    #     GroupName_bytes=b"Test Group 1\0", GroupPowers_val=GroupPowers.ALLOW_INVITE.value,
    #     MemberTitle_bytes=b"Officer\0", AcceptNotices=True, ListInProfile=True
    # )
    # test_packet.group_data_blocks.append(gb1)
    # # packet_bytes = test_packet.to_bytes() # Would need header for full test
    # # print(f"Serialized length: {len(packet_bytes)}")
    # # parsed_packet = AgentGroupDataUpdatePacket().from_bytes_body(packet_bytes, 0, len(packet_bytes))
    # # assert len(parsed_packet.group_data_blocks) == 1
    # # assert parsed_packet.group_data_blocks[0].group_name_str == "Test Group 1"
    print("Conceptual test ideas added.")


class AgentSetGroupPacket(Packet):
    """
    Sent by the client to set its active group tag.
    Corresponds to PacketType.AgentSetGroup (109 / 0xFFFFFF6D)
    """
    # PACKET_ID = PacketType.AgentSetGroup # To be assigned
    # FREQUENCY = PacketFrequency.Low
    # FLAGS = PacketFlags.Reliable

    # Direct fields as per C# OpenMetaverse.Packets.AgentSetGroupPacket
    agent_id: CustomUUID
    session_id: CustomUUID
    group_id: CustomUUID

    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, group_id: CustomUUID,
                 header: PacketHeader | None = None):
        # The actual PacketType ID will be set once defined in packets_base.py
        # For now, using a placeholder. Ensure this is updated.
        super().__init__(PacketType.Unhandled, header if header else PacketHeader()) # Placeholder ID
        self.agent_id = agent_id
        self.session_id = session_id
        self.group_id = group_id
        self.header.reliable = True # This packet should be reliable

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.agent_id.get_bytes())
        data.extend(self.session_id.get_bytes())
        data.extend(self.group_id.get_bytes())
        return bytes(data)

    @classmethod
    def from_bytes_body(cls, buffer: bytes, offset: int, length: int) -> "AgentSetGroupPacket":
        # This packet is client-to-server, so from_bytes_body is less critical for client.
        # Implemented for completeness or potential testing.
        if length < 48: # 3 UUIDs
            raise ValueError("Buffer too small for AgentSetGroupPacket body.")

        agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        session_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        group_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        return cls(agent_id=agent_id, session_id=session_id, group_id=group_id)
