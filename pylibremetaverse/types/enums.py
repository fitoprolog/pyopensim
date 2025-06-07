import enum

class AssetType(enum.Enum):
    Unknown = -1; Texture = 0; Sound = 1; CallingCard = 2; Landmark = 3; Clothing = 5; Object = 6; Notecard = 7; Category = 8; LSLText = 10; Bodypart = 13; Snapshot = 15; Animation = 20; Gesture = 21; Link = 24; LinkFolder = 25; RenderMaterial = 57
    Script = 4
class InventoryType(enum.Enum): # Based on C# OpenMetaverse.InventoryType and values from WearableType
    Unknown = -1
    Texture = 0
    Sound = 1
    CallingCard = 2
    Landmark = 3

    # Wearable types directly use WearableType values for their InvType
    Shape = 0       # AssetType.Bodypart, InvType is WearableType.Shape
    Skin = 1        # AssetType.Bodypart, InvType is WearableType.Skin
    Hair = 2        # AssetType.Bodypart, InvType is WearableType.Hair
    Eyes = 3        # AssetType.Bodypart, InvType is WearableType.Eyes
    Shirt = 4       # AssetType.Clothing, InvType is WearableType.Shirt
    Pants = 5       # AssetType.Clothing, InvType is WearableType.Pants
    Shoes = 6       # AssetType.Clothing, InvType is WearableType.Shoes (also Object/Attachment)
    Socks = 7       # AssetType.Clothing, InvType is WearableType.Socks
    Jacket = 8      # AssetType.Clothing, InvType is WearableType.Jacket
    Gloves = 9      # AssetType.Clothing, InvType is WearableType.Gloves
    Undershirt = 10 # AssetType.Clothing, InvType is WearableType.Undershirt
    Underpants = 11 # AssetType.Clothing, InvType is WearableType.Underpants
    Skirt = 12      # AssetType.Clothing, InvType is WearableType.Skirt
    Alpha = 13      # AssetType.Clothing, InvType is WearableType.Alpha (also Bodypart)
    Tattoo = 14     # AssetType.Clothing, InvType is WearableType.Tattoo
    Physics = 15    # AssetType.Clothing, InvType is WearableType.Physics
    Universal = 16  # AssetType.Clothing, InvType is WearableType.Universal

    Object = 6      # Generic object, could be an attachment if worn
    Notecard = 7
    Folder = 8      # Preferred for actual folders
    Category = 8    # Legacy or alternative for Folder
    RootFolder = 9  # Specific to root inventory folder

    LSLText = 10    # Script as text
    LSLBytecode = 11 # Compiled script
    TextureTGA = 12 # Specific texture format
    # Bodypart (13) from AssetType is covered by Shape, Skin, Hair, Eyes, Alpha if those are used as InvTypes
    # If a generic "Bodypart" InvType is needed, it can be added, but C# seems to use specific WearableType values.
    TrashFolder = 14
    Snapshot = 15
    LostAndFoundFolder = 16

    Attachment = 17 # An object that is attached to an avatar attachment point

    # General "Wearable" category if the specific type isn't known or for broader filtering.
    # However, individual items usually have specific InvTypes like Shirt, Pants etc.
    # This Wearable = 18 is from C# InventoryType, but its usage for *specific* items is less clear
    # if InvType is directly the WearableType value.
    GenericWearable = 18

    Animation = 19
    Gesture = 20

    Simstate = 21 # Not common for inventory items
    Link = 22 # Link to another inventory item
    LinkFolder = 23 # Link to an inventory folder

    MarketplaceFolder = 24
    MarketplaceListings = 25 # Deprecated by SL
    SettingsFolder = 26 # Client settings
    OutfitFolder = 27   # Contains links to items in an outfit
    MyOutfitsFolder = 28 # Root folder for outfits
    CurrentOutfitFolder = 29 # Virtual folder, not directly in inventory hierarchy usually

    Mesh = 30
    Inbox = 31          # System folder for received items
    Outbox = 32         # System folder
    Material = 33       # Material asset applied to a prim face

    # Ensure no duplicate values if new items are added unless they are true aliases
    # Example: Category = Folder is a true alias.
    # Shape's value is 0, same as Texture. This is per C# practice where InvType for wearables IS WearableType.
    # This means context (AssetType) is important. A Texture InvType 0 is AssetType.Texture.
    # A Shape InvType 0 is AssetType.Bodypart.

