from enum import Enum, IntEnum, Flag # IntEnum for direct integer compatibility, Flag for bitmasks

# Based on OpenMetaverse.AssetType
class AssetType(IntEnum):
    """Asset type values"""
    Unknown = -1
    Texture = 0         # Texture asset, stores in JPEG2000 J2C stream format
    Sound = 1           # Sound asset
    CallingCard = 2     # Calling card asset
    Landmark = 3        # Landmark asset
    Script = 4          # Script asset (deprecated, use LSLText or LSLBytecode)
    Clothing = 5        # Clothing asset
    Object = 6          # Object asset
    Notecard = 7        # Notecard asset
    Category = 8        # Inventory category folder (used as a type for folders in asset server)
    Root = 9            # Inventory root folder (deprecated by Linden Lab)
    LSLText = 10        # LSL script text asset
    LSLBytecode = 11    # LSL compiled bytecode asset
    TextureTGA = 12     # Uncompressed TGA texture asset (typically uploaded and converted to Texture)
    Bodypart = 13       # Bodypart asset (contains wearable parameters)
    Trash = 14          # Trash folder (deprecated by Linden Lab)
    Snapshot = 15       # Snapshot folder
    LostAndFound = 16   # Lost and found folder (deprecated by Linden Lab)
    Animation = 20      # Animation asset (BVH format)
    Gesture = 21        # Gesture asset
    Simstate = 22       # Simstate file (simulator state backup, not common for clients)
    FavoriteFolder = 23 # Favorite Folder (no longer used by viewer)
    Link = 24           # Link to another inventory item (deprecated by Linden Lab)
    LinkFolder = 25     # Link to an inventory folder (deprecated by Linden Lab)
    MarketplaceFolder = 26 # Marketplace Listings folder (deprecated by Linden Lab)
    CurrentOutfitFolder = 46 # Current outfit folder
    OutfitFolder = 47   # Outfit folder
    MyOutfitsFolder = 48 # My Outfits folder
    Mesh = 49           # Mesh asset
    Inbox = 50          # Received items folder (deprecated by Linden Lab, use FolderType.Inbox)
    Outbox = 51         # Merchant outbox folder (deprecated by Linden Lab)
    BasicRoot = 52      # Basic root folder (deprecated by Linden Lab)
    MarketplaceListings = 53 # Marketplace listings folder (deprecated by Linden Lab)
    MarketplaceStock = 54    # Marketplace stock folder (deprecated by Linden Lab)
    Hyperlink = 55      # Hyperlink asset (deprecated by Linden Lab)
    MarketplaceSale = 56 # An item that has been sold on the Marketplace and is awaiting delivery.
    Settings = 57       # Viewer settings asset
    RenderMaterial = 58 # RenderMaterial Asset. Contains PBR material properties.

    @staticmethod
    def is_transient(asset_type: "AssetType") -> bool:
        return asset_type == AssetType.Simstate

# Based on OpenMetaverse.InventoryType
class InventoryType(IntEnum):
    """Inventory type values for inventory items. Note the overlap with WearableType for clothing/bodyparts."""
    Unknown = -1
    Texture = 0
    Sound = 1
    CallingCard = 2
    Landmark = 3
    # Script = 4 (Obsolete: See LSLText) AssetType.Script is also obsolete.
    Clothing = 5 # This is a general category. Specific items use WearableType.
    Object = 6
    Notecard = 7
    Category = 8 # Represents a folder category.
    RootCategory = 9 # The root folder of inventory.
    LSL = 10 # LSLText Script. AssetType.LSLText.
    # LSLBytecode = 11 (Not an inventory item, only an asset type)
    # TextureTGA = 12 (Not an inventory item, only an asset type)
    Bodypart = 13 # This is a general category. Specific items use WearableType.
    Trash = 14 # Trash folder.
    Snapshot = 15 # Snapshot folder.
    LostAndFound = 16 # Lost and Found folder.
    Attachment = 17 # An object that is attached to an avatar attachment point.
    Wearable = 18 # Generic "wearable" item, context of AssetType and ItemID needed. Specific items use WearableType.
    Animation = 19 # AssetType.Animation
    Gesture = 20 # AssetType.Gesture
    # Simstate = 21 (Not an inventory item, only an asset type)
    Link = 22 # Link to another inventory item
    LinkFolder = 23 # Link to an inventory folder (rarely used)
    MarketplaceFolder = 24 # A virtual folder in marketplace direct delivery.
    # MarketplaceListings = 25 (No longer an InvType per se)
    Settings = 26 # Client settings item/folder. AssetType.Settings.
    Outfit = 27 # An outfit folder.
    MyOutfits = 28 # The "My Outfits" root folder.
    CurrentOutfit = 29 # The "Current Outfit" links folder (virtual).
    Mesh = 30 # AssetType.Mesh
    Inbox = 31 # System folder for received items.
    Outbox = 32 # System folder for merchant outbox.
    Material = 33 # AssetType.RenderMaterial

