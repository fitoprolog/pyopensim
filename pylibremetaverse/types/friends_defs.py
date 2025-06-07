from enum import IntFlag
import dataclasses
from .custom_uuid import CustomUUID

class FriendRights(IntFlag):
    """
    Represents permissions granted to/from a friend.
    Directly maps to C# LibreMetaverse.FriendRights enum values.
    """
    NONE = 0x00
    CAN_SEE_ONLINE = 0x01       # This friend can see your online status
    CAN_SEE_ON_MAP = 0x02       # This friend can see you on the map
    CAN_MODIFY_OBJECTS = 0x04   # This friend can modify your objects
    ALL = CAN_SEE_ONLINE | CAN_SEE_ON_MAP | CAN_MODIFY_OBJECTS # Convenience for all rights

@dataclasses.dataclass(slots=True)
class FriendInfo:
    """Represents information about a friend."""
    uuid: CustomUUID
    name: str = ""  # Populated from IMs, Group lookups, or other sources

    # Rights THEY have granted to US (agent)
    their_rights_given_to_us: FriendRights = FriendRights.NONE

    # Rights WE (agent) have granted to THEM
    our_rights_given_to_them: FriendRights = FriendRights.NONE

    online: bool = False # Presence status, updated via presence system or IMs

    def __str__(self) -> str:
        return (f"FriendInfo(uuid={self.uuid}, name='{self.name}', "
                f"online={self.online}, "
                f"their_rights_to_us={self.their_rights_given_to_us!r}, " # Use !r for IntFlag full name
                f"our_rights_to_them={self.our_rights_given_to_them!r})")

    def __repr__(self) -> str:
        return (f"<FriendInfo name='{self.name}' uuid={self.uuid} online={self.online} "
                f"their_rights={self.their_rights_given_to_us.value} our_rights={self.our_rights_given_to_them.value}>")

@dataclasses.dataclass(slots=True)
class BuddyListEntry:
    """
    Represents an entry in the buddy list received at login from LoginResponseData.
    The field names map to the C# struct OpenMetaverse.Login.BuddyListEntry.
    """
    buddy_id: CustomUUID    # UUID of the friend
    buddy_rights_given: int # Rights they have given to us (their_rights_given_to_us)
    buddy_rights_has: int   # Rights we have given to them (our_rights_given_to_them)

    def get_their_rights_to_us(self) -> FriendRights:
        """Returns the rights this friend has granted to us."""
        return FriendRights(self.buddy_rights_given)

    def get_our_rights_to_them(self) -> FriendRights:
        """Returns the rights we have granted to this friend."""
        return FriendRights(self.buddy_rights_has)

if __name__ == '__main__':
    print("Testing friends_defs.py...")

    # Test FriendRights
    rights_can_see = FriendRights.CAN_SEE_ONLINE | FriendRights.CAN_SEE_ON_MAP
    print(f"Rights combination: {rights_can_see!r} (Value: {rights_can_see.value})")
    assert FriendRights.CAN_SEE_ONLINE in rights_can_see
    assert FriendRights.CAN_SEE_ON_MAP in rights_can_see
    assert FriendRights.CAN_MODIFY_OBJECTS not in rights_can_see
    assert (rights_can_see & FriendRights.CAN_SEE_ONLINE) == FriendRights.CAN_SEE_ONLINE
    assert FriendRights.ALL == (FriendRights.CAN_SEE_ONLINE | FriendRights.CAN_SEE_ON_MAP | FriendRights.CAN_MODIFY_OBJECTS)

    # Test FriendInfo
    friend_uuid = CustomUUID()
    info = FriendInfo(
        uuid=friend_uuid,
        name="Test Friend",
        their_rights_given_to_us=FriendRights.CAN_SEE_ONLINE,
        our_rights_given_to_them=FriendRights.CAN_MODIFY_OBJECTS | FriendRights.CAN_SEE_ON_MAP,
        online=True
    )
    print(f"FriendInfo: {info}")
    assert info.uuid == friend_uuid
    assert info.online is True
    assert FriendRights.CAN_SEE_ONLINE in info.their_rights_given_to_us
    assert FriendRights.CAN_MODIFY_OBJECTS in info.our_rights_given_to_them

    # Test BuddyListEntry
    # buddy_rights_has: rights WE have given THEM
    # buddy_rights_given: rights THEY have given US
    raw_our_rights_to_them = FriendRights.CAN_MODIFY_OBJECTS.value | FriendRights.CAN_SEE_ONLINE.value
    raw_their_rights_to_us = FriendRights.CAN_SEE_ON_MAP.value

    buddy_entry = BuddyListEntry(
        buddy_id=friend_uuid,
        buddy_rights_has=raw_our_rights_to_them,     # We give them modify and see online
        buddy_rights_given=raw_their_rights_to_us    # They give us see on map
    )
    print(f"BuddyListEntry: ID={buddy_entry.buddy_id}, RawOurRightsToThem={buddy_entry.buddy_rights_has}, RawTheirRightsToUs={buddy_entry.buddy_rights_given}")

    our_rights = buddy_entry.get_our_rights_to_them()
    their_rights = buddy_entry.get_their_rights_to_us()

    print(f"Processed Our Rights to Them: {our_rights!r}")
    print(f"Processed Their Rights to Us: {their_rights!r}")

    assert FriendRights.CAN_MODIFY_OBJECTS in our_rights
    assert FriendRights.CAN_SEE_ONLINE in our_rights
    assert FriendRights.CAN_SEE_ON_MAP not in our_rights # Correct

    assert FriendRights.CAN_SEE_ON_MAP in their_rights
    assert FriendRights.CAN_SEE_ONLINE not in their_rights # Correct

    print("friends_defs.py tests passed.")