class WearableType(enum.Enum):
    Shape = 0; Skin = 1; Hair = 2; Eyes = 3; Shirt = 4; Pants = 5; Shoes = 6; Socks = 7; Jacket = 8; Gloves = 9; Undershirt = 10; Underpants = 11; Skirt = 12; Alpha = 13; Tattoo = 14; Physics = 15; Universal = 16; Invalid = 255
class PCode(enum.Enum):
    Primitive = 0; Box = 0; Cylinder = 1; Prism = 2; Sphere = 3; Torus = 4; Tube = 5; Ring = 6; Sculpt = 7; Mesh = 8
class WearableType(enum.Enum):
    Shape = 0; Skin = 1; Hair = 2; Eyes = 3; Shirt = 4; Pants = 5; Shoes = 6; Socks = 7; Jacket = 8; Gloves = 9; Undershirt = 10; Underpants = 11; Skirt = 12; Alpha = 13; Tattoo = 14; Physics = 15; Universal = 16; Invalid = 255
class PCode(enum.Enum):
    Primitive = 0; Box = 0; Cylinder = 1; Prism = 2; Sphere = 3; Torus = 4; Tube = 5; Ring = 6; Sculpt = 7; Mesh = 8
class PrimFlags(enum.IntFlag):
    None_ = 0; ObjectPhysics = 1; ObjectPhantom = 2; ObjectCastShadows = 4; ObjectMotion = 8; ObjectDieAtEdge = 16; ObjectReturnAtEdge = 32; ObjectSandbox = 64; ObjectBlockGrab = 128; ObjectBlockGrabNonOwner = 256; ObjectInventoryEmpty = 2048; ObjectUseNewPhysics = 4096; ObjectCameraSource = 8192; ObjectCastMasterShadows = 16384; ObjectTemporaryOnRez = 0x00080000; ObjectTemporary = 0x00080000; ObjectSelected = 0x01000000; ObjectForSale = 0x02000000; ObjectForSaleCopy = 0x04000000; ObjectForSaleContents = 0x06000000; ObjectForSaleOriginal = 0x0A000000; ObjectShowInSearch = 0x08000000; ObjectPartOfSelection = 0x10000000; ObjectAllowInventoryDrop = 0x40000000
    ObjectYouAvatar = 0x200; ObjectSheetBronze = 0x8000; ObjectScriptAlwaysColliding = 0x10000; ObjectIsCameraDecoy = 0x20000; ObjectTouchKeepsActive = 0x40000; ObjectTransferProtected = 0x20000000