# Based on OpenMetaverse.WearableType
class WearableType(IntEnum):
    """Specific type of wearable item. These values are often used as the InventoryType for clothing/bodyparts."""
    Shape = 0
    Skin = 1
    Hair = 2
    Eyes = 3
    Shirt = 4
    Pants = 5
    Shoes = 6
    Socks = 7
    Jacket = 8
    Gloves = 9
    Undershirt = 10
    Underpants = 11
    Skirt = 12
    Alpha = 13
    Tattoo = 14
    Physics = 15
    Universal = 16
    Invalid = 255

# Based on OpenMetaverse.PCode (Primitive Code)
class PCode(IntEnum):
    """Primitive code, indicates the high-level type of a primitive in object updates."""
    Unknown = 0
    Prim = 9 # Deprecated, effectively Box
    Avatar = 47
    Grass = 95
    NewTree = 111 # Linden tree type used in new style regions
    ParticleSystem = 143
    Tree = 255 # Linden tree type used in old style regions

# Based on OpenMetaverse.PrimType (used for prim shape/meshing)
# This was the second PCode definition in the existing file. Renamed for clarity.
class PrimType(IntEnum):
    """Type of a primitive, used for path cutting and profile."""
    Unknown = 0 # Should not be used
    Box = 0
    Cylinder = 1
    Prism = 2
    Sphere = 3
    Torus = 4
    Tube = 5
    Ring = 6
    Sculpt = 7 # Sculpted prim
    Mesh = 8   # Mesh

# Based on OpenMetaverse.Material
class Material(IntEnum):
    """Material type for a primitive, affects physics and sound."""
    Stone = 0
    Metal = 1
    Glass = 2
    Wood = 3
    Flesh = 4
    Plastic = 5
    Rubber = 6
    Light = 7 # Used for light source prims

