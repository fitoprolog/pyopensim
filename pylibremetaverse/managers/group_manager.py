# -*- coding: UTF-8 -*-
"""
Manages group-related information and interactions.
"""
import logging
import asyncio
import dataclasses
from typing import TYPE_CHECKING, Dict, List, Callable, Optional, Any

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.group_defs import Group, GroupPowers, GroupRole, GroupMember, GroupNoticeInfo
# Assuming PacketType might be needed later for handler registration
# from pylibremetaverse.types.enums import PacketType

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    # from pylibremetaverse.network.simulator import Simulator # If needed for packet sending
    # from pylibremetaverse.network.packets_base import Packet # If handling packets directly

logger = logging.getLogger(__name__)

from pylibremetaverse.types.enums import AssetType, PacketType
from pylibremetaverse.network.packets_group import AgentGroupDataUpdatePacket, AgentSetGroupPacket # Added AgentSetGroupPacket
from pylibremetaverse.network.http_caps_client import HttpCapsClient
from pylibremetaverse.structured_data.osd import OSDMap, OSDArray, OSDUUID, OSDString, OSDBoolean, OSDInteger # Added OSDInteger

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator # If needed for packet sending
    from pylibremetaverse.network.packets_base import Packet # If handling packets directly

logger = logging.getLogger(__name__)

# --- Event Argument Dataclasses ---
@dataclasses.dataclass(slots=True)
class GroupSummary:
    """Summarized information about a group the agent is a member of."""
    group_id: CustomUUID
    name: str
    insignia_id: CustomUUID
    title: str  # Agent's title in this group
    accept_notices: bool
    list_in_profile: bool # Agent's preference for this group (whether it shows on their profile)

@dataclasses.dataclass(slots=True)
class GroupListEventArgs: # Renamed from GroupListUpdatedEventArgs
    """Event arguments for when the agent's list of groups is updated."""
    groups: List[GroupSummary]

@dataclasses.dataclass(slots=True)
class GroupProfileUpdatedEventArgs:
    """Event arguments for when a specific group's profile/details are updated."""
    group: Group # The full Group object with updated details

@dataclasses.dataclass(slots=True)
class ActiveGroupChangedEventArgs:
    """Event arguments for when the agent's active group changes."""
    active_group_id: Optional[CustomUUID]
    active_group_powers: GroupPowers
    active_group_name: Optional[str]
    active_group_title: Optional[str] # Agent's title in the active group

@dataclasses.dataclass(slots=True)
class GroupNoticesUpdatedEventArgs:
    """Event arguments for when group notices are updated."""
    group_id: CustomUUID
    notices: List[GroupNoticeInfo]

@dataclasses.dataclass(slots=True)
class GroupMembersUpdatedEventArgs:
    """Event arguments for when group members are updated."""
    group_id: CustomUUID
    members: List[GroupMember]

@dataclasses.dataclass(slots=True)
class GroupRolesUpdatedEventArgs:
    """Event arguments for when group roles are updated."""
    group_id: CustomUUID
    roles: List[GroupRole]

# --- Handler Types ---
GroupListHandler = Callable[[GroupListEventArgs], None] # Renamed from GroupListUpdatedHandler
GroupProfileUpdatedHandler = Callable[[GroupProfileUpdatedEventArgs], None]
ActiveGroupChangedHandler = Callable[[ActiveGroupChangedEventArgs], None]
GroupNoticesUpdatedHandler = Callable[[GroupNoticesUpdatedEventArgs], None]
GroupMembersUpdatedHandler = Callable[[GroupMembersUpdatedEventArgs], None]
GroupRolesUpdatedHandler = Callable[[GroupRolesUpdatedEventArgs], None]


