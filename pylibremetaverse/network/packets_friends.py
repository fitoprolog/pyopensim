import dataclasses
import logging

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

# --- AgentDataBlock (Common for many friend packets) ---
@dataclasses.dataclass
class FriendPacketAgentDataBlock:
    AgentID: CustomUUID
    SessionID: CustomUUID

# --- OfferFriendshipPacket (Client -> Server) ---
@dataclasses.dataclass
class OfferFriendshipOffereeBlock:
    OffereeID: CustomUUID # UUID of the agent being offered friendship

@dataclasses.dataclass
class OfferFriendshipMessageBlock:
    Message: bytes # UTF-8 encoded, null-terminated IM message (max 1023 bytes + null)

class OfferFriendshipPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 target_uuid: CustomUUID, message: str,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.OfferFriendship, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.offeree_block = OfferFriendshipOffereeBlock(OffereeID=target_uuid)

        msg_bytes = message.encode('utf-8')
        if len(msg_bytes) > 1023: msg_bytes = msg_bytes[:1023]
        self.message_block = OfferFriendshipMessageBlock(Message=msg_bytes + b'\0')

        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # OffereeBlock
        data.extend(self.offeree_block.OffereeID.get_bytes())
        # MessageBlock
        data.extend(self.message_block.Message) # Already null-terminated
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive OfferFriendshipPacket.")
        return self

# --- AcceptFriendshipPacket (Client -> Server) ---
@dataclasses.dataclass
class AcceptFriendshipTransactionBlock:
    TransactionID: CustomUUID # This is the IM Session ID from the friendship offer

@dataclasses.dataclass
class AcceptFriendshipFolderDataBlock: # Array of these, but typically one (agent's inv root)
    FolderID: CustomUUID

class AcceptFriendshipPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 transaction_id: CustomUUID, my_inventory_root: CustomUUID,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.AcceptFriendship, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.transaction_block = AcceptFriendshipTransactionBlock(TransactionID=transaction_id)
        # Typically, one folder is sent: the agent's inventory root folder where the friend's calling card will be placed.
        self.folder_data_blocks: list[AcceptFriendshipFolderDataBlock] = \
            [AcceptFriendshipFolderDataBlock(FolderID=my_inventory_root)]
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # TransactionBlock
        data.extend(self.transaction_block.TransactionID.get_bytes())
        # FolderData Blocks
        data.append(len(self.folder_data_blocks) & 0xFF) # Count byte (usually 1)
        for block in self.folder_data_blocks:
            data.extend(block.FolderID.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive AcceptFriendshipPacket.")
        return self

# --- DeclineFriendshipPacket (Client -> Server) ---
# Note: C# LibreMetaverse sends an IM for declining friendship (dialog=FriendshipDeclined).
# This packet definition is provided for completeness or if direct packet use is preferred.
@dataclasses.dataclass
class DeclineFriendshipTransactionBlock: # Same as AcceptFriendship's
    TransactionID: CustomUUID

class DeclineFriendshipPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 transaction_id: CustomUUID,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.DeclineFriendship, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.transaction_block = DeclineFriendshipTransactionBlock(TransactionID=transaction_id)
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # TransactionBlock
        data.extend(self.transaction_block.TransactionID.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive DeclineFriendshipPacket.")
        return self


# --- OnlineNotificationPacket (Server -> Client) ---
# This packet informs us that friends have come online and includes their rights.
@dataclasses.dataclass
class OnlineNotificationAgentBlock: # Renamed from OnlineNotificationPacketDataBlock for clarity
    AgentID: CustomUUID

@dataclasses.dataclass
class BuddyRightsBlock: # New dataclass for rights information
    AgentID: CustomUUID  # The friend's AgentID
    Rights: int          # The rights bitmask (FriendRights value)

class OnlineNotificationPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.OnlineNotification, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO) # Our own AgentID/SessionID
        self.agent_block_array: list[OnlineNotificationAgentBlock] = [] # Friends who came online
        self.buddy_rights_online_array: list[BuddyRightsBlock] = [] # Rights they have granted to us
        self.buddy_rights_friend_array: list[BuddyRightsBlock] = [] # Rights we have granted to them

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "OnlineNotificationPacket":
        initial_offset = offset

        # AgentData (Our own ID/Session)
        self.agent_data.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.SessionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        # AgentBlock array (friends who came online)
        num_agent_blocks = buffer[offset]; offset += 1
        for _ in range(num_agent_blocks):
            agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            self.agent_block_array.append(OnlineNotificationAgentBlock(AgentID=agent_id))

        # BuddyRightsOnline array (Rights they grant us)
        num_buddy_online_blocks = buffer[offset]; offset += 1
        for _ in range(num_buddy_online_blocks):
            agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            rights = helpers.bytes_to_int32(buffer, offset); offset += 4 # Rights are int32
            self.buddy_rights_online_array.append(BuddyRightsBlock(AgentID=agent_id, Rights=rights))

        # BuddyRightsFriend array (Rights we grant them)
        num_buddy_friend_blocks = buffer[offset]; offset += 1
        for _ in range(num_buddy_friend_blocks):
            agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            rights = helpers.bytes_to_int32(buffer, offset); offset += 4 # Rights are int32
            self.buddy_rights_friend_array.append(BuddyRightsBlock(AgentID=agent_id, Rights=rights))

        if offset - initial_offset != length:
            logger.warning(f"OnlineNotificationPacket: Expected to read {length} bytes, but read {offset - initial_offset}")
        return self

    def to_bytes(self) -> bytes: # Server -> Client, client does not send this
        logger.error("Client does not send OnlineNotificationPacket.")
        return b''

# --- OfflineNotificationPacket (Server -> Client) ---
# This packet only informs which friends went offline, no rights info.
@dataclasses.dataclass
class OfflineNotificationAgentBlock: # Renamed for clarity
    AgentID: CustomUUID

class OfflineNotificationPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.OfflineNotification, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO)
        self.agent_block_array: list[OfflineNotificationAgentBlock] = [] # Friends who went offline

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "OfflineNotificationPacket":
        initial_offset = offset
        self.agent_data.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.SessionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        num_blocks = buffer[offset]; offset += 1
        for _ in range(num_blocks):
            agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            self.agent_block_array.append(OfflineNotificationAgentBlock(AgentID=agent_id))

        if offset - initial_offset != length:
            logger.warning(f"OfflineNotificationPacket: Expected to read {length} bytes, but read {offset - initial_offset}")
        return self

    def to_bytes(self) -> bytes: # Server -> Client, client does not send this
        logger.error("Client does not send OfflineNotificationPacket.")
        return b''

