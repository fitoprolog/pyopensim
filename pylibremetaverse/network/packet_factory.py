import logging

from .packets_base import Packet, PacketHeader, PacketType
from .packets_control import RegionHandshakePacket, AckPacket
from .packets_agent import (
    AgentDataUpdatePacket, AgentMovementCompletePacket, AvatarAnimationPacket, AvatarSitResponsePacket,
    MuteListUpdatePacket
)
from .packets_appearance import AgentWearablesUpdatePacket, AvatarAppearancePacket
from .packets_comms import ChatFromSimulatorPacket, ImprovedInstantMessagePacket
from .packets_teleport import (
    TeleportStartPacket, TeleportProgressPacket, TeleportFailedPacket,
    TeleportCancelPacket, TeleportFinishPacket, TeleportLocalPacket
)
from .packets_script import ScriptDialogPacket, ScriptQuestionPacket
from .packets_object import (
    ObjectUpdatePacket, ObjectUpdateCachedPacket, ImprovedTerseObjectUpdatePacket,
    KillObjectPacket, ObjectPropertiesFamilyPacket, ObjectPropertiesPacket
)
from .packets_asset import (
    TransferInfoPacket, TransferPacket, SendXferPacket,
    ImageDataPacket, ImageNotInDatabasePacket, AssetUploadCompletePacket
)
from .packets_friends import ( # Added for new friend status packets
    OnlineNotificationPacket, OfflineNotificationPacket, AgentOnlineStatusPacket
)


logger = logging.getLogger(__name__)

