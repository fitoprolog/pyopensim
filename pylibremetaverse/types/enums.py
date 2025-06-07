import enum

class AssetType(enum.Enum):
    """
    Asset types that can be uploaded or found in inventory.
    Corresponds to sbyte in C#.
    """
    Unknown = -1
    Texture = 0
    Sound = 1
    CallingCard = 2
    Landmark = 3
    # Script = 4 # Obsolete
    Clothing = 5
    Object = 6
    Notecard = 7
    Category = 8 # Also an InventoryType
    # Root = 9 # Obsolete
    LSLText = 10 # LSL Script
    LSLBytecode = 11 # Obsolete
    TextureTGA = 12 # Obsolete
    Bodypart = 13
    # Trash = 14 # Obsolete
    Snapshot = 15
    # LostAndFound = 16 # Obsolete
    SoundWAV = 17 # Obsolete
    TextureJPEG = 18 # Obsolete
    Animation = 20
    Gesture = 21
    Simstate = 22 # Obsolete
    # FavoriteFolder = 23 # Obsolete
    Link = 24 # Inventory Link
    LinkFolder = 25 # Inventory Link Folder
    # CurrentOutfitFolder = 26 # Obsolete
    # OutfitFolder = 27 # Obsolete
    # MyOutfitsFolder = 28 # Obsolete
    # Mesh = 30 # Obsolete
    MarketplaceFolder = 32 # Obsolete
    MarketplaceListing = 33 # Obsolete
    SettingsFolder = 38 # Obsolete
    # Settings = 39 # Obsolete
    RenderMaterial = 57 # Obsolete (was Material)


class InventoryType(enum.Enum):
    """
    Inventory item types. Corresponds to sbyte in C#.
    Note that some values overlap with AssetType.
    """
    Unknown = -1
    Texture = 0
    Sound = 1
    CallingCard = 2
    Landmark = 3
    Object = 6
    Notecard = 7
    Folder = 8 # Category and Folder are the same value, representing a folder.
    Category = 8 # Alias for Folder
    RootCategory = 9 # Root folder for the inventory category
    LSL = 10 # LSLText
    Snapshot = 15
    Attachment = 17 # Attachment to an avatar
    Wearable = 18 # Wearable item (actual clothing, body part, etc.)
    Animation = 19
    Gesture = 20
    # Note: AssetType has more granular types like Bodypart, Clothing.
    # InventoryType uses 'Wearable' as a broader category for inventory purposes.
    # Values like 26-28 (Outfit folders) were specific to viewer inventory organization.
    # Values like 4, 5, 11, 12, 13, 14, 16, 21, 22, 23 are not standard inventory types
    # or are obsolete in this context.


class WearableType(enum.Enum):
    """
    Types of wearable items. Corresponds to byte in C#.
    """
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
    Alpha = 13 # Alpha Mask
    Tattoo = 14
    Physics = 15
    Universal = 16 # Obsolete
    Invalid = 255


class PCode(enum.Enum):
    """
    Primitive type codes. Corresponds to byte in C#.
    Used in fields like ProfileShape, PathShape, HoleShape.
    """
    Primitive = 0 # Deprecated
    Box = 0
    Cylinder = 1
    Prism = 2
    Sphere = 3
    Torus = 4
    Tube = 5 # AKA Cylinder with hole
    Ring = 6 # AKA Torus with ProfileBegin/End
    Sculpt = 7
    Mesh = 8
    # Invalid = 255 # No explicit Invalid in C# PCode


class PrimFlags(enum.IntFlag):
    """
    Flags associated with a primitive. Corresponds to uint in C#.
    """
    None_ = 0 # Renamed from None to avoid Python keyword conflict
    ObjectPhysics = 0x00000001 # If on, this object is physical
    ObjectPhantom = 0x00000002 # If on, this object is phantom
    ObjectCastShadows = 0x00000004 # Obsolete, not used
    ObjectMotion = 0x00000008 # If on, this object is not static (deprecated)
    ObjectDieAtEdge = 0x00000010 # If on, object dies if it touches an edge of the region
    ObjectReturnAtEdge = 0x00000020 # If on, object is returned if it touches an edge of the region
    ObjectSandbox = 0x00000040 # If on, object is in a sandbox (cannot affect other objects)
    ObjectBlockGrab = 0x00000080 # If on, this object cannot be grabbed
    ObjectBlockGrabNonOwner = 0x00000100 # If on, this object cannot be grabbed by non-owners
    ObjectYouAvatar = 0x00000200 # Deprecated
    ObjectInventoryEmpty = 0x00000800 # If on, inventory is empty and hidden. If off, inventory may be empty or not.
    ObjectUseNewPhysics = 0x00001000 # If on, use new physics engine (Havok by default)
    ObjectCameraSource = 0x00002000 # If on, this object is a camera source
    ObjectCastMasterShadows = 0x00004000 # If on, this object casts shadows from the master camera
    ObjectSheetBronze = 0x00008000 # If on, this object is made of bronze (used for pathfinding)
    ObjectScriptAlwaysColliding = 0x00010000 # If on, scripts consider this object to always be colliding
    ObjectIsCameraDecoy = 0x00020000 # If on, this object is a camera decoy (hides avatar)
    ObjectTouchKeepsActive = 0x00040000 # If on, touching this object keeps it active
    ObjectTemporaryOnRez = 0x00080000 # If on, this object is temporary when rezzed
    ObjectTemporary = 0x00080000 # Alias for ObjectTemporaryOnRez
    ObjectSelected = 0x01000000 # If on, this object is selected
    ObjectForSale = 0x02000000 # If on, this object is for sale
    ObjectForSaleCopy = 0x04000000 # If on, this object is for sale (copy)
    ObjectForSaleContents = 0x06000000 # If on, this object is for sale (contents)
    ObjectForSaleOriginal = 0x0A000000 # If on, this object is for sale (original)
    ObjectShowInSearch = 0x08000000 # If on, this object is shown in search results
    ObjectPartOfSelection = 0x10000000 # If on, this object is part of a selection
    ObjectTransferProtected = 0x20000000 # Obsolete
    ObjectAllowInventoryDrop = 0x40000000 # If on, inventory can be dropped onto this object
    # ObjectTextureAnim = 0x00000001 (from PrimFlags_SL) - Conflicts with ObjectPhysics, PrimFlags in libomv seems different.
    # Using the values from the provided PrimFlags.cs which seems more extensive.


class Material(enum.Enum):
    """
    Material types for primitives. Corresponds to byte in C#.
    """
    Stone = 0
    Metal = 1
    Glass = 2
    Wood = 3
    Flesh = 4
    Plastic = 5
    Rubber = 6
    Light = 7 # Used for light sources
    # Invalid = 255 # No explicit Invalid in C# Material enum