class Material(enum.Enum): Stone = 0; Metal = 1; Glass = 2; Wood = 3; Flesh = 4; Plastic = 5; Rubber = 6; Light = 7
class LogLevel(enum.Enum): NONE = 0; DEBUG = 1; INFO = 2; WARNING = 3; ERROR = 4
class ControlFlags(enum.IntFlag):
    NONE=0;AGENT_CONTROL_AT_POS=1;AGENT_CONTROL_AT_NEG=2;AGENT_CONTROL_LEFT_POS=4;AGENT_CONTROL_LEFT_NEG=8;AGENT_CONTROL_UP_POS=16;AGENT_CONTROL_UP_NEG=32;AGENT_CONTROL_PITCH_POS=64;AGENT_CONTROL_PITCH_NEG=128;AGENT_CONTROL_YAW_POS=256;AGENT_CONTROL_YAW_NEG=512;AGENT_CONTROL_FAST_AT=1024;AGENT_CONTROL_FLY=2048;AGENT_CONTROL_STOP=4096;AGENT_CONTROL_FINISH_ANIM=0x2000;AGENT_CONTROL_STAND_UP=0x4000;AGENT_CONTROL_SIT_ON_GROUND=0x8000;AGENT_CONTROL_MOUSELOOK=0x10000;AGENT_CONTROL_NUDGE_AT_POS=0x20000;AGENT_CONTROL_NUDGE_AT_NEG=0x40000;AGENT_CONTROL_NUDGE_LEFT_POS=0x80000;AGENT_CONTROL_NUDGE_LEFT_NEG=0x100000;AGENT_CONTROL_TURN_LEFT=0x200000;AGENT_CONTROL_TURN_RIGHT=0x400000;AGENT_CONTROL_AWAY=0x800000;AGENT_CONTROL_LBUTTON_DOWN=0x1000000;AGENT_CONTROL_LBUTTON_UP=0x2000000;AGENT_CONTROL_ML_LBUTTON_DOWN=0x4000000;AGENT_CONTROL_ML_LBUTTON_UP=0x8000000;AGENT_CONTROL_UNSIT=0x10000000;AGENT_CONTROL_DELAY_SHUTDOWN=0x20000000;AGENT_CONTROL_HANDLE_SHUTDOWN=0x40000000;AGENT_CONTROL_AUTOPILOT=0x80000000
    AGENT_CONTROL_ROT_LEFT=AGENT_CONTROL_YAW_POS;AGENT_CONTROL_ROT_RIGHT=AGENT_CONTROL_YAW_NEG
class AgentState(enum.IntEnum): NONE=0;WALKING=1;RUNNING=2;FLYING=3;JUMPING=4;HOVERING=5;CROUCHING=6;SITTING=7
class AgentFlags(enum.IntFlag): NONE=0;FLYING=1;ALWAYS_RUN=2;MOUSELOOK=4;SITTING=8;AUTOPILOT=16
class ChatType(enum.Enum): WHISPER=0;NORMAL=1;SHOUT=2;START_TYPING=4;STOP_TYPING=5;DEBUG=6;OWNER_SAY=8;REGION_SAY_TO=9;REGION_SAY=10
class ChatSourceType(enum.Enum): SYSTEM=0;AGENT=1;OBJECT=2
class ChatAudibleLevel(enum.Enum): NOT=-1;BARELY=0;FULLY=1
class InstantMessageDialog(enum.Enum): MessageFromAgent=0;MessageBox=1;GroupInvitation=3;InventoryOffered=4;InventoryAccepted=5;InventoryDeclined=6;GroupVote=7;TaskInventoryOffered=9;TaskInventoryAccepted=10;TaskInventoryDeclined=11;NewUserDefault=12;SessionSend=13;SessionOffline=14;SessionGroupStart=15;SessionRequest=17;SessionAccept=18;SessionDecline=19;SessionLeave=20;FriendshipOffered=21;FriendshipAccepted=22;FriendshipDeclined=23;StartTyping=24;StopTyping=25;SessionToAgent=26;SessionGroupInvite=27;RequestTeleport=30;AcceptTeleport=31;DenyTeleport=32;RequestLure=33;GroupNotice=37;ToAgent=41;RequestOnlineStatus=42;RequestDisplayName=45;RequestDisplayNames=46;SendDisplayName=47;SendUserIdentification=48;CONSOLE=100
class TeleportFlags(enum.IntFlag): NONE=0;ViaLure=8;ViaLandmark=16;ViaLocation=32;ViaHome=64;ViaTelehub=128;ViaLogin=256;ViaGodlikeLure=512;Godlike=1024;NineOneOne=2048;DisableCancel=4096;ViaRegionID=0x2000;IsFlying=0x4000;ForceRedirect=0x8000;FinishedSignalling=0x10000;EnableSwirling=0x20000;NoSimChange=0x80000
class TeleportStatus(enum.Enum): NONE=0;START=1;PROGRESS=2;FAILED=3;FINISHED=4;CANCELLED=5
class ScriptPermission(enum.IntFlag): NONE=0;DEBIT=2;TAKE_CONTROLS=4;REMAP_CONTROLS=8;TRIGGER_ANIMATION=16;ATTACH=32;RELEASE_OWNERSHIP=64;CHANGE_LINKS=128;CHANGE_JOINTS=256;CHANGE_PERMISSIONS=512;TRACK_CAMERA=1024;CONTROL_CAMERA=2048;TELEPORT=4096;OVERRIDE_SIT_STATE=0x8000;ANIMATE=TRIGGER_ANIMATION;ALL=DEBIT|TAKE_CONTROLS|REMAP_CONTROLS|TRIGGER_ANIMATION|ATTACH|RELEASE_OWNERSHIP|CHANGE_LINKS|CHANGE_JOINTS|CHANGE_PERMISSIONS|TRACK_CAMERA|CONTROL_CAMERA|TELEPORT|OVERRIDE_SIT_STATE
class MuteType(enum.Enum): NONE=0;BY_NAME=1;RESIDENT=2;OBJECT=3;GROUP=4;EXTERNAL=5
class MuteFlags(enum.IntFlag): DEFAULT=0;TEXT_CHAT=1;VOICE_CHAT=2;PARTICLES=4;OBJECT_SOUNDS=8;ALL=0xFFFFFFFF
class InstantMessageOnline(enum.Enum): Online=0;Offline=1;Away=2;Busy=3;WantToChat=4;Muted=5;Unknown=6
class ClickAction(enum.Enum): TOUCH=0;SIT_ON=1;BUY_OBJECT=2;PAY_OBJECT=3;OPEN_TASK=4;PLAY_SOUND=5;OPEN_MEDIA=6;ZOOM=7;BUY_PASS=8;BUY_LAND=9;TOUCH_FACE=10;SIT_TARGET=11;NONE=255
class PathCurve(enum.Enum):
    LINE = 0x00
    CIRCLE = 0x01
    CIRCLE2 = 0x02      # Circle Reverse
    TEST = 0x03         # Effectively Flexible in many viewers
    FLEXIBLE = 0x04
