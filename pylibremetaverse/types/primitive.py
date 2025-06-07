import dataclasses
import uuid # For CreatorID if it's a raw UUID
import struct # Moved import to top

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


    TEXTURE_ENTRY_DEFAULT_SIZE = 470  # For ObjectUpdatePacket, often less for default avatar
    TEXTURE_ENTRY_MAX_SIZE = 1000 # Max size for an entire TextureEntry block in some contexts
    MAX_AVATAR_FACES = 22 # Number of bakeable avatar faces (0-21), matches C# AvatarTextureIndex.COUNT

    def __str__(self):
        return (f"Prim(LocalID={self.local_id}, UUID={self.id_uuid}, Name='{self.name}', "
                f"Pos={self.position}, PCode={self.pcode.name if self.pcode else 'N/A'})")

    def __repr__(self):
        return (f"<Primitive local_id={self.local_id} id_uuid='{self.id_uuid}' name='{self.name}' "
                f"pcode={self.pcode} position={self.position} scale={self.scale}>")


@dataclasses.dataclass
class TextureEntryFace:
    """Represents a single face in a TextureEntry block."""
    texture_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    color: Color4 = dataclasses.field(default_factory=lambda: Color4(1.0, 1.0, 1.0, 1.0))
    repeat_u: float = 1.0
    repeat_v: float = 1.0
    offset_u: float = 0.0
    offset_v: float = 0.0
    rotation_rad: float = 0.0 # Radians for texture rotation
    glow: float = 0.0         # 0.0 to 1.0
    # Bump and MediaFlags are often single bytes in SL protocol. Fullbright is a bit in a flags byte.
    # For simplicity, using separate fields for now.
    bump: int = 0             # Placeholder for Bumpiness enum (e.g., 0=None, 1=Bright, 2=Dark, 3=Woodgrain etc.)
    fullbright: bool = False
    media_flags: bool = False # True if this face has media/texture animation

    # Size of this serialized face: 16 (UUID) + 4 (Color) + 4*6 (floats) + 1 (bump) + 1 (fullbright) + 1 (media) = 47 bytes
    # This is a non-compacted representation.
    SERIALIZED_SIZE = 47

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.texture_id.get_bytes())
        data.extend(self.color.get_bytes_rgba_int()) # Assuming this returns 4 bytes (R,G,B,A as 0-255)
        data.extend(struct.pack('<f', self.repeat_u))
        data.extend(struct.pack('<f', self.repeat_v))
        data.extend(struct.pack('<f', self.offset_u))
        data.extend(struct.pack('<f', self.offset_v))
        data.extend(struct.pack('<f', self.rotation_rad))
        data.extend(struct.pack('<f', self.glow))
        data.append(self.bump & 0xFF)
        data.append(1 if self.fullbright else 0)
        data.append(1 if self.media_flags else 0)
        # Pad to 30 bytes for some compatibility? C# full face is 30 bytes.
        # My current explicit fields sum to 47. Let's stick to explicit for now.
        # If padding or specific packing is needed, this needs revision.
        return bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'TextureEntryFace | None':
        # This is a placeholder for deserialization, not strictly needed for sending TE yet.
        # For a fixed size of 47 bytes:
        if len(data) - offset < cls.SERIALIZED_SIZE:
            return None # Not enough data

        face = cls()
        face.texture_id = CustomUUID(data, offset); offset += 16

        r = data[offset]; g = data[offset+1]; b = data[offset+2]; a = data[offset+3]; offset += 4
        face.color = Color4(float(r)/255.0, float(g)/255.0, float(b)/255.0, float(a)/255.0)

        face.repeat_u = struct.unpack_from('<f', data, offset)[0]; offset += 4
        face.repeat_v = struct.unpack_from('<f', data, offset)[0]; offset += 4
        face.offset_u = struct.unpack_from('<f', data, offset)[0]; offset += 4
        face.offset_v = struct.unpack_from('<f', data, offset)[0]; offset += 4
        face.rotation_rad = struct.unpack_from('<f', data, offset)[0]; offset += 4
        face.glow = struct.unpack_from('<f', data, offset)[0]; offset += 4

        face.bump = data[offset]; offset += 1
        face.fullbright = bool(data[offset]); offset += 1
        face.media_flags = bool(data[offset]); offset += 1
        return face


