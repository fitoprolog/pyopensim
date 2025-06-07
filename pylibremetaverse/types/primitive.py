import dataclasses
import uuid # For CreatorID if it's a raw UUID
from .custom_uuid import CustomUUID
from .vector import Vector3
from .quaternion import Quaternion
from .color import Color4
from .enums import PrimFlags, PCode, Material, ClickAction, PathCurve, ProfileCurve, SaleType # Added SaleType

@dataclasses.dataclass
class Primitive:
    """
    Represents an in-world primitive object.
    This is a basic version and will be expanded as more ObjectUpdate fields are handled.
    """
    # Core Identifiers
    local_id: int = 0 # Local ID within the simulator
    id_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Full UUID of the prim
    parent_id: int = 0 # LocalID of the parent object, 0 if no parent (root prim of an object)

    # Basic Properties often included in ObjectUpdate
    flags: PrimFlags = PrimFlags.None_ # PrimFlags, e.g., Physics, Phantom, CastShadows
    pcode: PCode = PCode.Primitive # Type of primitive (Box, Sphere, etc.)

    # Transform
    position: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    rotation: Quaternion = dataclasses.field(default_factory=Quaternion.Identity)
    scale: Vector3 = dataclasses.field(default_factory=lambda: Vector3(0.5, 0.5, 0.5)) # Default size
    velocity: Vector3 = dataclasses.field(default_factory=Vector3.ZERO) # For physics
    acceleration: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    angular_velocity: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)

    # Appearance and Interaction (Simplified for now)
    material: Material = Material.STONE # Material type
    click_action: ClickAction = ClickAction.TOUCH # What happens on click

    # TextureEntry related (Full TE is complex, placeholder for now)
    # texture_entry_bytes: bytes | None = None
    # For ObjectUpdate, Color is often part of ObjectData instead of TE directly for base color
    color: Color4 = dataclasses.field(default_factory=lambda: Color4(0.5, 0.5, 0.5, 1.0)) # Default grey

    # Text and Name/Description (Often in NameValue field of ObjectUpdate)
    name: str = ""
    description: str = ""
    text: str = "" # Text displayed on prim (e.g. floating text)

    # Ownership (Placeholders)
    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    group_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)

    # Other common fields (can be added as stubs or when their data blocks are parsed)
    # e.g., Sound, Light, Particles, ExtraParams, Pathfinding, PhysicsShapeType etc.
    crc: int = 0 # u32, often from ObjectUpdate CRC field
    state: int = 0 # u8, often used for attachment point or other state info

    # Path and Profile parameters
    path_curve: PathCurve = PathCurve.LINE
    profile_curve: ProfileCurve = ProfileCurve.CIRCLE
    path_begin: float = 0.0; path_end: float = 0.0
    profile_begin: float = 0.0; profile_hollow: float = 0.0

    texture_entry_bytes: bytes | None = None
    text_color: Color4 = dataclasses.field(default_factory=lambda: Color4(1.0,1.0,1.0,1.0))
    media_url: str = ""

    # Ownership and Permissions
    creator_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # From properties
    # owner_id: CustomUUID = CustomUUID.ZERO # Already exists
    # group_id: CustomUUID = CustomUUID.ZERO # Already exists
    last_owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # From properties
    base_mask: int = 0 # PermissionMask (u32)
    owner_mask: int = 0 # PermissionMask (u32)
    group_mask: int = 0 # PermissionMask (u32)
    everyone_mask: int = 0 # PermissionMask (u32)
    next_owner_mask: int = 0 # PermissionMask (u32)

    # Sale and Category
    ownership_cost: int = 0 # s32
    sale_price: int = 0     # s32
    sale_type: SaleType = SaleType.NOT_FOR_SALE # u8
    category: int = 0       # u32, inventory category

    # Click action related text (from NameValue parsing, refined)
    touch_text: str = "" # Part of NameValue in properties
    sit_text: str = ""   # Part of NameValue in properties


    TEXTURE_ENTRY_DEFAULT_SIZE = 470
    TEXTURE_ENTRY_MAX_SIZE = 1000 # As per C# ObjectAddPacket.TEXTURE_ENTRY_MAX_SIZE

    def __str__(self):
        return (f"Prim(LocalID={self.local_id}, UUID={self.id_uuid}, Name='{self.name}', "
                f"Pos={self.position}, PCode={self.pcode.name if self.pcode else 'N/A'})")

    def __repr__(self):
        return (f"<Primitive local_id={self.local_id} id_uuid='{self.id_uuid}' name='{self.name}' "
                f"pcode={self.pcode} position={self.position} scale={self.scale}>")