class ProfileCurve(enum.Enum): CIRCLE=0;SQUARE=1;ISOSCELES_TRIANGLE=2;EQUILATERAL_TRIANGLE=3;RIGHT_TRIANGLE=4;HALF_CIRCLE=5
class HoleType(enum.Enum): # Used for prim hole types, often combined with ProfileCurve
    SAME = 0x00
    CIRCLE = 0x10
    SQUARE = 0x20
    TRIANGLE = 0x30
class SaleType(enum.Enum): NOT_FOR_SALE=0;COPY=1;CONTENTS=2;ORIGINAL=3
class PermissionMask(enum.IntFlag): NONE=0;MOVE=0x8000;COPY=0x10000;TRANSFER=0x2000;MODIFY=0x4000;NEXT_OWNER_COPY=8;NEXT_OWNER_MODIFY=16;NEXT_OWNER_TRANSFER=4;ALL=0x7FFFFFFF;DEFAULT_ITEM_PERMS=COPY|MODIFY|TRANSFER
class InventoryItemFlags(enum.IntFlag): NONE=0;ALLOW_INVENTORY_DROP=1;TAKEN_VIA_TASK=2;PERMISSIONS_VERSION=4;COPIED_FROM_SIM=8;WEARABLE_VERSION=16;GROUP_OWNED_DEPRECATED=32;LINK=64;ALWAYS_WEARABLE=128;BAD_PERMISSIONS=256;ALLOW_ASSET_DROP=512

# --- Asset/Xfer Related Enums ---
class ChannelType(enum.Enum):
    """Channel type for asset transfers (Xfer system)."""
    Lindenванта = 0 # Linden "ванта" channel (main asset channel) - Note: 'ванта' might be a typo for 'Vanta' or similar. Using as is.
    Misc = 1        # Miscellaneous channel (e.g., for mute lists, some configs)
    Unknown = 2     # Deprecated/Unknown (C# uses 255)