# Based on OpenMetaverse.PrimFlags
class PrimFlags(Flag):
    """Low-level flags that modify the properties of a primitive."""
    NoneFlag = 0x00000000 # Using "NoneFlag" to avoid keyword clash with None
    CreateSelected = 0x00000001 # Object is selected. This is a client-side only flag
    ObjectModify = 0x00000002 # Deprecated, use an appropriate part of Permissions mask
    ObjectCopy = 0x00000004 # Deprecated, use an appropriate part of Permissions mask
    ObjectAnyOwner = 0x00000008 # Deprecated
    ObjectYouOwner = 0x00000010 # Deprecated
    ObjectGroupOwned = 0x00000020 # Deprecated
    ObjectOwnerModify = 0x00000040 # Deprecated
    ObjectTransfer = 0x00000080 # Deprecated, use an appropriate part of Permissions mask
    ObjectYouOfficer = 0x00000100 # Deprecated
    ObjectGroupMod = 0x00000200 # Deprecated
    ObjectMove = ObjectModify # Alias, also deprecated

    InventoryEmpty = 0x00000800 # Object has no inventory
    Touch = 0x00001000 # Object can be touched
    Money = 0x00002000 # Object is a money object (pays on touch)
    Phantom = 0x00004000 # Object is phantom (no collision)
    InventoryTransfer = 0x00008000 # Deprecated
    ObjectSale = 0x00010000 # Deprecated
    AllowInventoryDrop = 0x00020000 # Allow inventory to be dropped onto this prim
    CastShadows = 0x00040000 # Object casts shadows
    ObjectPhysical = 0x00080000 # Object is physical (subject to physics)
    DieAtEdge = 0x00100000 # Object is destroyed when it crosses a region boundary
    ReturnAtEdge = 0x00200000 # Object is returned when it crosses a region boundary
    Sandbox = 0x00400000 # Object is in a sandbox region (auto-return after some time)
    BlockGrab = 0x00800000 # Object cannot be grabbed by default
    ObjectForSale = ObjectSale # Alias, also deprecated

    Scripted = 0x08000000 # Object contains one or more scripts
    TextureAnim = 0x10000000 # Object has texture animations
    UsePhysics = ObjectPhysical # Alias
    Physics = ObjectPhysical # Alias
    BlockGrabOverride = 0x40000000 # Individual prim grab override, allows BlockGrab to be overridden
    Fly = 0x80000000 # Object can fly (usually applies to avatars, but can be set on objects)

# --- Other Enums from existing file (to be kept and reviewed) ---
class LogLevel(IntEnum): NONE = 0; DEBUG = 1; INFO = 2; WARNING = 3; ERROR = 4

class ControlFlags(Flag):
    NONE=0;AGENT_CONTROL_AT_POS=1;AGENT_CONTROL_AT_NEG=2;AGENT_CONTROL_LEFT_POS=4;AGENT_CONTROL_LEFT_NEG=8
    AGENT_CONTROL_UP_POS=16;AGENT_CONTROL_UP_NEG=32;AGENT_CONTROL_PITCH_POS=64;AGENT_CONTROL_PITCH_NEG=128
    AGENT_CONTROL_YAW_POS=256;AGENT_CONTROL_YAW_NEG=512;AGENT_CONTROL_FAST_AT=1024;AGENT_CONTROL_FLY=2048
    AGENT_CONTROL_STOP=4096;AGENT_CONTROL_FINISH_ANIM=0x2000;AGENT_CONTROL_STAND_UP=0x4000
    AGENT_CONTROL_SIT_ON_GROUND=0x8000;AGENT_CONTROL_MOUSELOOK=0x10000
    AGENT_CONTROL_NUDGE_AT_POS=0x20000;AGENT_CONTROL_NUDGE_AT_NEG=0x40000
    AGENT_CONTROL_NUDGE_LEFT_POS=0x80000;AGENT_CONTROL_NUDGE_LEFT_NEG=0x100000
    AGENT_CONTROL_TURN_LEFT=0x200000;AGENT_CONTROL_TURN_RIGHT=0x400000;AGENT_CONTROL_AWAY=0x800000
    AGENT_CONTROL_LBUTTON_DOWN=0x1000000;AGENT_CONTROL_LBUTTON_UP=0x2000000
    AGENT_CONTROL_ML_LBUTTON_DOWN=0x4000000;AGENT_CONTROL_ML_LBUTTON_UP=0x8000000
    AGENT_CONTROL_UNSIT=0x10000000 # Stand up from a chosen sit target
    AGENT_CONTROL_DELAY_SHUTDOWN=0x20000000 # Client is performing a delayed logoff
    AGENT_CONTROL_HANDLE_SHUTDOWN=0x40000000 # Deprecated
    AGENT_CONTROL_AUTOPILOT=0x80000000 # Client is in autopilot mode
    AGENT_CONTROL_ROT_LEFT=AGENT_CONTROL_YAW_POS # Alias
    AGENT_CONTROL_ROT_RIGHT=AGENT_CONTROL_YAW_NEG # Alias

class AgentState(IntEnum): NONE=0;WALKING=1;RUNNING=2;FLYING=3;JUMPING=4;HOVERING=5;CROUCHING=6;SITTING=7