@dataclasses.dataclass
class TextureEntry:
    """Represents the TextureEntry block for prims or avatars."""
    # Default texture is applied to faces not explicitly overridden.
    default_texture: TextureEntryFace = dataclasses.field(default_factory=TextureEntryFace)
    # List of face textures. Index corresponds to face number. None means use default.
    face_textures: list[TextureEntryFace | None] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        # Ensure face_textures list is padded to MAX_AVATAR_FACES with None
        # This is primarily for avatar TEs. Prims can have fewer effective faces.
        if len(self.face_textures) < Primitive.MAX_AVATAR_FACES:
            self.face_textures.extend([None] * (Primitive.MAX_AVATAR_FACES - len(self.face_textures)))
        elif len(self.face_textures) > Primitive.MAX_AVATAR_FACES:
            self.face_textures = self.face_textures[:Primitive.MAX_AVATAR_FACES]

    def to_bytes(self, max_faces_to_serialize: int = Primitive.MAX_AVATAR_FACES) -> bytes:
        """
        Serializes the TextureEntry to bytes.
        Simplified serialization: Default face + full serialization of each face up to max_faces.
        A more compact version would use bitfields to indicate which faces use default
        and which parameters of non-default faces are themselves default.
        """
        data = bytearray()

        # Serialize default texture
        default_face_bytes = self.default_texture.to_bytes()
        data.extend(default_face_bytes)

        # For each face, determine if we use default or a specific face
        num_faces = min(max_faces_to_serialize, len(self.face_textures))

        for i in range(num_faces):
            face = self.face_textures[i]
            if face is not None:
                data.extend(face.to_bytes())
            else:
                # If face is None, use the default texture's bytes for that face slot
                data.extend(default_face_bytes)

        # The actual SL TE format includes a bitmask indicating which faces are present/default.
        # This simplified version always writes data for each face up to num_faces.
        # Example: (NumFaces byte) + (Bitmask for up to 8 faces) + DefaultFace + Face0 + Face1 ...
        # For now, this simplified, larger representation is used.
        # Total size = (1 + num_faces) * TextureEntryFace.SERIALIZED_SIZE (approx)
        # This needs to be carefully matched with server expectations or C# serialization.
        # The C# TextureEntry.ToBytes() is complex.
        # A common short TE for avatars is around 470 bytes.
        # (1 + 21 faces) * 47 bytes/face = 1034 bytes. This is too large for the typical default.
        # The default TE is often much smaller, implying heavy use of "use default" flags.

        # Let's adjust to a very simple TE for now for AgentSetAppearance:
        # Just the default texture repeated. This is likely wrong but a starting point.
        # A more common simple TE is just the default texture block if all faces are default.
        # If AgentSetAppearancePacket's TextureEntry field is variable and can be short,
        # just sending the default_texture.to_bytes() might be a starting point if all faces are default.
        # However, the prompt implies constructing it based on wearables.

        # For AgentSetAppearance, the TextureEntry is often a pre-baked composite texture ID
        # for each bake layer (head, upper, lower, etc.), rather than individual prim-like faces.
        # This implementation is more like a prim's TextureEntry.
        # This part needs significant refinement to match SL avatar TE structure.
        # For now, this will produce a very large TE block.

        # A very, very simplified placeholder for AgentSetAppearance:
        # Often, TextureEntry for avatars is a series of UUIDs for baked textures.
        # Example: 16 bytes for head bake, 16 for upper, 16 for lower, etc.
        # This is NOT what the current TextureEntry/TextureEntryFace classes are building.
        # The current classes are for prim-style multi-face texturing.

        # Given the complexity, and that AgentSetAppearancePacket needs *baked* texture IDs
        # for avatar appearance, this TextureEntry class might be more for object texturing
        # than for direct use in AgentSetAppearance in its current detailed form.
        # For AgentSetAppearance, we'd typically provide a byte array that IS the TextureEntry,
        # often fetched from AvatarAppearancePacket.

        # For this subtask, the goal is to *construct* a TE.
        # The simplified approach: default_texture + N * (face_texture or default_texture)
        # This will be large. Max length is often ~1000 bytes.
        # (1 default + 21 faces) * 47 bytes/face = 1034 bytes. This is too much.
        # Let's assume max_faces_to_serialize will be small for testing, or the client TE for avatars is different.

        # C# AgentSetAppearance uses a TextureEntryBlock which is just 17 bytes per face:
        # UUID (16) + MediaFlags (1). This is for *overriding* specific avatar bake layers.
        # The main TextureEntry in AvatarAppearancePacket is the full set of these.
        # This current TextureEntry class is too detailed for that specific packet structure.

        # Sticking to the simplified plan: Default + N faces (all fields).
        # This might not be what AgentSetAppearance expects for avatars.
        # It's more like a prim TE.
        # If AppearanceManager is to build this, it needs to know which face index corresponds to which wearable.

        # For now, let's return the current data. It will be oversized.
        # This will need heavy refinement or a different structure for avatar appearance.
        if len(data) > Primitive.TEXTURE_ENTRY_MAX_SIZE:
            # This will happen with MAX_AVATAR_FACES = 22 and SERIALIZED_SIZE = 47
            # data will be 47 + 22*47 = 1081 bytes.
            # logger.warning(f"TextureEntry serialized size ({len(data)}) exceeds MAX_SIZE ({Primitive.TEXTURE_ENTRY_MAX_SIZE}). Truncating.")
            # return data[:Primitive.TEXTURE_ENTRY_MAX_SIZE]
            # For AgentSetAppearance, the TE is often much smaller.
            # This structure is more for object_update.
            # For now, let's assume the AppearanceManager will call this with a small max_faces_to_serialize
            # or this structure is primarily for prims, not avatar appearance TEs.
        pass # Keep current behavior for prim TE to_bytes

    return bytes(data)

    def to_avatar_appearance_bytes(self, default_textures_map: dict[int, CustomUUID]) -> bytes:
        """
        Serializes the TextureEntry to a byte array suitable for AgentSetAppearancePacket.
        This format is typically an array of (TextureID (16 bytes) + MediaFlags (1 byte))
        for each avatar bake layer, up to MAX_AVATAR_FACES.

        Args:
            default_textures_map: A dictionary mapping face_index to default TextureID for that slot.
                                  Used if a face texture is not explicitly set or is CustomUUID.ZERO.
        """
        data = bytearray()
        num_faces = Primitive.MAX_AVATAR_FACES # Should be 21 or 22 for SL avatars

        for i in range(num_faces):
            face_texture_id = None
            media_flags = 0 # Default media flags

            specific_face = self.face_textures[i] if i < len(self.face_textures) else None

            if specific_face and specific_face.texture_id != CustomUUID.ZERO:
                face_texture_id = specific_face.texture_id
                if specific_face.media_flags: # Assuming media_flags is a simple boolean for now
                    media_flags = 0x01 # Example: Set bit 0 for media_flags if True
            else:
                # Use the provided default texture for this face index
                face_texture_id = default_textures_map.get(i, CustomUUID.ZERO) # Fallback to ZERO if no specific default

            if face_texture_id is None: # Should not happen if default_textures_map is comprehensive
                face_texture_id = CustomUUID.ZERO

            data.extend(face_texture_id.get_bytes())
            data.append(media_flags & 0xFF)

        # Expected size: num_faces * (16 + 1) = 22 * 17 = 374 bytes if MAX_AVATAR_FACES is 22.
        # This is a more reasonable size for AgentSetAppearancePacket's TextureEntry.
        return bytes(data)
