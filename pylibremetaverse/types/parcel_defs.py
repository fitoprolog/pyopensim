import enum
import dataclasses
from datetime import datetime, timezone # Added timezone
from .custom_uuid import CustomUUID
from .vector import Vector3
# from .color import Color4 # Not directly used in ParcelInfo base, but could be for related features

# Based on OpenMetaverse.ParcelFlags (OpenMetaverseTypes/ParcelManager.cs)
class ParcelFlags(enum.IntFlag):
    NONE = 0x00000000
    ALLOW_FLY = 0x00000001  # Set if flying is allowed
    ALLOW_SCRIPTS = 0x00000002  # Set if scripts are allowed to run
    ALLOW_LANDMARK = 0x00000008  # Set if landmarks can be created on this parcel
    ALLOW_CREATE_OBJECTS = 0x00000010  # Set if users can create objects on this parcel
    ALLOW_ALL_OBJECT_ENTRY = 0x00000020  # If true, any prim can enter. If false, only owner/group prims.
    ALLOW_GROUP_OBJECT_ENTRY = 0x00000040  # If true, group prims can enter. If false, only owner prims.
    ALLOW_CREATE_GROUP_OBJECTS = 0x00000080  # Set if group members can create objects on this parcel
    ALLOW_OBJECT_ENTRY = 0x000000A0  # Meta flag, equivalent to (ALLOW_ALL_OBJECT_ENTRY | ALLOW_GROUP_OBJECT_ENTRY)
    ALLOW_TERRAFORM = 0x00000100  # Set if parcel owner can terraform the land
    ALLOW_DAMAGE = 0x00000200  # Set if damage is enabled on this parcel
    ALLOW_DEED_TO_GROUP = 0x00000800  # Set if parcel can be deeded to a group
    ALLOW_GROUP_DEED = 0x00000800  # Alias for ALLOW_DEED_TO_GROUP
    FOR_SALE = 0x00001000  # Set if parcel is for sale
    ALLOW_RETURN_OBJECTS = 0x00002000  # Set if owner can return objects on this parcel
    ALLOW_RETURN_GROUP_OBJECTS = 0x00002000  # Alias for ALLOW_RETURN_OBJECTS
    ALLOW_RETURN_NONGROUP_OBJECTS = 0x00002000  # Alias
    RESTRICT_PUSHOBJECT = 0x00004000  # Set if PUSHOBJECT is restricted for non-owners/group-members.
    DENY_ANONYMOUS = 0x00008000  # Prevents anonymous (UUID.Zero) users from interacting with this parcel
    SOUND_LOCAL = 0x00010000  # Restricts spatialized sound to this parcel
    USE_ACCESS_LIST = 0x00080000  # Parcel access is restricted to a list of agents (AccessList)
    USE_GROUP_ACCESS_LIST = 0x00080000 # Alias for USE_ACCESS_LIST
    USE_BAN_LIST = 0x00100000  # Parcel bans are restricted to a list of agents (BanList)
    SHOW_IN_SEARCH = 0x00800000  # Parcel is listed in search (Search->Places)
    MATURE_PUBLISH = 0x00800000 # Alias for SHOW_IN_SEARCH
    MATURE_GENERAL = 0x01000000  # Parcel is rated General
    MATURE_MODERATE = 0x02000000  # Parcel is rated Moderate
    MATURE_ADULT = 0x04000000  # Parcel is rated Adult
    MATURE_PG = 0x01000000 # Alias
    MATURE = 0x02000000 | 0x04000000 # Alias for Moderate or Adult
    BUILD_ENABLED = 0x08000000  # Linden Lab only: if false, building is disabled sim-wide
    SCRIPT_ENABLED = 0x10000000  # Linden Lab only: if false, scripts are disabled sim-wide
    PUBLIC_ON_SEARCH = 0x20000000  # Linden Lab only: if true, parcel is public in search even if access is restricted
    PRIVACY = 0x40000000 # Parcel has privacy settings (voice chat restricted to parcel)