class TargetType(enum.Enum):
    """Target type for asset transfers."""
    File = 0            # Transfer is for a generic file asset
    TaskInventory = 1   # Transfer is for an item into task (prim) inventory
    Unknown = 2         # Deprecated/Unknown (C# uses 255)

class StatusCode(enum.Enum):
    """Status codes for various operations, often used in Xfer system and CAPS."""
    OK = 200; CREATED = 201; NO_CONTENT = 204; NOT_MODIFIED = 304
    BAD_REQUEST = 400; UNAUTHORIZED = 401; FORBIDDEN = 403; NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405; PRECONDITION_FAILED = 412; UNSUPPORTED_MEDIA_TYPE = 415
    INTERNAL_SERVER_ERROR = 500; NOT_IMPLEMENTED = 501; SERVICE_UNAVAILABLE = 503
    UNKNOWN = -1 # Local client addition for unknown status

class TransferStatus(enum.Enum):
    """Status of an asset transfer."""
    Unknown = 0; Queued = 1; InProgress = 2; Done = 3
    Error = -1; NotFound = -2; AssetProblem = -3; InsufficientFunds = -4
    # Custom statuses for client-side management
    WaitingForInfo = 100 # Waiting for TransferInfoPacket
    Cancelled = -5 # Client cancelled
    TimedOut = -6  # Transfer timed out
    FileError = -7 # Local file error during save/load
    HttpError = -8 # HTTP error during CAPS based transfer part

class AddFlags(enum.IntFlag):
    NONE = 0
    USE_PHYSICS = 0x01          # Enable physics for the new object
    CREATE_SELECTED = 0x02      # Object should be selected after creation
    FOLLOW_CAM = 0x04           # Object should follow camera until clicked again (deprecated/rarely used by clients)
    ATTACH_TO_ROOT = 0x08       # Attach to avatar root (no specific attach point)
    ROTATE_SELECTED = 0x10      # Used with CreateSelected, new object becomes root of selection, current selection rotates
    PING_PONG = 0x20            # Path PCode parameter for ping-pong movement
    ZERO_POSITION = 0x40        # Internal use with FollowCam, object position is not offset by agent
    ZERO_ROTATION = 0x80        # Internal use with FollowCam, object rotation is not offset by agent

class FolderType(enum.Enum):
    """Preferred content type for a folder. Matches C# OpenMetaverse.FolderType."""
    NONE = -1
    TEXTURE = 0
    SOUND = 1
    CALLING_CARD = 2
    LANDMARK = 3
    CLOTHING = 5
    OBJECT = 6
    NOTECARD = 7
    ROOT = 8  # Inventory Root Folder
    LSLTEXT = 10
    BODYPART = 13 # Body Parts Folder
    TRASH = 14
    SNAPSHOT = 15
    LOST_AND_FOUND = 16
    ANIMATION = 20
    GESTURE = 21
    FAVORITES = 23
    # Values from InventoryType that are folder concepts
    SETTINGS = 26         # Settings Folder
    OUTFIT = 27           # Outfit Folder (containing links)
    MY_OUTFITS = 28       # My Outfits Root Folder
    CURRENT_OUTFIT = 29   # Current Outfit Links Folder (virtual)
    MESH = 49             # Mesh Folder
    INBOX = 50            # Received Items Folder
    OUTBOX = 51           # Sent Items Folder (less common)
    MARKETPLACE_LISTINGS = 53 # Marketplace Listings
    MARKETPLACE_STOCK = 54    # Marketplace Stock
    SUITCASE = 100        # Hypergrid Suitcase folder (OpenSim)
    # Other specific system folders might exist.
    # For general user created folders, NONE or a content type is fine.

class ImageType(enum.Enum):
    """Type of image being requested, used in RequestImagePacket."""
    NORMAL = 0      # Normal texture asset
    BAKED = 1       # Avatar baked texture (e.g., head, body, skirt)
    # Values from C# TextureType that might be relevant if ImageType expands:
    # Unknown = -1 (though usually default to Normal if not specified)
