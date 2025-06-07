# -*- coding: UTF-8 -*-
"""
Definitions for group-related data types.
"""
import enum
import dataclasses
from datetime import datetime, timezone
from typing import List, Dict # For type hinting

from .custom_uuid import CustomUUID
from .enums import AssetType # Assuming AssetType is already in enums.py

@enum.unique
class GroupPowers(enum.IntFlag):
    """
    Defines abilities that can be assigned to group members through roles.
    Ported from OpenMetaverse.GroupPowers (ulong in C#).
    Python's IntFlag supports arbitrary precision, so ulong mapping is fine.
    """
    NONE = 0
    # Role powers
    ALLOW_SET_HOME = (1 << 0)  # Ability to set group land as home
    ALLOW_ACCOUNTABLE = (1 << 1)  # Member is listed in accounting
    JOIN_CHAT = (1 << 2)  # Ability to join group chat sessions
    ALLOW_VOICE_CHAT = (1 << 3)  # Ability to join group voice chat
    ALLOW_MODERATE_CHAT = (1 << 4)  # Ability to moderate group chat
    ALLOW_INVITE = (1 << 5)  # Ability to invite members to the group
    ALLOW_ENROLL = (1 << 6)  # Ability to accept or reject membership applications
    ALLOW_EJECT = (1 << 7)  # Ability to eject members from the group
    ALLOW_CHANGE_IDENTITY = (1 << 8)  # Ability to change group identity (name, charter, insignia)
    ALLOW_CHANGE_ACTIONS = (1 << 9)  # Ability to change group actions (roles, powers)
    ALLOW_LAND_EJECT = (1 << 10) # Ability to eject strangers from group land
    ALLOW_LAND_SALE = (1 << 11) # Ability to sell group-owned land
    ALLOW_LAND_ABANDON = (1 << 12) # Ability to abandon group-owned land
    ALLOW_SET_LAND_INFO = (1 << 13) # Ability to set land info (name, desc, etc.)
    ALLOW_LAND_DEED = (1 << 14) # Ability to deed land to the group
    ALLOW_JOIN_GROUP = (1 << 15) # Ability to join a group that is "closed"
    ALLOW_FIND_GROUP = (1 << 16) # Group is listed in Find->Groups
    ALLOW_PUBLISH = (1 << 17) # Allow group to publish information in Find->Groups
    ALLOW_MEMBERSHIP_OPEN = (1 << 18) # Group is open for anyone to join
    ALLOW_MEMBERSHIP_CLOSED = (1 << 19) # Group is closed, requires invite/application
    ALLOW_MEMBERSHIP_APPLICATION = (1 << 20) # Group allows applications for membership
    CHANGE_OPTIONS = (1 << 21) # Ability to change group options (membership, etc.)
    CHANGE_ROLES = (1 << 22) # Ability to create, delete, and modify roles
    CHANGE_MEMBERS = (1 << 23) # Ability to assign members to roles
    CREATE_ROLES = (1 << 24) # Ability to create new roles
    DELETE_ROLES = (1 << 25) # Ability to delete roles
    ASSIGN_MEMBERS = (1 << 26) # Ability to assign members to existing roles
    REMOVE_MEMBERS = (1 << 27) # Ability to remove members from roles (not eject from group)
    ROLE_PROPERTIES = (1 << 28) # Ability to change role properties (name, desc, title, powers)
    DEED_OBJECTS = (1 << 29) # Ability to deed objects to the group
    OWNER_DEED_OBJECTS = (1 << 30) # Ability to deed objects owned by the group back to the owner
    RETURN_OBJECTS = (1 << 31) # Ability to return objects set to the group
    SET_OBJECT_OWNER = (1 << 32) # Ability to set the owner of group-deeded objects
    ALLOW_LAND_CONTENT_MANAGEMENT = (1 << 33) # Manage parcel content (public, group, owner only)
    ALLOW_LAND_DIVIDE_JOIN = (1 << 34) # Ability to divide and join group-owned land parcels
    ALLOW_LAND_OPTIONS = (1 << 35) # Ability to set parcel options (for sale, for auction, etc.)
    PAY_DIVIDENDS = (1 << 36) # Ability to pay dividends from group funds
    RECEIVE_DIVIDENDS = (1 << 37) # Member is eligible to receive dividends
    # Object powers
    ALLOW_OBJECT_DEED = (1 << 38) # Ability to deed an object to the group
    ALLOW_OBJECT_MANIPULATION = (1 << 39) # Move, copy, rotate, delete group-owned objects
    ALLOW_OBJECT_SET_SALE = (1 << 40) # Set group-owned objects for sale
    # Notice powers
    SEND_NOTICES = (1 << 41) # Ability to send group notices
    RECEIVE_NOTICES = (1 << 42) # Member receives group notices
    # Proposal powers
    CREATE_PROPOSALS = (1 << 43) # Ability to create group proposals
    VOTE_ON_PROPOSALS = (1 << 44) # Ability to vote on group proposals
    # Liabilities powers
    PAY_GROUP_LIABILITIES = (1 << 45) # Ability to pay group liabilities from group funds
    # Experience powers (these are more recent, may not be in all viewers/servers)
    ALLOW_EXPERIENCE_CONTROLS = (1 << 46) # Ability to manage group experiences
    ALLOW_EXPERIENCE_ADMIN = (1 << 47) # Ability to administrate group experiences
    ALLOW_EXPERIENCE_CONTRIBUTE = (1 << 48) # Ability to contribute to group experiences

    # Commonly used combinations
    EVERYONE_POWERS = (JOIN_CHAT | ALLOW_VOICE_CHAT | ALLOW_SET_HOME | RECEIVE_NOTICES | VOTE_ON_PROPOSALS)
    OFFICER_POWERS = (EVERYONE_POWERS | ALLOW_INVITE | ALLOW_EJECT | ALLOW_MODERATE_CHAT | SEND_NOTICES | CREATE_PROPOSALS)
    OWNER_POWERS = 0xFFFFFFFFFFFFFFFF # All powers (represents a ulong max value)