# Based on OpenMetaverse.ParcelCategory
class ParcelCategory(enum.Enum):
    NONE = 0
    LINDEN = 1
    RESIDENTIAL = 2
    COMMERCIAL = 3
    RECREATIONAL = 4 # Corrected from C# (was RECREATION)
    PARK = 5
    ROADSIDE = 6 # Corrected from C# (was ROAD)
    PUBLIC_SPACE = 7 # Corrected from C# (was PUBLIC)
    SKIES = 8 # Added based on common usage
    WATER = 9 # Added
    DANGEROUS = 10 # Added
    UNKNOWN = 255 # Not in C# enum but useful

# Based on OpenMetaverse.ParcelStatus
class ParcelStatus(enum.Enum):
    UNKNOWN = -1 # Not in C# enum but useful default
    LEASED = 0
    LEASE_PENDING = 1
    ABANDONED = 2
    FOR_SALE = 3
    AUCTIONED = 4 # Not in C# enum, but seen in some contexts

@dataclasses.dataclass(slots=True)
class ParcelDwell:
    """Represents the dwell value for a parcel (from ParcelDwellPacket)."""
    local_id: int = 0 # LocalID of the parcel
    parcel_dwell: float = 0.0 # Calculated dwell value

@dataclasses.dataclass(slots=True)
class ParcelInfo:
    """Represents detailed information about a land parcel."""
    local_id: int = -1
    parcel_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    is_group_owned: bool = False
    name: str = ""
    description: str = ""
    area: int = 0
    billable_area: int = 0
    flags: ParcelFlags = ParcelFlags.NONE
    status: ParcelStatus = ParcelStatus.UNKNOWN
    category: ParcelCategory = ParcelCategory.NONE
    sale_price: int = 0
    auction_id: int = 0
    snapshot_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    landing_type: int = 0 # 0=direct, 1=blocked, 2=elsewhere (landing point)
    media_url: str = ""
    media_content_type: str = "" # E.g., "text/html", "image/jpeg"
    media_width: int = 0
    media_height: int = 0
    media_loop: bool = False
    music_url: str = ""
    pass_hours: float = 0.0 # How long a temp pass is valid
    pass_price: int = 0     # Price to buy a temp pass
    auth_buyer_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    claim_date: datetime = dataclasses.field(default_factory=lambda: datetime.fromtimestamp(0, timezone.utc)) # Use epoch as default
    claim_price: int = 0

    # Global position of the SW corner of the parcel
    global_x: float = 0.0
    global_y: float = 0.0
    global_z: float = 0.0 # Average Z of parcel, or ground height at SW corner

    sim_name: str = "" # Name of the simulator this parcel is in
    region_handle: int = 0 # Region handle (ulong in C#)

    # AABB (Axis-Aligned Bounding Box) of the parcel in region coordinates
    min_coord: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    max_coord: Vector3 = dataclasses.field(default_factory=Vector3.ZERO)
    center_coord: Vector3 = dataclasses.field(default_factory=Vector3.ZERO) # Calculated center

    prim_owners: list['ParcelPrimOwnerData'] = dataclasses.field(default_factory=list)

    # TODO: Traffic/Dwell: parcel_dwell from ParcelDwellPacket could be stored here or managed separately
    access_list: list['ParcelAccessEntry'] = dataclasses.field(default_factory=list)


    def __str__(self):
        return (f"ParcelInfo(Name='{self.name}', LocalID={self.local_id}, Area={self.area}, "
                f"Owner={self.owner_id}, Status={self.status.name}, PrimsByOwnerCount={len(self.prim_owners)}, "
                f"AccessEntries={len(self.access_list)})")

class ParcelACLFlags(enum.IntFlag):
    """ Defines specific access rights for an agent on a parcel's access list. """
    ALLOWED = 1 << 0  # Agent is allowed access
    BANNED = 1 << 1   # Agent is banned from access
    GROUP = 1 << 2    # The ID in the entry refers to a group UUID

