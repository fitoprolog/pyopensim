# This file marks pylibremetaverse.network as a Python package.

from .http_caps_client import HttpCapsClient
from .login_defs import (
    LoginStatus, LastExecStatus, LoginCredential, LoginParams,
    BuddyListEntry, HomeInfo, LoginResponseData
)
from .simulator import Simulator
from .packet_protocol import PacketProtocol, IncomingPacket
from .packets_base import Packet, PacketHeader, PacketType, PacketFlags
from .packets_control import (
    UseCircuitCodePacket, RegionHandshakePacket, RegionHandshakeReplyPacket,
    CompleteAgentMovementPacket, AgentThrottlePacket, EconomyDataRequestPacket,
    LogoutRequestPacket, CloseCircuitPacket, AckPacket
)
from .packets_agent import (
    AgentUpdatePacket, SetAlwaysRunPacket, AgentDataUpdatePacket,
    AgentMovementCompletePacket, AvatarAnimationPacket, ChatFromViewerPacket,
    AgentRequestSitPacket, AgentSitPacket, AvatarSitResponsePacket, AgentAnimationPacket,
    ActivateGesturesPacket, DeactivateGesturesPacket, MuteListRequestPacket,
    MuteListUpdatePacket, UpdateMuteListEntryPacket, RemoveMuteListEntryPacket
)
from .packets_appearance import (
    AgentWearablesRequestPacket, AgentWearablesUpdatePacket,
    AgentSetAppearancePacket, AvatarAppearancePacket, AgentIsNowWearingPacket # Added
)
from .packets_comms import ChatFromSimulatorPacket, ImprovedInstantMessagePacket
from .packets_teleport import (
    TeleportLandmarkRequestPacket, TeleportLocationRequestPacket, TeleportCancelPacket,
    TeleportStartPacket, TeleportProgressPacket, TeleportFailedPacket,
    TeleportFinishPacket, TeleportLocalPacket,
    StartLurePacket, TeleportLureRequestPacket
)
from .packets_script import (
    ScriptDialogPacket, ScriptDialogReplyPacket, ScriptQuestionPacket, ScriptAnswerYesPacket
)
from .packets_object import (
    ObjectUpdatePacket, RequestMultipleObjectsPacket, ObjectUpdateCachedPacket,
    ImprovedTerseObjectUpdatePacket, KillObjectPacket,
    RequestObjectPropertiesFamilyPacket, ObjectPropertiesFamilyPacket, ObjectPropertiesPacket,
    ObjectMovePacket, ObjectScalePacket, ObjectRotationPacket,
    ObjectNamePacket, ObjectDescriptionPacket, ObjectTextPacket, ObjectClickActionPacket,
    ObjectAddPacket, ObjectGrabPacket, ObjectDeGrabPacket # Added Grab/DeGrab
)
from .packets_asset import (
    RequestXferPacket, SendXferPacket, ConfirmXferPacket,
    TransferInfoPacket, TransferPacket,
    RequestImagePacket, ImageDataPacket, ImageNotInDatabasePacket,
    AssetUploadRequestPacket, AssetUploadCompletePacket
)
from .packets_inventory import (
    UpdateCreateInventoryItemPacket, UpdateInventoryItemPacket # Added server-side packet
)
from .packets_friends import (
    OfferFriendshipPacket, AcceptFriendshipPacket, DeclineFriendshipPacket,
    OnlineNotificationPacket, OfflineNotificationPacket, FindAgentPacket, AgentOnlineStatusPacket,
    ChangeUserRightsPacket, TerminateFriendshipPacket
)
from .packets_parcel import ( # Added Parcel packets
    ParcelPropertiesRequestPacket, ParcelPropertiesPacket,
    ParcelAccessListRequestPacket, ParcelAccessListReplyPacket # Added ACL packets
)
from .packets_group import ( # Added Group packets
    AgentGroupDataUpdatePacket, AgentSetGroupPacket # Added AgentSetGroupPacket
)

__all__ = [
    "HttpCapsClient", "LoginStatus", "LastExecStatus", "LoginCredential", "LoginParams",
    "BuddyListEntry", "HomeInfo", "LoginResponseData", "Simulator", "PacketProtocol",
    "IncomingPacket", "Packet", "PacketHeader", "PacketType", "PacketFlags",
    "UseCircuitCodePacket", "RegionHandshakePacket", "RegionHandshakeReplyPacket",
    "CompleteAgentMovementPacket", "AgentThrottlePacket", "EconomyDataRequestPacket",
    "LogoutRequestPacket", "CloseCircuitPacket", "AckPacket",
    "AgentUpdatePacket", "SetAlwaysRunPacket", "AgentDataUpdatePacket",
    "AgentMovementCompletePacket", "AvatarAnimationPacket", "ChatFromViewerPacket",
    "AgentRequestSitPacket", "AgentSitPacket", "AvatarSitResponsePacket", "AgentAnimationPacket",
    "ActivateGesturesPacket", "DeactivateGesturesPacket", "MuteListRequestPacket",
    "MuteListUpdatePacket", "UpdateMuteListEntryPacket", "RemoveMuteListEntryPacket",
    "AgentWearablesRequestPacket", "AgentWearablesUpdatePacket", "AgentSetAppearancePacket",
    "AvatarAppearancePacket", "ChatFromSimulatorPacket", "ImprovedInstantMessagePacket",
    "TeleportLandmarkRequestPacket", "TeleportLocationRequestPacket", "TeleportCancelPacket",
    "TeleportStartPacket", "TeleportProgressPacket", "TeleportFailedPacket",
    "TeleportFinishPacket", "TeleportLocalPacket", "StartLurePacket", "TeleportLureRequestPacket",
    "ScriptDialogPacket", "ScriptDialogReplyPacket", "ScriptQuestionPacket", "ScriptAnswerYesPacket",
    "ObjectUpdatePacket", "RequestMultipleObjectsPacket", "ObjectUpdateCachedPacket",
    "ImprovedTerseObjectUpdatePacket", "KillObjectPacket", "RequestObjectPropertiesFamilyPacket",
    "ObjectPropertiesFamilyPacket", "ObjectPropertiesPacket",
    "ObjectMovePacket", "ObjectScalePacket", "ObjectRotationPacket",
    "ObjectNamePacket", "ObjectDescriptionPacket", "ObjectTextPacket", "ObjectClickActionPacket",
    "ObjectAddPacket", "ObjectGrabPacket", "ObjectDeGrabPacket",
    "RequestXferPacket", "SendXferPacket", "ConfirmXferPacket", "TransferInfoPacket", "TransferPacket",
    "RequestImagePacket", "ImageDataPacket", "ImageNotInDatabasePacket",
    "AssetUploadRequestPacket", "AssetUploadCompletePacket",
    "UpdateCreateInventoryItemPacket", "UpdateInventoryItemPacket", # Added server-side packet
    "OfferFriendshipPacket", "AcceptFriendshipPacket", "DeclineFriendshipPacket",
    "OnlineNotificationPacket", "OfflineNotificationPacket", "FindAgentPacket", "AgentOnlineStatusPacket",
    "ChangeUserRightsPacket", "TerminateFriendshipPacket",
    "ParcelPropertiesRequestPacket", "ParcelPropertiesPacket", # Added Parcel packets
    "ParcelAccessListRequestPacket", "ParcelAccessListReplyPacket", # Added ACL packets
    "AgentGroupDataUpdatePacket", "AgentSetGroupPacket" # Added Group packets
]