class GroupManager:
    def __init__(self, client: 'GridClient'):
        self.client: 'GridClient' = client

        self.groups: Dict[CustomUUID, Group] = {}
        self.current_groups_summary: List[GroupSummary] = [] # Changed type

        self.active_group_uuid: Optional[CustomUUID] = None
        self.active_group_powers: GroupPowers = GroupPowers.NONE
        self.active_group_name: Optional[str] = None
        self.active_group_title: Optional[str] = None

        # Event Handlers
        self._group_list_handlers: List[GroupListHandler] = [] # Renamed
        self._group_profile_updated_handlers: List[GroupProfileUpdatedHandler] = []
        self._active_group_changed_handlers: List[ActiveGroupChangedHandler] = []
        self._group_notices_updated_handlers: List[GroupNoticesUpdatedHandler] = []
        self._group_members_updated_handlers: List[GroupMembersUpdatedHandler] = []
        self._group_roles_updated_handlers: List[GroupRolesUpdatedHandler] = []

        if self.client.network:
            reg = self.client.network.register_packet_handler
            # The AgentDataUpdatePacket contains active group ID, powers, name, title.
            # It does NOT contain the list of all groups the agent is in. That's usually from AgentGroupDataUpdate.
            # So, we don't register for AgentDataUpdatePacket here for group *list*.
            # AgentManager handles AgentDataUpdatePacket for active group changes and calls _update_active_group_details.
            reg(PacketType.AgentGroupDataUpdate, self._on_agent_group_data_update_wrapper, is_async=False)
        else:
            logger.error("GroupManager: NetworkManager not available at init for packet handlers.")

    # --- Handler Registration Methods ---
    def register_group_list_handler(self, callback: GroupListHandler): # Renamed
        if callback not in self._group_list_handlers:
            self._group_list_handlers.append(callback)

    def unregister_group_list_handler(self, callback: GroupListHandler): # Renamed
        if callback in self._group_list_handlers:
            self._group_list_handlers.remove(callback)

    def register_group_profile_updated_handler(self, callback: GroupProfileUpdatedHandler):
        if callback not in self._group_profile_updated_handlers:
            self._group_profile_updated_handlers.append(callback)

    def unregister_group_profile_updated_handler(self, callback: GroupProfileUpdatedHandler):
        if callback in self._group_profile_updated_handlers:
            self._group_profile_updated_handlers.remove(callback)

    def register_active_group_changed_handler(self, callback: ActiveGroupChangedHandler):
        if callback not in self._active_group_changed_handlers:
            self._active_group_changed_handlers.append(callback)

    def unregister_active_group_changed_handler(self, callback: ActiveGroupChangedHandler):
        if callback in self._active_group_changed_handlers:
            self._active_group_changed_handlers.remove(callback)

    def register_group_notices_updated_handler(self, callback: GroupNoticesUpdatedHandler):
        if callback not in self._group_notices_updated_handlers:
            self._group_notices_updated_handlers.append(callback)

    def unregister_group_notices_updated_handler(self, callback: GroupNoticesUpdatedHandler):
        if callback in self._group_notices_updated_handlers:
            self._group_notices_updated_handlers.remove(callback)

    def register_group_members_updated_handler(self, callback: GroupMembersUpdatedHandler):
        if callback not in self._group_members_updated_handlers:
            self._group_members_updated_handlers.append(callback)

    def unregister_group_members_updated_handler(self, callback: GroupMembersUpdatedHandler):
        if callback in self._group_members_updated_handlers:
            self._group_members_updated_handlers.remove(callback)

    def register_group_roles_updated_handler(self, callback: GroupRolesUpdatedHandler):
        if callback not in self._group_roles_updated_handlers:
            self._group_roles_updated_handlers.append(callback)

    def unregister_group_roles_updated_handler(self, callback: GroupRolesUpdatedHandler):
        if callback in self._group_roles_updated_handlers:
            self._group_roles_updated_handlers.remove(callback)

    # --- Event Firing Helper Methods ---
    def _fire_group_list_updated(self): # Uses new GroupListEventArgs
        logger.debug(f"Firing group_list_updated with {len(self.current_groups_summary)} groups.")
        # Make a copy of the list of GroupSummary objects to pass to handlers
        args = GroupListEventArgs(groups=list(self.current_groups_summary))
        for handler in self._group_list_handlers: # Renamed handler list
            try: handler(args)
            except Exception as e: logger.error(f"Error in group_list_handler: {e}", exc_info=True)

    def _fire_group_profile_updated(self, group: Group):
        logger.debug(f"Firing group_profile_updated for group '{group.name}' ({group.id}).")
        args = GroupProfileUpdatedEventArgs(group=group)
        for handler in self._group_profile_updated_handlers:
            try: handler(args)
            except Exception as e: logger.error(f"Error in group_profile_updated_handler: {e}", exc_info=True)

    def _fire_active_group_changed(self):
        logger.debug(f"Firing active_group_changed: ID={self.active_group_uuid}, Name='{self.active_group_name}', Title='{self.active_group_title}', Powers={self.active_group_powers!r}")
        args = ActiveGroupChangedEventArgs(
            active_group_id=self.active_group_uuid,
            active_group_powers=self.active_group_powers,
            active_group_name=self.active_group_name,
            active_group_title=self.active_group_title
        )
        for handler in self._active_group_changed_handlers:
            try: handler(args)
            except Exception as e: logger.error(f"Error in active_group_changed_handler: {e}", exc_info=True)

    def _fire_group_notices_updated(self, group_id: CustomUUID, notices: List[GroupNoticeInfo]):
        logger.debug(f"Firing group_notices_updated for group {group_id} with {len(notices)} notices.")
        args = GroupNoticesUpdatedEventArgs(group_id=group_id, notices=notices)
        for handler in self._group_notices_updated_handlers:
            try: handler(args)
            except Exception as e: logger.error(f"Error in group_notices_updated_handler: {e}", exc_info=True)

    def _fire_group_members_updated(self, group_id: CustomUUID, members: List[GroupMember]):
        logger.debug(f"Firing group_members_updated for group {group_id} with {len(members)} members.")
        args = GroupMembersUpdatedEventArgs(group_id=group_id, members=members)
        for handler in self._group_members_updated_handlers:
            try: handler(args)
            except Exception as e: logger.error(f"Error in group_members_updated_handler: {e}", exc_info=True)

    def _fire_group_roles_updated(self, group_id: CustomUUID, roles: List[GroupRole]):
        logger.debug(f"Firing group_roles_updated for group {group_id} with {len(roles)} roles.")
        args = GroupRolesUpdatedEventArgs(group_id=group_id, roles=roles)
        for handler in self._group_roles_updated_handlers:
            try: handler(args)
            except Exception as e: logger.error(f"Error in group_roles_updated_handler: {e}", exc_info=True)

    # --- Packet Handlers & CAP Methods ---
    def _on_agent_group_data_update_wrapper(self, simulator: 'Simulator', packet: 'Packet'): # Added
        if isinstance(packet, AgentGroupDataUpdatePacket):
            self._on_agent_group_data_update(simulator, packet)
        else:
            logger.warning(f"GroupManager: Incorrect packet type {type(packet).__name__} for _on_agent_group_data_update_wrapper")

    def _on_agent_group_data_update(self, source_sim: 'Simulator', packet: AgentGroupDataUpdatePacket): # Added
        if packet.agent_data_block.AgentID != self.client.self.agent_id:
            logger.warning(f"Received AgentGroupDataUpdate for another agent {packet.agent_data_block.AgentID}, ignoring.")
            return

        new_summary_list: List[GroupSummary] = []
        for group_block in packet.group_data_blocks:
            summary = GroupSummary(
                group_id=group_block.GroupID,
                name=group_block.group_name_str,
                insignia_id=group_block.GroupInsigniaID,
                title=group_block.member_title_str,
                accept_notices=group_block.AcceptNotices,
                list_in_profile=group_block.ListInProfile # Assuming ListInProfile is part of packet
            )
            new_summary_list.append(summary)

        self.current_groups_summary = new_summary_list
        logger.info(f"Updated current_groups_summary from AgentGroupDataUpdate packet: {len(self.current_groups_summary)} groups.")
        self._fire_group_list_updated()


    async def request_current_groups_summary(self) -> None: # Added
        """Requests the list of groups the agent is a member of, primarily via CAPS."""
        if not self.client.network.current_sim or not self.client.network.current_sim.caps:
            logger.warning("Cannot request current groups summary: No CAPS available.")
            # Optionally, could trigger a packet-based request here if one exists for this purpose
            return

        cap_url = self.client.network.current_sim.caps.get_cap_url("GroupData") # Or "agt_groups_data.llsd"
        if not cap_url:
            # Fallback for older viewers/sims, or if GroupData is not standard.
            # Some viewers use "AgentGroupData" CAP for a similar purpose, but it's often tied to active group.
            # "AvatarGroups" is another one mentioned in some contexts.
            # For now, we'll stick to "GroupData" as a primary.
            logger.warning("GroupData CAP URL not found. Cannot fetch current groups summary via CAP.")
            # As a fallback, some systems might re-trigger AgentGroupDataUpdate via other means,
            # but that's less direct than a CAP request.
            return

        try:
            logger.debug(f"Requesting current groups summary from CAP: {cap_url}")
            response_osd = await self.client.network.current_sim.caps.caps_get_llsd(cap_url)

            if not isinstance(response_osd, OSDMap):
                logger.error(f"Failed to fetch or parse current groups summary from CAP {cap_url}: Expected OSDMap, got {type(response_osd)}")
                return

            new_summary_list: List[GroupSummary] = []

            # Typical structure: response_osd["groups"] is an OSDArray of OSDMaps
            groups_array = response_osd.get("groups") # Key might vary, "groups" is common
            if isinstance(groups_array, OSDArray):
                for item in groups_array:
                    if isinstance(item, OSDMap):
                        try:
                            group_id = item["groupID"].as_uuid() if "groupID" in item and isinstance(item["groupID"], OSDUUID) else CustomUUID.ZERO
                            name = item["groupName"].as_string() if "groupName" in item and isinstance(item["groupName"], OSDString) else "Unknown Group"
                            insignia_id = item["groupInsigniaID"].as_uuid() if "groupInsigniaID" in item and isinstance(item["groupInsigniaID"], OSDUUID) else CustomUUID.ZERO
                            title = item["memberTitle"].as_string() if "memberTitle" in item and isinstance(item["memberTitle"], OSDString) else ""
                            # AcceptNotices might be under a different key or structure, e.g. part of group powers or a specific flag
                            # For now, assuming it's directly available or defaults.
                            accept_notices = item.get("acceptNotices", OSDBoolean(True)).as_bool() # Default to true if missing
                            # list_in_profile is also often a client-side setting or part of AgentDataUpdate.
                            # Defaulting it here if not found in this specific CAP.
                            list_in_profile = item.get("listInProfile", OSDBoolean(True)).as_bool() # Default to true

                            summary = GroupSummary(
                                group_id=group_id, name=name, insignia_id=insignia_id,
                                title=title, accept_notices=accept_notices, list_in_profile=list_in_profile
                            )
                            new_summary_list.append(summary)
                        except (KeyError, AttributeError, TypeError) as e:
                            logger.warning(f"Skipping group summary item due to parsing error: {e}. Item: {item}")
            else:
                logger.warning(f"CAP response for groups at {cap_url} did not contain a 'groups' OSDArray or was malformed: {response_osd}")

            self.current_groups_summary = new_summary_list
            logger.info(f"Fetched and updated current_groups_summary via CAP: {len(self.current_groups_summary)} groups.")
            self._fire_group_list_updated()

        except Exception as e:
            logger.error(f"Error fetching/processing current groups summary from CAP {cap_url}: {e}", exc_info=True)


    # --- Internal Methods (Agent Active Group Update) ---
    def _update_active_group_details(self, group_id: Optional[CustomUUID],
                                     group_powers_val: Optional[int],
                                     group_name: Optional[str],
                                     group_title: Optional[str]):
        """
        Called by AgentManager when agent's active group data is updated from AgentDataUpdatePacket.
        Updates the GroupManager's cache and fires the active_group_changed event.
        """
        changed = False
        new_powers = GroupPowers(group_powers_val if group_powers_val is not None else 0)

        if self.active_group_uuid != group_id:
            self.active_group_uuid = group_id
            changed = True
        if self.active_group_powers != new_powers:
            self.active_group_powers = new_powers
            changed = True
        if self.active_group_name != group_name: # Name might change even if ID is same (e.g. group name change)
            self.active_group_name = group_name
            changed = True
        if self.active_group_title != group_title: # Title might change
            self.active_group_title = group_title
            changed = True

        # Sync with AgentManager.SelfData
        if self.client.self:
            if getattr(self.client.self, 'active_group_id', CustomUUID.ZERO) != (group_id if group_id else CustomUUID.ZERO):
                setattr(self.client.self, 'active_group_id', group_id if group_id else CustomUUID.ZERO)
            if getattr(self.client.self, 'group_powers', 0) != new_powers.value:
                setattr(self.client.self, 'group_powers', new_powers.value)
            if getattr(self.client.self, 'group_name', "") != (group_name if group_name else ""):
                setattr(self.client.self, 'group_name', group_name if group_name else "")
            if getattr(self.client.self, 'group_title', "") != (group_title if group_title else ""):
                setattr(self.client.self, 'group_title', group_title if group_title else "")

        if changed:
            logger.info(f"Active group details updated: ID={self.active_group_uuid}, Name='{self.active_group_name}', Title='{self.active_group_title}', Powers={self.active_group_powers!r}")
            self._fire_active_group_changed()

    async def request_group_profile(self, group_uuid: CustomUUID) -> None: # Added
        """Requests a detailed profile for a specific group via CAPS."""
        if not self.client.network.current_sim or not self.client.network.current_sim.caps:
            logger.warning(f"Cannot request group profile for {group_uuid}: No CAPS available.")
            return

        cap_url_base = self.client.network.current_sim.caps.get_cap_url("GroupProfile")
        if not cap_url_base:
            logger.warning(f"GroupProfile CAP URL not found. Cannot fetch profile for group {group_uuid}.")
            return

        # Construct the URL: base_url + /?group_id=GROUP_UUID
        # Ensure no double slashes if cap_url_base already ends with one
        request_url = f"{cap_url_base.rstrip('/')}/?group_id={str(group_uuid)}"

        try:
            logger.debug(f"Requesting group profile for {group_uuid} from CAP: {request_url}")
            # C# LibreMetaverse uses an HTTP GET for this specific CAP.
            response_osd = await self.client.network.current_sim.caps.caps_get_llsd(request_url)

            if not isinstance(response_osd, OSDMap):
                logger.error(f"Failed to fetch or parse group profile for {group_uuid} from CAP {request_url}: Expected OSDMap, got {type(response_osd)}")
                return

            # Get or create the Group object
            group = self.groups.get(group_uuid, Group(id=group_uuid))

            # Parse fields from response_osd into group object
            # Using .get(key, default_osd_type).as_type() for safety
            group.name = response_osd.get('name', OSDString(group.name)).as_string()
            group.charter = response_osd.get('charter', OSDString(group.charter)).as_string()
            group.insignia_id = response_osd.get('insignia_id', OSDUUID(group.insignia_id)).as_uuid()
            group.founder_id = response_osd.get('founder_id', OSDUUID(group.founder_id)).as_uuid()
            group.member_count = response_osd.get('member_count', OSDInteger(group.member_count)).as_integer()
            # 'contribution' might not be in profile, more of an accounting detail.
            # group.contribution = response_osd.get('contribution', OSDInteger(group.contribution)).as_integer()
            group.open_enrollment = response_osd.get('open_enrollment', OSDBoolean(group.open_enrollment)).as_boolean()
            group.show_in_list = response_osd.get('show_in_list', OSDBoolean(group.show_in_list)).as_boolean()
            group.allow_publish = response_osd.get('allow_publish', OSDBoolean(group.allow_publish)).as_boolean()
            group.mature_publish = response_osd.get('mature_publish', OSDBoolean(group.mature_publish)).as_boolean()
            group.owner_role_id = response_osd.get('owner_role_id', OSDUUID(group.owner_role_id)).as_uuid()

            # GroupFee and MoneyBalance are less common in basic profile, might need other CAPS/permissions.
            group.group_fee = response_osd.get('group_fee', OSDInteger(group.group_fee)).as_integer()
            # MoneyBalance is highly sensitive, usually not in general profile.
            # group.money_balance = response_osd.get('money_balance', OSDReal(group.money_balance)).as_real()
            group.list_in_profile = response_osd.get('list_in_profile', OSDBoolean(group.list_in_profile)).as_boolean()


            # Parse Roles
            roles_array = response_osd.get('roles') # Key for roles array, e.g., "roles"
            if isinstance(roles_array, OSDArray):
                parsed_roles: Dict[CustomUUID, GroupRole] = {}
                for role_osd_item in roles_array: # OSDArray iteration gives direct items
                    if isinstance(role_osd_item, OSDMap):
                        try:
                            role_id = role_osd_item.get('role_id', OSDUUID(CustomUUID.ZERO)).as_uuid()
                            if role_id == CustomUUID.ZERO:
                                logger.warning(f"Skipping role with ZERO UUID in group {group_uuid}")
                                continue

                            role = GroupRole(role_id=role_id)
                            role.name = role_osd_item.get('name', OSDString("")).as_string()
                            role.title = role_osd_item.get('title', OSDString("")).as_string()
                            role.description = role_osd_item.get('description', OSDString("")).as_string()
                            # Powers are often ulong in C#, OSDInteger should handle large ints.
                            powers_val = role_osd_item.get('powers', OSDInteger(0)).as_integer()
                            role.powers = GroupPowers(powers_val)
                            parsed_roles[role.role_id] = role
                        except (KeyError, AttributeError, TypeError, ValueError) as e:
                            logger.warning(f"Skipping role in group {group_uuid} due to parsing error: {e}. Role OSD: {role_osd_item}")
                group.roles = parsed_roles

            self.groups[group.id] = group # Update cache
            logger.info(f"Fetched and updated profile for group '{group.name}' ({group.id}). Roles: {len(group.roles)}")
            self._fire_group_profile_updated(group) # Fire with the updated Group object

        except Exception as e:
            logger.error(f"Error fetching/processing group profile for {group_uuid} from CAP {request_url}: {e}", exc_info=True)


    # --- Public API Methods (stubs for now) ---
    async def activate_group(self, group_uuid: CustomUUID) -> None:
        """Sets the agent's active group tag."""
        if not self.client.self or not self.client.self.logged_in:
            logger.warning("Cannot activate group: Agent not logged in or IDs not available.")
            return
        if not self.client.network.current_sim:
            logger.warning("Cannot activate group: Not connected to a simulator.")
            return

        # Ensure the AgentSetGroupPacket has its PACKET_ID correctly set from PacketType
        # This should be handled by setting the correct PacketType in its __init__ call in packets_group.py
        # For now, we assume it's implicitly PacketType.AgentSetGroup

        # Check if AgentSetGroupPacket's __init__ needs explicit PacketType
        # If AgentSetGroupPacket's super().__init__ uses Unhandled, it must be overridden.
        # Packets should set their type correctly. If AgentSetGroupPacket was defined with Unhandled,
        # it should be fixed there, or explicitly set here:
        # set_group_packet = AgentSetGroupPacket(...)
        # set_group_packet.type = PacketType.AgentSetGroup
        # However, the packet definition itself should handle this.

        set_group_packet = AgentSetGroupPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            group_id=group_uuid
        )
        # Reliability is set in AgentSetGroupPacket's __init__

        await self.client.network.send_packet(set_group_packet, self.client.network.current_sim)
        logger.info(f"Sent AgentSetGroupPacket for GroupID: {group_uuid}.")
        # Server will respond with AgentDataUpdate, which will trigger _update_active_group_details
        # and subsequently the _fire_active_group_changed event.

    # async def request_group_profile(self, group_id: CustomUUID): ... # Implemented in previous step
    # async def request_group_members(self, group_id: CustomUUID): ...
    # async def request_group_notices(self, group_id: CustomUUID): ...
    # async def activate_group(self, group_id: CustomUUID): ... # Sets agent's active group tag
    # async def set_group_acceptance(self, group_id: CustomUUID, accept_notices: bool): ... # Opt-in/out of notices
    # ... other methods for group invites, ejects, role changes, etc.

    def get_group_profile_from_cache(self, group_id: CustomUUID) -> Optional[Group]:
        """Gets a group's full profile from the local cache, if available."""
        return self.groups.get(group_id)