@dataclasses.dataclass(slots=True)
class ParcelAccessEntry:
    """ Represents an entry in a parcel's access list (allowed or banned). """
    agent_id: CustomUUID  # Agent or Group UUID
    time: int = 0         # Timestamp of when the entry was added/modified (often 0 or unused)
    flags: ParcelACLFlags = dataclasses.field(default_factory=lambda: ParcelACLFlags(0))

@dataclasses.dataclass(slots=True)
class ParcelPrimOwnerData:
    """Represents the count of prims owned by a specific agent on a parcel."""
    owner_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    count: int = 0 # Number of prims owned by OwnerID on this parcel

if __name__ == '__main__':
    print("Testing parcel_defs.py...")
    # ParcelFlags
    flags = ParcelFlags.ALLOW_FLY | ParcelFlags.SHOW_IN_SEARCH
    assert ParcelFlags.ALLOW_FLY in flags
    assert (flags & ParcelFlags.MATURE_PUBLISH) == ParcelFlags.MATURE_PUBLISH # Alias test
    print(f"ParcelFlags example: {flags!r} (Value: {flags.value})")

    # ParcelCategory
    cat = ParcelCategory.RESIDENTIAL
    assert cat.value == 2
    print(f"ParcelCategory example: {cat.name} (Value: {cat.value})")

    # ParcelStatus
    stat = ParcelStatus.FOR_SALE
    assert stat.value == 3
    print(f"ParcelStatus example: {stat.name} (Value: {stat.value})")

    # ParcelDwell
    dwell_info = ParcelDwell(local_id=123, parcel_dwell=456.789)
    assert dwell_info.local_id == 123
    print(f"ParcelDwell example: {dwell_info}")

    # ParcelInfo
    parcel = ParcelInfo(local_id=10, name="My Test Parcel", area=512, owner_id=CustomUUID.random())
    parcel.flags = ParcelFlags.ALLOW_CREATE_OBJECTS | ParcelFlags.USE_ACCESS_LIST
    parcel.min_coord = Vector3(10,10,20)
    parcel.max_coord = Vector3(30,30,25)
    parcel.center_coord = (parcel.min_coord + parcel.max_coord) / 2.0
    print(f"ParcelInfo example: {parcel}")
    assert parcel.name == "My Test Parcel"
    assert ParcelFlags.ALLOW_CREATE_OBJECTS in parcel.flags
    assert parcel.center_coord.X == 20.0
    parcel.prim_owners.append(ParcelPrimOwnerData(owner_id=CustomUUID.random(), count=5))
    assert len(parcel.prim_owners) == 1
    parcel.access_list.append(ParcelAccessEntry(agent_id=CustomUUID.random(), flags=ParcelACLFlags.ALLOWED))
    assert len(parcel.access_list) == 1
    print(f"ParcelInfo example: {parcel}")


    # ParcelPrimOwnerData
    prim_owner_info = ParcelPrimOwnerData(owner_id=CustomUUID.random(), count=100)
    assert prim_owner_info.count == 100
    print(f"ParcelPrimOwnerData example: {prim_owner_info}")

    # ParcelACLFlags and ParcelAccessEntry
    acl_entry_allowed = ParcelAccessEntry(agent_id=CustomUUID.random(), time=int(datetime.now().timestamp()), flags=ParcelACLFlags.ALLOWED)
    acl_entry_banned_group = ParcelAccessEntry(agent_id=CustomUUID.random(), flags=ParcelACLFlags.BANNED | ParcelACLFlags.GROUP)
    assert ParcelACLFlags.ALLOWED in acl_entry_allowed.flags
    assert acl_entry_banned_group.flags & ParcelACLFlags.BANNED
    assert acl_entry_banned_group.flags & ParcelACLFlags.GROUP
    print(f"ParcelAccessEntry (Allowed): {acl_entry_allowed}")
    print(f"ParcelAccessEntry (Banned Group): {acl_entry_banned_group}")


    print("parcel_defs.py tests passed.")