class AgentFlags(Flag): NONE=0;FLYING=1;ALWAYS_RUN=2;MOUSELOOK=4;SITTING=8;AUTOPILOT=16

class ChatType(IntEnum):
    WHISPER=0;NORMAL=1;SHOUT=2;START_TYPING=4;STOP_TYPING=5;DEBUG=6;OWNER_SAY=8
    REGION_SAY_TO=9 # Say to a specific avatar (نیمه خصوصی)
    REGION_SAY=10 # Public chat only in the current region

class ChatSourceType(IntEnum): SYSTEM=0;AGENT=1;OBJECT=2

class ChatAudibleLevel(IntEnum): NOT=-1;BARELY=0;FULLY=1

class InstantMessageDialog(IntEnum):
    MessageFromAgent=0;MessageBox=1;GroupInvitation=3;InventoryOffered=4;InventoryAccepted=5
    InventoryDeclined=6;GroupVote=7;TaskInventoryOffered=9;TaskInventoryAccepted=10
    TaskInventoryDeclined=11;NewUserDefault=12;SessionSend=13;SessionOffline=14
    SessionGroupStart=15;SessionRequest=17;SessionAccept=18;SessionDecline=19;SessionLeave=20
    FriendshipOffered=21;FriendshipAccepted=22;FriendshipDeclined=23;StartTyping=24;StopTyping=25
    SessionToAgent=26;SessionGroupInvite=27;RequestTeleport=30;AcceptTeleport=31;DenyTeleport=32
    RequestLure=33;GroupNotice=37;ToAgent=41;RequestOnlineStatus=42;RequestDisplayName=45
    RequestDisplayNames=46;SendDisplayName=47;SendUserIdentification=48;CONSOLE=100

class TeleportFlags(Flag):
    NONE=0;ViaLure=8;ViaLandmark=16;ViaLocation=32;ViaHome=64;ViaTelehub=128;ViaLogin=256
    ViaGodlikeLure=512;Godlike=1024;NineOneOne=2048;DisableCancel=4096;ViaRegionID=0x2000
    IsFlying=0x4000;ForceRedirect=0x8000;FinishedSignalling=0x10000 # Client finished signal to server
    EnableSwirling=0x20000 # Client requests swirly effect
    NoSimChange=0x80000 # Teleport within the same sim

class TeleportStatus(IntEnum): NONE=0;START=1;PROGRESS=2;FAILED=3;FINISHED=4;CANCELLED=5

class ScriptPermission(Flag): # From C# ScriptSensorTypeFlags, but seems like permissions
    NONE=0;DEBIT=2;TAKE_CONTROLS=4;REMAP_CONTROLS=8;TRIGGER_ANIMATION=16;ATTACH=32
    RELEASE_OWNERSHIP=64;CHANGE_LINKS=128;CHANGE_JOINTS=256;CHANGE_PERMISSIONS=512
    TRACK_CAMERA=1024;CONTROL_CAMERA=2048;TELEPORT=4096;OVERRIDE_SIT_STATE=0x8000
    ANIMATE=TRIGGER_ANIMATION # Alias
    ALL=(DEBIT|TAKE_CONTROLS|REMAP_CONTROLS|TRIGGER_ANIMATION|ATTACH|RELEASE_OWNERSHIP|
         CHANGE_LINKS|CHANGE_JOINTS|CHANGE_PERMISSIONS|TRACK_CAMERA|CONTROL_CAMERA|TELEPORT|OVERRIDE_SIT_STATE)

class MuteType(IntEnum): NONE=0;BY_NAME=1;RESIDENT=2;OBJECT=3;GROUP=4;EXTERNAL=5 # External is for web-based mutes

class MuteFlags(Flag): DEFAULT=0;TEXT_CHAT=1;VOICE_CHAT=2;PARTICLES=4;OBJECT_SOUNDS=8;ALL=0xFFFFFFFF