if __name__ == '__main__':
    print("GroupManager structure defined.")

    class MockSelfData: # Simplified SelfData for testing
        active_group_id: CustomUUID = CustomUUID.ZERO
        group_powers: int = 0
        group_name: str = ""
        group_title: str = ""

    class MockClientForGroup:
        self: MockSelfData = MockSelfData()
        # network = None # Mock if packet handlers were being registered

    mock_client = MockClientForGroup()
    gm = GroupManager(mock_client)

    test_group_id_val = CustomUUID.random()
    test_group_name_val = "Test Group Alpha"
    test_group_title_val = "Officer"
    test_group_powers_obj = GroupPowers.ALLOW_INVITE | GroupPowers.JOIN_CHAT
    test_group_powers_int_val = test_group_powers_obj.value


    def handler_active_group_changed_test(args: ActiveGroupChangedEventArgs):
        print(f"Event Handler - Active Group Changed: ID={args.active_group_id}, Name='{args.active_group_name}', Title='{args.active_group_title}', Powers={args.active_group_powers!r}")

    gm.register_active_group_changed_handler(handler_active_group_changed_test)

    print("\nTesting update 1 (setting active group):")
    gm._update_active_group_details(test_group_id_val, test_group_powers_int_val, test_group_name_val, test_group_title_val)
    assert gm.active_group_uuid == test_group_id_val
    assert gm.active_group_powers == test_group_powers_obj
    assert gm.active_group_name == test_group_name_val
    assert gm.active_group_title == test_group_title_val
    assert mock_client.self.active_group_id == test_group_id_val
    assert mock_client.self.group_powers == test_group_powers_int_val
    assert mock_client.self.group_name == test_group_name_val
    assert mock_client.self.group_title == test_group_title_val

    print("\nTesting update 2 (deactivating group):")
    gm._update_active_group_details(None, GroupPowers.NONE.value, None, None)
    assert gm.active_group_uuid is None
    assert gm.active_group_powers == GroupPowers.NONE
    assert gm.active_group_name is None
    assert gm.active_group_title is None
    assert mock_client.self.active_group_id == CustomUUID.ZERO
    assert mock_client.self.group_powers == GroupPowers.NONE.value
    assert mock_client.self.group_name == ""
    assert mock_client.self.group_title == ""

    print("\nGroupManager conceptual tests passed.")