# --- FindAgentPacket (Client -> Server) ---
# Note: C# client sends multiple FindAgentPackets if the list of PreyIDs is large,
# typically one PreyID per packet. The packet structure itself supports an array.
@dataclasses.dataclass
class FindAgentPacketDataBlock:
    HunterID: CustomUUID # Our AgentID
    PreyID: CustomUUID   # Friend's UUID whose status we are querying

class FindAgentPacket(Packet):
    def __init__(self, agent_id: CustomUUID, target_agent_uuids: list[CustomUUID],
                 header: PacketHeader | None = None):
        super().__init__(PacketType.FindAgent, header if header else PacketHeader())
        # AgentData block is not explicitly part of FindAgent in C# structure, SessionID is though.
        # The packet itself is simple: an array of HunterID/PreyID blocks.
        # However, packets usually require AgentID/SessionID for routing by server.
        # For now, let's assume it's not needed as a top-level block in this specific packet's payload,
        # and SessionID is part of the overall UDP message context or implied.
        # If it is needed, the structure would be:
        # self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id_if_needed)

        self.agent_block_array: list[FindAgentPacketDataBlock] = []
        for target_id in target_agent_uuids:
            self.agent_block_array.append(FindAgentPacketDataBlock(HunterID=agent_id, PreyID=target_id))

        self.header.reliable = True # Typically reliable

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData block (if it were needed here)
        # data.extend(self.agent_data.AgentID.get_bytes())
        # data.extend(self.agent_data.SessionID.get_bytes())

        data.append(len(self.agent_block_array) & 0xFF) # Count byte
        for block in self.agent_block_array:
            data.extend(block.HunterID.get_bytes())
            data.extend(block.PreyID.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive FindAgentPacket (it's a request).")
        return self


# --- AgentOnlineStatusPacket (Server -> Client) ---
@dataclasses.dataclass
class AgentOnlineStatusDataBlock:
    AgentID: CustomUUID
    Online: bool
    Timestamp: int # uint32, Unix timestamp of last status change

class AgentOnlineStatusPacket(Packet):
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.AgentOnlineStatus, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=CustomUUID.ZERO, SessionID=CustomUUID.ZERO)
        self.agent_block_array: list[AgentOnlineStatusDataBlock] = []

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "AgentOnlineStatusPacket":
        initial_offset = offset
        self.agent_data.AgentID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.agent_data.SessionID = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16

        num_blocks = buffer[offset]; offset += 1
        for _ in range(num_blocks):
            agent_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
            online_status = buffer[offset] != 0; offset += 1
            timestamp = helpers.bytes_to_uint32(buffer, offset); offset += 4 # Assuming little-endian from SL
            self.agent_block_array.append(AgentOnlineStatusDataBlock(
                AgentID=agent_id, Online=online_status, Timestamp=timestamp
            ))

        if offset - initial_offset != length:
            logger.warning(f"AgentOnlineStatusPacket: Expected to read {length} bytes, but read {offset - initial_offset}")
        return self

    def to_bytes(self) -> bytes: # Server -> Client, client does not send this
        logger.error("Client does not send AgentOnlineStatusPacket.")
        return b''

# --- ChangeUserRightsPacket (Client -> Server) ---
@dataclasses.dataclass
class ChangeUserRightsBlock:
    AgentRelated: CustomUUID # Friend's ID whose rights we are changing
    RelatedRights: int     # New FriendRights bitmask we grant them (int32)

class ChangeUserRightsPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 friend_uuid: CustomUUID, new_rights: int, # new_rights is FriendRights.value
                 header: PacketHeader | None = None):
        super().__init__(PacketType.ChangeUserRights, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        # This packet sends an array of RightsBlocks, but typically client sends for one friend at a time.
        self.rights_blocks: list[ChangeUserRightsBlock] = \
            [ChangeUserRightsBlock(AgentRelated=friend_uuid, RelatedRights=new_rights)]
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # RightsBlocks
        data.append(len(self.rights_blocks) & 0xFF) # Count byte (usually 1)
        for block in self.rights_blocks:
            data.extend(block.AgentRelated.get_bytes())
            data.extend(helpers.int32_to_bytes(block.RelatedRights)) # Rights are int32
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive ChangeUserRightsPacket.")
        return self

# --- TerminateFriendshipPacket (Client -> Server) ---
@dataclasses.dataclass
class TerminateFriendshipOtherDataBlock:
    OtherID: CustomUUID # Friend's ID to remove

class TerminateFriendshipPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 friend_to_remove_uuid: CustomUUID,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.TerminateFriendship, header if header else PacketHeader())
        self.agent_data = FriendPacketAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.other_data_block = TerminateFriendshipOtherDataBlock(OtherID=friend_to_remove_uuid)
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())
        # OtherDataBlock
        data.extend(self.other_data_block.OtherID.get_bytes())
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive TerminateFriendshipPacket.")
        return self
