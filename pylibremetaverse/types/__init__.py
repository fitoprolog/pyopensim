# Main __init__.py for the types sub-package

from .custom_uuid import CustomUUID
from .vector import Vector2, Vector3, Vector4
from .quaternion import Quaternion
from .matrix import Matrix4
from .color import Color4
from .enums import (
    AssetType, InventoryType, WearableType, PCode, PrimFlags, Material, LogLevel,
    ControlFlags, AgentState, AgentFlags,
    ChatType, ChatSourceType, ChatAudibleLevel,
    InstantMessageDialog, InstantMessageOnline,
    TeleportFlags, TeleportStatus,
    ScriptPermission,
    MuteType, MuteFlags, ClickAction,
    PathCurve, ProfileCurve, HoleType, SaleType, # Added HoleType
    PermissionMask, InventoryItemFlags,
    ChannelType, TargetType, StatusCode, TransferStatus,
    AddFlags, ImageType, FolderType # Added more recent enums
)
from .animations import Animations
from .primitive import Primitive, TextureEntryFace, TextureEntry, MAX_AVATAR_FACES # Added TE
from .inventory_defs import InventoryBase, InventoryFolder, InventoryItem
from .default_textures import ( # Added default textures
    DEFAULT_SKIN_TEXTURE, DEFAULT_EYES_TEXTURE, DEFAULT_HAIR_TEXTURE,
    DEFAULT_SHIRT_TEXTURE, DEFAULT_PANTS_TEXTURE
)
from .friends_defs import FriendRights, FriendInfo, BuddyListEntry # Added Friends defs


__all__ = [
    "CustomUUID", "Vector2", "Vector3", "Vector4", "Quaternion", "Matrix4", "Color4",
    "AssetType", "InventoryType", "WearableType", "PCode", "PrimFlags", "Material", "LogLevel",
    "ControlFlags", "AgentState", "AgentFlags",
    "ChatType", "ChatSourceType", "ChatAudibleLevel",
    "InstantMessageDialog", "InstantMessageOnline",
    "TeleportFlags", "TeleportStatus",
    "ScriptPermission",
    "MuteType", "MuteFlags", "ClickAction",
    "PathCurve", "ProfileCurve", "HoleType", "SaleType",
    "PermissionMask", "InventoryItemFlags",
    "ChannelType", "TargetType", "StatusCode", "TransferStatus",
    "AddFlags", "ImageType", "FolderType",
    "Animations",
    "Primitive", "TextureEntryFace", "TextureEntry", "MAX_AVATAR_FACES",
    "InventoryBase", "InventoryFolder", "InventoryItem",
    "DEFAULT_SKIN_TEXTURE", "DEFAULT_EYES_TEXTURE", "DEFAULT_HAIR_TEXTURE",
    "DEFAULT_SHIRT_TEXTURE", "DEFAULT_PANTS_TEXTURE",
    "FriendRights", "FriendInfo", "BuddyListEntry" # Added Friends defs
]