class InstantMessageOnline(IntEnum):
    Online=0;Offline=1;Away=2;Busy=3;WantToChat=4;Muted=5;Unknown=6 # Should map to UIMFriendStatus

class ClickAction(IntEnum):
    TOUCH=0;SIT_ON=1;BUY_OBJECT=2;PAY_OBJECT=3;OPEN_TASK=4;PLAY_SOUND=5;OPEN_MEDIA=6;ZOOM=7
    BUY_PASS=8;BUY_LAND=9;TOUCH_FACE=10 # Obsolete?
    SIT_TARGET=11;NONE=255

class PathCurve(IntEnum):
    LINE = 0x00; CIRCLE = 0x01; CIRCLE2 = 0x02; TEST = 0x03; FLEXIBLE = 0x04

class ProfileCurve(IntEnum):
    CIRCLE=0;SQUARE=1;ISOSCELES_TRIANGLE=2;EQUILATERAL_TRIANGLE=3;RIGHT_TRIANGLE=4;HALF_CIRCLE=5

class HoleType(IntEnum):
    SAME = 0x00; CIRCLE = 0x10; SQUARE = 0x20; TRIANGLE = 0x30

class SaleType(IntEnum): NOT_FOR_SALE=0;COPY=1;CONTENTS=2;ORIGINAL=3

class PermissionMask(Flag):
    NONE = 0
    MOVE = 0x00008000
    COPY = 0x00010000
    TRANSFER = 0x00002000 # Corresponds to "No Transfer" if not set.
    MODIFY = 0x00004000
    NEXT_OWNER_COPY = 0x00000008
    NEXT_OWNER_MODIFY = 0x00000010
    NEXT_OWNER_TRANSFER = 0x00000004
    ALL = 0x7FFFFFFF
    # DEFAULT_ITEM_PERMS = COPY | MODIFY | TRANSFER # This is not a standard mask value

class InventoryItemFlags(Flag):
    NONE = 0
    ALLOW_INVENTORY_DROP = 1 # Item can be dropped from inventory onto a prim.
    TAKEN_VIA_TASK = 2       # Item was taken from a prim via a script (LSL give inventory).
    PERMISSIONS_VERSION = 4  # Indicates if the permissions fields are up to date (SalePrice, SaleType).
    COPIED_FROM_SIM = 8      # Item was copied from in-world (e.g. "Take Copy").
    WEARABLE_VERSION = 16    # Indicates if wearable item uses new style parameters.
    GROUP_OWNED_DEPRECATED = 32 # Deprecated. Group ownership is now on Permissions.OwnerMask.
    LINK = 64                # Item is a link (symlink) to another item.
    ALWAYS_WEARABLE = 128    # Item can be worn even if it's no-copy.
    BAD_PERMISSIONS = 256    # Permissions on this item are invalid or inconsistent.
    ALLOW_ASSET_DROP = 512   # Item can be dropped from inventory as an asset (e.g. texture onto a face).

class ChannelType(IntEnum):
    LindenVanta = 0 # 'ванта' was a typo for Vchannel or similar, but this is the C# name.
    Misc = 1
    Unknown = 255 # From C#

class TargetType(IntEnum):
    File = 0
    TaskInventory = 1
    Unknown = 255 # From C#

class StatusCode(IntEnum):
    OK = 200; CREATED = 201; NO_CONTENT = 204; NOT_MODIFIED = 304
    BAD_REQUEST = 400; UNAUTHORIZED = 401; FORBIDDEN = 403; NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405; PRECONDITION_FAILED = 412; UNSUPPORTED_MEDIA_TYPE = 415
    INTERNAL_SERVER_ERROR = 500; NOT_IMPLEMENTED = 501; SERVICE_UNAVAILABLE = 503
    UNKNOWN = -1 # Local client addition

class TransferStatus(IntEnum):
    Unknown = 0; Queued = 1; InProgress = 2; Done = 3
    Error = -1; NotFound = -2; AssetProblem = -3; InsufficientFunds = -4
    WaitingForInfo = 100; Cancelled = -5; TimedOut = -6; FileError = -7; HttpError = -8