@dataclasses.dataclass(slots=True)
class GroupNoticeInfo:
    notice_id: CustomUUID
    created_date: datetime # Renamed from Timestamp for clarity
    from_name: str
    subject: str
    message: str
    asset_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    asset_type: AssetType = AssetType.Unknown
    item_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # For inventory attachment

@dataclasses.dataclass(slots=True)
class GroupRole:
    role_id: CustomUUID
    name: str = ""
    title: str = "" # This is the title associated with the role
    description: str = ""
    powers: GroupPowers = GroupPowers.NONE
    # members_count: int = 0 # Number of members in this role, might be dynamic

@dataclasses.dataclass(slots=True)
class GroupMember:
    agent_id: CustomUUID
    selected_role_title: str = "" # Member's chosen title from their roles
    contribution: int = 0 # L$ contribution to the group
    is_owner: bool = False # Is this member the group owner
    online_status: bool = False # Requires separate mechanism to update
    # effective_powers: GroupPowers = GroupPowers.NONE # Calculated based on roles, can be computed on demand
    roles: List[CustomUUID] = dataclasses.field(default_factory=list) # List of RoleIDs this member belongs to

@dataclasses.dataclass(slots=True)
class Group:
    id: CustomUUID # Group's UUID
    name: str = ""
    charter: str = ""
    insignia_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Texture UUID for group insignia
    founder_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    member_count: int = 0 # Total members in the group
    contribution: int = 0 # Total L$ contribution to group land
    open_enrollment: bool = False # True if anyone can join (no application/invite needed)
    show_in_list: bool = False # True if group is shown in search/find
    allow_publish: bool = False # True if charter, roles, etc. are publicly visible
    mature_publish: bool = False # True if mature content is published
    owner_role_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Role that owns the group (usually "Owners")

    # Populated on demand or by specific requests
    roles: Dict[CustomUUID, GroupRole] = dataclasses.field(default_factory=dict)
    members: Dict[CustomUUID, GroupMember] = dataclasses.field(default_factory=dict)
    notices: Dict[CustomUUID, GroupNoticeInfo] = dataclasses.field(default_factory=dict)

    # Additional fields from C# Group class that might be useful later
    group_fee: int = 0 # Fee to join the group
    membership_type: int = 0 # Placeholder for C# MembershipType enum (Open, Closed, Application)
    list_in_profile: bool = True # Whether this group is shown in member profiles by default
    money_balance: float = 0.0 # Group's L$ balance (requires specific permissions to view)

    # Calculated property example (can be added if needed)
    # @property
    # def everyone_role_id(self) -> CustomUUID | None:
    #     for role in self.roles.values():
    #         if role.name == "Everyone": # Or check for specific powers
    #             return role.role_id
    #     return None

if __name__ == '__main__':
    print("Testing group_defs.py...")
    # GroupPowers
    owner_powers = GroupPowers.OWNER_POWERS
    assert GroupPowers.ALLOW_LAND_EJECT in owner_powers
    assert GroupPowers.SEND_NOTICES in owner_powers
    print(f"OwnerPowers includes ALLOW_LAND_EJECT: {GroupPowers.ALLOW_LAND_EJECT in owner_powers}")
    print(f"OfficerPowers: {GroupPowers.OFFICER_POWERS!r} (Value: {GroupPowers.OFFICER_POWERS.value})")

    # GroupNoticeInfo
    notice = GroupNoticeInfo(
        notice_id=CustomUUID.random(),
        created_date=datetime.now(timezone.utc),
        from_name="Test User",
        subject="Hello World",
        message="This is a test notice."
    )
    assert notice.subject == "Hello World"
    print(f"GroupNoticeInfo: {notice.subject} from {notice.from_name}")

    # GroupRole
    role_id_test = CustomUUID.random()
    role = GroupRole(
        role_id=role_id_test,
        name="Officers",
        title="Officer",
        description="Group Officers",
        powers=GroupPowers.OFFICER_POWERS
    )
    assert role.name == "Officers"
    assert GroupPowers.ALLOW_INVITE in role.powers
    print(f"GroupRole: {role.name} ({role.title}), Powers: {role.powers!r}")

    # GroupMember
    member_id_test = CustomUUID.random()
    member = GroupMember(
        agent_id=member_id_test,
        selected_role_title="Officer",
        contribution=100,
        roles=[role_id_test]
    )
    assert member.agent_id == member_id_test
    assert role_id_test in member.roles
    print(f"GroupMember: {member.agent_id}, Title: {member.selected_role_title}")

    # Group
    group_id_test = CustomUUID.random()
    group = Group(
        id=group_id_test,
        name="Test Group",
        charter="A group for testing.",
        founder_id=CustomUUID.random(),
        owner_role_id=role_id_test,
        roles={role_id_test: role},
        members={member_id_test: member},
        notices={notice.notice_id: notice}
    )
    assert group.name == "Test Group"
    assert group.roles[role_id_test].name == "Officers"
    assert group.members[member_id_test].contribution == 100
    print(f"Group: {group.name} (ID: {group.id}), Member count: {group.member_count}")
    print(f"  Owner Role: {group.roles[group.owner_role_id].name if group.owner_role_id in group.roles else 'N/A'}")

    print("group_defs.py tests passed.")