def from_bytes(payload_with_type_markers: bytes, header: PacketHeader) -> Packet | None:
    packet_class = None
    body_payload = b''
    packet_enum_type_for_logging = PacketType.Unhandled

    if not payload_with_type_markers:
        logger.warning(f"Empty payload received for packet factory. Seq={header.sequence}")
        return None

    # Low Frequency Packets (Start with 0xFFFFFF)
    if len(payload_with_type_markers) >= 4 and \
       payload_with_type_markers[0] == 0xFF and \
       payload_with_type_markers[1] == 0xFF and \
       payload_with_type_markers[2] == 0xFF:

        type_byte = payload_with_type_markers[3]

        if type_byte == 0x04: packet_class=RegionHandshakePacket; packet_enum_type_for_logging=PacketType.RegionHandshake
        elif type_byte == 0xF4: packet_class=AckPacket; packet_enum_type_for_logging=PacketType.PacketAck
        elif type_byte == 0x4A: packet_class=AgentDataUpdatePacket; packet_enum_type_for_logging=PacketType.AgentDataUpdate
        elif type_byte == 0x08: packet_class=AgentMovementCompletePacket; packet_enum_type_for_logging=PacketType.AgentMovementComplete
        elif type_byte == 0x3B: packet_class=AvatarAnimationPacket; packet_enum_type_for_logging=PacketType.AvatarAnimation
        elif type_byte == 0x2C: packet_class=ChatFromSimulatorPacket; packet_enum_type_for_logging=PacketType.ChatFromSimulator
        elif type_byte == 0x36: packet_class=ImprovedInstantMessagePacket; packet_enum_type_for_logging=PacketType.ImprovedInstantMessage
        elif type_byte == 0x19: packet_class=TeleportStartPacket; packet_enum_type_for_logging=PacketType.TeleportStart
        elif type_byte == 0x1A: packet_class=TeleportProgressPacket; packet_enum_type_for_logging=PacketType.TeleportProgress
        elif type_byte == 0x1B: packet_class=TeleportFailedPacket; packet_enum_type_for_logging=PacketType.TeleportFailed
        elif type_byte == 0x3A: packet_class=TeleportCancelPacket; packet_enum_type_for_logging=PacketType.TeleportCancel
        elif type_byte == 0x0E: packet_class=TeleportFinishPacket; packet_enum_type_for_logging=PacketType.TeleportFinish
        elif type_byte == 0x0F: packet_class=TeleportLocalPacket; packet_enum_type_for_logging=PacketType.TeleportLocal
        elif type_byte == 0x39: packet_class=AvatarSitResponsePacket; packet_enum_type_for_logging=PacketType.AvatarSitResponse
        elif type_byte == 0x4C: packet_class=ScriptDialogPacket; packet_enum_type_for_logging=PacketType.ScriptDialog
        elif type_byte == 0x51: packet_class=ScriptQuestionPacket; packet_enum_type_for_logging=PacketType.ScriptQuestion
        elif type_byte == 0x17: packet_class=MuteListUpdatePacket; packet_enum_type_for_logging=PacketType.MuteListUpdate
        elif type_byte == 0x06: packet_class=ObjectUpdateCachedPacket; packet_enum_type_for_logging=PacketType.ObjectUpdateCached
        elif type_byte == 0x0B: packet_class=KillObjectPacket; packet_enum_type_for_logging=PacketType.KillObject
        elif type_byte == 0x3F: packet_class=ObjectPropertiesFamilyPacket; packet_enum_type_for_logging=PacketType.ObjectPropertiesFamily
        elif type_byte == 0x5A: packet_class=ObjectPropertiesPacket; packet_enum_type_for_logging=PacketType.ObjectProperties
        elif type_byte == 0x23: packet_class=TransferInfoPacket; packet_enum_type_for_logging=PacketType.TransferInfo
        elif type_byte == 0x22: packet_class=TransferPacket; packet_enum_type_for_logging=PacketType.TransferPacket
        elif type_byte == 0x25: packet_class=SendXferPacket; packet_enum_type_for_logging=PacketType.SendXferPacket
        elif type_byte == 0x1B: packet_class=ImageNotInDatabasePacket; packet_enum_type_for_logging=PacketType.ImageNotInDatabase
        elif type_byte == 0x28: packet_class=AssetUploadCompletePacket; packet_enum_type_for_logging=PacketType.AssetUploadComplete
        elif type_byte == 0x29: # Value 41 (0x29) - Server to Client is UpdateInventoryItemPacket
            from pylibremetaverse.network.packets_inventory import UpdateInventoryItemPacket
            packet_class=UpdateInventoryItemPacket; packet_enum_type_for_logging=PacketType.UpdateInventoryItem
        # Friend Online Status Packets
        elif type_byte == 0x72: packet_class=OnlineNotificationPacket; packet_enum_type_for_logging=PacketType.OnlineNotification
        elif type_byte == 0x73: packet_class=OfflineNotificationPacket; packet_enum_type_for_logging=PacketType.OfflineNotification
        elif type_byte == 0x75: packet_class=AgentOnlineStatusPacket; packet_enum_type_for_logging=PacketType.AgentOnlineStatus
        # Asset Xfer packets (Server -> Client for uploads)
        elif type_byte == 0x24: # RequestXfer can be sent by server to initiate upload
            from pylibremetaverse.network.packets_asset import RequestXferPacket as ServerRequestXferPacket
            packet_class=ServerRequestXferPacket; packet_enum_type_for_logging=PacketType.RequestXfer
        elif type_byte == 0x26: # ConfirmXferPacket can be sent by server to confirm upload chunk
            from pylibremetaverse.network.packets_asset import ConfirmXferPacket as ServerConfirmXferPacket
            packet_class=ServerConfirmXferPacket; packet_enum_type_for_logging=PacketType.ConfirmXferPacket
        else: logger.debug(f"Unknown Low Freq packet type: 0xFFFFFF{type_byte:02X}. Seq={header.sequence}")
        if packet_class: body_payload = payload_with_type_markers[4:]

    # Medium Frequency Packets (0xFFFFFECE for AgentWearablesUpdate, 0xFFFFFECC for AvatarAppearance)
    elif len(payload_with_type_markers) >= 4 and \
         payload_with_type_markers[0] == 0xFF and \
         payload_with_type_markers[1] == 0xFF and \
         payload_with_type_markers[2] == 0xFE:
        type_byte_med = payload_with_type_markers[3]
        if type_byte_med == 0xCE: packet_class=AgentWearablesUpdatePacket;packet_enum_type_for_logging=PacketType.AgentWearablesUpdate
        elif type_byte_med == 0xCC: packet_class=AvatarAppearancePacket;packet_enum_type_for_logging=PacketType.AvatarAppearance
        else: logger.debug(f"Unknown Med-Low Freq packet type (0xFFFFFE XX): 0xFFFFFE{type_byte_med:02X}. Seq={header.sequence}")
        if packet_class: body_payload = payload_with_type_markers[4:]

    # High Frequency Packets (Type is the first byte)
    elif len(payload_with_type_markers) >= 1:
        type_byte_high = payload_with_type_markers[0]
        if type_byte_high == 0x05: packet_class=ObjectUpdatePacket;packet_enum_type_for_logging=PacketType.ObjectUpdate;body_payload=payload_with_type_markers[1:]
        elif type_byte_high == 0x07: packet_class=ImprovedTerseObjectUpdatePacket;packet_enum_type_for_logging=PacketType.ImprovedTerseObjectUpdate;body_payload=payload_with_type_markers[1:]
        elif type_byte_high == 0x1A: packet_class=ImageDataPacket;packet_enum_type_for_logging=PacketType.ImageData;body_payload=payload_with_type_markers[1:] # Value 26 (0x1A)
        else: logger.debug(f"Unknown High Freq packet type: 0x{type_byte_high:02X}. Seq={header.sequence}")

    if not packet_class:
        logger.debug(f"Unrecognized packet type or unhandled prefix. Seq={header.sequence}. Payload start: {payload_with_type_markers[:8].hex()}")
        return None

    try:
        packet_instance = packet_class(header=header)
        packet_instance.from_bytes_body(body_payload, 0, len(body_payload))
        logger.debug(f"Deserialized packet: {packet_instance.type.name} (Seq={header.sequence})")
        return packet_instance
    except ValueError as ve: logger.error(f"ValueError deserializing {packet_enum_type_for_logging.name} (Seq={header.sequence}): {ve}. Payload: {body_payload.hex()[:100]}")
    except Exception as e: logger.exception(f"Failed to deserialize {packet_enum_type_for_logging.name} (Seq={header.sequence}): {e}. Payload: {body_payload.hex()[:100]}")
    return None