class AddFlags(Flag): # Flags used in ObjectAdd packet
    NONE = 0
    USE_PHYSICS = 0x01
    CREATE_SELECTED = 0x02
    FOLLOW_CAM = 0x04
    ATTACH_TO_ROOT = 0x08 # Deprecated, use AttachmentPoint
    ROTATE_SELECTED = 0x10
    PING_PONG = 0x20
    ZERO_POSITION = 0x40 # For internal use with FollowCam
    ZERO_ROTATION = 0x80 # For internal use with FollowCam

class FolderType(IntEnum): # Preferred content type for a folder, matches C# OpenMetaverse.FolderType
    NONE = -1; TEXTURE = 0; SOUND = 1; CALLING_CARD = 2; LANDMARK = 3; CLOTHING = 5
    OBJECT = 6; NOTECARD = 7; ROOT = 8; LSLTEXT = 10; BODYPART = 13; TRASH = 14
    SNAPSHOT = 15; LOST_AND_FOUND = 16; ANIMATION = 20; GESTURE = 21; FAVORITES = 23
    SETTINGS = 26; OUTFIT = 27; MY_OUTFITS = 28; CURRENT_OUTFIT = 29
    MESH = 49; INBOX = 50; OUTBOX = 51; MARKETPLACE_LISTINGS = 53; MARKETPLACE_STOCK = 54
    SUITCASE = 100 # OpenSim specific

class ImageType(IntEnum): # Used in RequestImagePacket
    NORMAL = 0; BAKED = 1

if __name__ == '__main__':
    print("Testing Enums...")
    print(f"AssetType.Texture: {AssetType.Texture.value} ({AssetType.Texture.name})")
    assert AssetType.Texture == 0
    print(f"InventoryType.Mesh: {InventoryType.Mesh.value} ({InventoryType.Mesh.name})")
    assert InventoryType.Mesh == 30
    print(f"WearableType.Shirt: {WearableType.Shirt.value} ({WearableType.Shirt.name})")
    assert WearableType.Shirt == 4
    print(f"PCode.Avatar: {PCode.Avatar.value} ({PCode.Avatar.name})")
    assert PCode.Avatar == 47
    print(f"PrimType.Cylinder: {PrimType.Cylinder.value} ({PrimType.Cylinder.name})")
    assert PrimType.Cylinder == 1
    print(f"Material.Metal: {Material.Metal.value} ({Material.Metal.name})")
    assert Material.Metal == 1
    flags = PrimFlags.ObjectPhysical | PrimFlags.CastShadows
    print(f"PrimFlags Combo: {flags} (int: {int(flags)})")
    assert PrimFlags.ObjectPhysical in flags
    assert PrimFlags.Sandbox not in flags
    print(f"ControlFlags.AGENT_CONTROL_FLY: {ControlFlags.AGENT_CONTROL_FLY.value}")
    assert ControlFlags.AGENT_CONTROL_FLY == 2048
    print(f"LogLevel.INFO: {LogLevel.INFO.value}")
    assert LogLevel.INFO == 2
    print(f"TeleportFlags.ViaLogin: {TeleportFlags.ViaLogin.value}")
    assert TeleportFlags.ViaLogin == 256
    print(f"PermissionMask.COPY: {PermissionMask.COPY.value}")
    assert PermissionMask.COPY == 0x10000

    # Test a few more from the existing list
    print(f"ChatType.SHOUT: {ChatType.SHOUT.value}")
    assert ChatType.SHOUT == 2
    print(f"ClickAction.SIT_ON: {ClickAction.SIT_ON.value}")
    assert ClickAction.SIT_ON == 1
    print(f"FolderType.MESH: {FolderType.MESH.value}")
    assert FolderType.MESH == 49
    print(f"StatusCode.NOT_FOUND: {StatusCode.NOT_FOUND.value}")
    assert StatusCode.NOT_FOUND == 404
    print("Enums tests passed.")
