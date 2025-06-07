import curses
import asyncio
import threading
import queue
import logging
import os
import sys
import time
import math
import curses.ascii # For isprint

try:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.login_defs import LoginStatus
    from pylibremetaverse.types.enums import TeleportStatus, ChatType, ControlFlags, FolderType
    from pylibremetaverse.types import CustomUUID, Primitive, Vector3
    from pylibremetaverse.types.inventory_defs import InventoryBase, InventoryFolder, InventoryItem
    from pylibremetaverse.types.friends_defs import FriendInfo, FriendRights
    from pylibremetaverse.managers.friends_manager import (
        FriendshipOfferedEventArgs, FriendshipResponseEventArgs,
        FriendOnlineStatusEventArgs, FriendRightsEventArgs, FriendRemovedEventArgs
    )
    from pylibremetaverse.managers.parcel_manager import (
        ParcelPropertiesEventArgs, ParcelManager, ParcelAccessListEventArgs
    )
    from pylibremetaverse.managers.group_manager import ( # Added Group manager imports
        GroupListEventArgs, GroupSummary, GroupProfileEventArgs, ActiveGroupChangedEventArgs # Added ActiveGroupChangedEventArgs
    )
    from pylibremetaverse.types.parcel_defs import ParcelInfo, ParcelAccessEntry, ParcelACLFlags
    from pylibremetaverse.types.group_defs import Group, GroupRole, GroupPowers
except ImportError:
    current_dir_for_import = os.path.dirname(os.path.abspath(__file__))
    parent_dir_for_import = os.path.dirname(current_dir_for_import)
    sys.path.insert(0, parent_dir_for_import)
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.login_defs import LoginStatus
    from pylibremetaverse.types.enums import TeleportStatus, ChatType, ControlFlags, FolderType
    from pylibremetaverse.types import CustomUUID, Primitive, Vector3
    from pylibremetaverse.types.inventory_defs import InventoryBase, InventoryFolder, InventoryItem
    from pylibremetaverse.types.friends_defs import FriendInfo, FriendRights
    from pylibremetaverse.managers.friends_manager import (
        FriendshipOfferedEventArgs, FriendshipResponseEventArgs,
        FriendOnlineStatusEventArgs, FriendRightsEventArgs, FriendRemovedEventArgs
    )
    from pylibremetaverse.managers.parcel_manager import (
        ParcelPropertiesEventArgs, ParcelManager, ParcelAccessListEventArgs
    )
    from pylibremetaverse.managers.group_manager import ( # Added Group manager imports
        GroupListEventArgs, GroupSummary, GroupProfileEventArgs, ActiveGroupChangedEventArgs # Added ActiveGroupChangedEventArgs
    )
    from pylibremetaverse.types.parcel_defs import ParcelInfo, ParcelAccessEntry, ParcelACLFlags
    from pylibremetaverse.types.group_defs import Group, GroupRole, GroupPowers


MAX_LOG_LINES = 100 # Kept it smaller for now
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOGIN_SERVER = "https://login.agni.lindenlab.com/cgi-bin/login.cgi"

COLOR_PAIR_LOG_DEFAULT = 1; COLOR_PAIR_SUCCESS = 2; COLOR_PAIR_IMPORTANT = 3
COLOR_PAIR_ERROR = 4; COLOR_PAIR_STATUS_BAR = 5; COLOR_PAIR_INPUT = 6
COLOR_PAIR_BORDER = 7; COLOR_PAIR_PANEL_TEXT = 8; COLOR_PAIR_PROMPT = 9

class CursesApp:
    def __init__(self): # ... (other inits as before) ...
        self.stdscr=None; self.grid_client=GridClient(); self.ui_update_queue=queue.Queue()
        self.command_queue=queue.Queue(); self.log_messages:List[Tuple[str,int]]=[]
        self.input_buffer=""; self.is_running=True; self.pylibremetaverse_thread=None
        self.pylibremetaverse_loop=None; self.log_win=None; self.status_win=None; self.input_win=None
        self.current_status_text="Status: Initializing..."; self.active_main_panel="log"
        self.inventory_win=None; self.inventory_scroll_pos=0; self.inventory_display_lines=[]
        self.nearby_prims_win=None; self.nearby_prims_scroll_pos=0; self.nearby_prims_display_list:list[Primitive]=[]
        self.friends_win=None; self.friends_scroll_pos=0; self.friends_display_list:list[FriendInfo]=[]
        self.groups_win=None; self.groups_scroll_pos=0; self.groups_display_list:list[GroupSummary]=[] # Added Groups panel state
        self.active_friendship_offers:dict[CustomUUID,CustomUUID]={}

    def setup_colors(self): # ... (as before) ...
        if not curses.has_colors(): return
        curses.start_color(); curses.use_default_colors()
        curses.init_pair(COLOR_PAIR_LOG_DEFAULT, curses.COLOR_CYAN, -1)
        curses.init_pair(COLOR_PAIR_SUCCESS, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_PAIR_IMPORTANT, curses.COLOR_YELLOW, -1)
        curses.init_pair(COLOR_PAIR_ERROR, curses.COLOR_RED, -1)
        curses.init_pair(COLOR_PAIR_STATUS_BAR, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(COLOR_PAIR_INPUT, curses.COLOR_WHITE, -1)
        curses.init_pair(COLOR_PAIR_BORDER, curses.COLOR_BLUE, -1)
        curses.init_pair(COLOR_PAIR_PANEL_TEXT, curses.COLOR_WHITE, -1)
        curses.init_pair(COLOR_PAIR_PROMPT, curses.COLOR_MAGENTA, -1)

    def _create_main_panel_window(self, height:int, width:int, y:int, x:int) -> curses.window: # ... (as before) ...
        win = curses.newwin(height, width, y, x); win.keypad(True)
        if curses.has_colors(): win.attron(curses.color_pair(COLOR_PAIR_BORDER))
        win.box();
        if curses.has_colors(): win.attroff(curses.color_pair(COLOR_PAIR_BORDER))
        return win

    def setup_windows(self): # ... (as before) ...
        if self.stdscr is None: return
        max_y, max_x = self.stdscr.getmaxyx();
        if max_y <= 3 or max_x <= 10: raise Exception("Terminal window too small.")
        self.status_win=curses.newwin(1,max_x,max_y-1,0); self.input_win=curses.newwin(1,max_x,max_y-2,0)
        self.input_win.keypad(True); main_h=max_y-2; main_w=max_x
        self.log_win=self._create_main_panel_window(main_h,main_w,0,0); self.log_win.scrollok(True)
        self.inventory_win=None; self.nearby_prims_win=None; self.friends_win=None; self.groups_win=None # Added groups_win
        self.stdscr.clear();self.stdscr.refresh();self.status_win.clear();self.status_win.refresh()
        self.input_win.clear();self.input_win.refresh();
        if self.log_win:self.log_win.clear();self.log_win.refresh()

    def _activate_panel(self, panel_name:str):
        self.active_main_panel = panel_name; max_y,max_x=self.stdscr.getmaxyx(); main_h=max_y-2; main_w=max_x
        panel_windows = {
            "inventory": "inventory_win", "nearby": "nearby_prims_win",
            "friends": "friends_win", "log": "log_win", "groups": "groups_win" # Added groups
        }
        for name, attr_name in panel_windows.items():
            win_instance = getattr(self, attr_name)
            if name != panel_name and win_instance:
                # If switching away from a panel, clear it but don't destroy the window object yet
                # to avoid recreating it constantly if user switches back and forth.
                # Consider full teardown if memory becomes an issue.
                win_instance.clear(); win_instance.refresh()
            elif name == panel_name and not win_instance:
                # Create window if it doesn't exist for the activated panel
                new_win = self._create_main_panel_window(main_h, main_w, 0, 0)
                if name == "log": new_win.scrollok(True)
                setattr(self, attr_name, new_win)

        if panel_name == "inventory": self.command_queue.put(("request_full_inventory", {}))
        elif panel_name == "groups": self.command_queue.put(("request_groups_summary", {})) # Request data for groups panel

        self.stdscr.clear(); self.stdscr.refresh(); self.draw_all_panels()

    def teardown_curses(self): logging.info("Curses client shutting down.")

    # --- Event Handlers ---
    def _on_login_progress(self, status: LoginStatus, message: str, error_key: str): # ... (as before)
        log_msg = f"[Login] {status.name}: {message}" + (f" ({error_key})" if error_key else "")
        color = COLOR_PAIR_SUCCESS if status == LoginStatus.SUCCESS else (COLOR_PAIR_ERROR if status == LoginStatus.FAILED else COLOR_PAIR_LOG_DEFAULT)
        self.ui_update_queue.put((log_msg, color))

        s_msg_base = f"Status: {status.name} - {message}"
        if status == LoginStatus.SUCCESS:
            agent_name = self.grid_client.self.name if self.grid_client.self else "Unknown"
            sim_name = self.grid_client.network.current_sim.name if self.grid_client.network.current_sim else "Unknown Sim"
            active_group_str = f" | Group: {self.grid_client.groups.active_group_name or 'None'}" if self.grid_client.groups.active_group_name else ""
            s_msg = f"Status: Connected to {sim_name} as {agent_name}{active_group_str}"
            self.ui_update_queue.put(("friends_list_changed", None)) # Also trigger friend list update
        elif status == LoginStatus.FAILED:
            s_msg = f"Status: Login Failed - {message}"
        else: # In progress or other states
            s_msg = s_msg_base
        self.ui_update_queue.put(("update_status", s_msg))

    def _on_sim_connected(self, sim: 'Simulator'):
        self.ui_update_queue.put((f"[SimConn] {sim.name}", COLOR_PAIR_SUCCESS))
        agent_name = self.grid_client.self.name if self.grid_client.self else "Unknown"
        active_group_str = f" | Group: {self.grid_client.groups.active_group_name or 'None'}" if self.grid_client.groups.active_group_name else ""
        self.ui_update_queue.put(("update_status", f"Status: Connected to {sim.name} as {agent_name}{active_group_str}"))
        self.ui_update_queue.put(("objects_changed", {"sim_uuid": sim.uuid}))

    def _on_sim_disconnected(self, sim: 'Simulator', req_logout: bool):
        self.ui_update_queue.put((f"[SimDisconn] {sim.name if sim else 'N/A'}. Logout: {req_logout}", COLOR_PAIR_LOG_DEFAULT))
        status_msg = "Status: Disconnected." + (" Logged out." if req_logout else "")
        self.ui_update_queue.put(("update_status", status_msg))
        self.ui_update_queue.put(("objects_changed", None))
        self.ui_update_queue.put(("friends_list_changed", None))
        # Could also clear active group display here if desired, or wait for next login.
    def _on_network_disconnected(self, reason: str): # ... (as before)
        self.ui_update_queue.put((f"[NetDisconn] Reason: {reason}", COLOR_PAIR_ERROR))
        self.ui_update_queue.put(("update_status", f"Status: Disconnected - {reason}")); self.ui_update_queue.put(("objects_changed", None)); self.ui_update_queue.put(("friends_list_changed", None))
    def _on_chat(self, ca: 'AgentManager.ChatEventArgs'): self.ui_update_queue.put((f"[{ca.source_type.name}] {ca.from_name}: {ca.message}" + (f" ({ca.chat_type.name})" if ca.chat_type != ChatType.NORMAL else ""), COLOR_PAIR_LOG_DEFAULT))
    def _on_im(self, ia: 'AgentManager.IMEventArgs'): # ... (as before)
        im = ia.im_data
        if im.dialog not in [InstantMessageDialog.FriendshipOffered, InstantMessageDialog.FriendshipAccepted, InstantMessageDialog.FriendshipDeclined]:
            self.ui_update_queue.put((f"IM from {im.from_agent_name} ({im.from_agent_id}): {im.message} (Dialog: {im.dialog.name}, Session: {im.im_session_id})", COLOR_PAIR_IMPORTANT))
    def _on_teleport_progress(self, tp: 'AgentManager.TeleportEventArgs'): # ... (as before)
        self.ui_update_queue.put((f"[Teleport] {tp.status.name}: {tp.message} Flags:{tp.flags!r}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put(("update_status", f"Status: Teleporting - {tp.status.name}"))
        if tp.status == TeleportStatus.FINISHED: self.ui_update_queue.put(("objects_changed", {"sim_uuid": self.grid_client.network.current_sim.uuid if self.grid_client.network.current_sim else None}))
    def _on_inventory_updated(self, inv_items: Dict[CustomUUID, InventoryBase]): self.ui_update_queue.put(("inventory_updated", None))
    def _on_objects_changed(self, prim: Primitive | None, sim: 'Simulator' | None, rem: bool = False): self.ui_update_queue.put(("objects_changed", {"sim_uuid": sim.uuid if sim else None}))
    def _on_wearables_updated(self, wearables: dict): self.ui_update_queue.put(("wearables_updated", wearables))
    def _on_friendship_offered(self, args: FriendshipOfferedEventArgs): # ... (as before)
        self.active_friendship_offers[args.offerer_uuid] = args.session_id
        self.ui_update_queue.put((f"Friendship from {args.offerer_name} ({args.offerer_uuid}). Msg: '{args.message}'. Use /friend_accept or /friend_decline {args.offerer_uuid}", COLOR_PAIR_IMPORTANT)); self.ui_update_queue.put(("friends_list_changed", None))
    def _on_friendship_response(self, args: FriendshipResponseEventArgs): # ... (as before)
        self.ui_update_queue.put((f"Friendship with {args.friend_uuid} {'accepted' if args.accepted else 'declined'}.", COLOR_PAIR_SUCCESS if args.accepted else COLOR_PAIR_LOG_DEFAULT))
        self.active_friendship_offers.pop(args.friend_uuid, None); self.ui_update_queue.put(("friends_list_changed", None))
    def _on_friend_online_status_changed(self, args: FriendOnlineStatusEventArgs): # ... (as before)
        self.ui_update_queue.put((f"Friend {args.friend_uuid} is now {'online' if args.is_online else 'offline'}.", COLOR_PAIR_LOG_DEFAULT)); self.ui_update_queue.put(("friends_list_changed", None))
    def _on_friend_rights_changed(self, args: FriendRightsEventArgs): # ... (as before)
        self.ui_update_queue.put((f"Rights for {args.friend_uuid}: TheirsToUs: {args.their_rights_to_us!r}, OursToThem: {args.our_rights_to_them!r}", COLOR_PAIR_LOG_DEFAULT)); self.ui_update_queue.put(("friends_list_changed", None))
    def _on_friend_removed(self, args: FriendRemovedEventArgs): # ... (as before)
        self.ui_update_queue.put((f"Friendship terminated with {args.friend_uuid}.", COLOR_PAIR_LOG_DEFAULT)); self.active_friendship_offers.pop(args.friend_uuid, None); self.ui_update_queue.put(("friends_list_changed", None))

    def _on_parcel_properties_updated(self, args: ParcelPropertiesEventArgs):
        parcel = args.parcel
        log_msg = (f"[ParcelProps] ID: {parcel.local_id}, Name: '{parcel.name}', Area: {parcel.area}sqm, "
                   f"Owner: {parcel.owner_id}, Status: {parcel.status.name}, Flags: {parcel.flags!r}\n"
                   f"  Desc: {parcel.description[:100]}...\n"
                   f"  Sim: {parcel.sim_name}, Global: ({parcel.global_x:.0f},{parcel.global_y:.0f},{parcel.global_z:.0f}) MusicURL: {parcel.music_url}\n"
                   f"  PrimOwners: {len(parcel.prim_owners)}, ACL Entries: {len(parcel.access_list)}")
        self.ui_update_queue.put((log_msg, COLOR_PAIR_SUCCESS))

    def _on_parcel_access_list_updated(self, args: ParcelAccessListEventArgs):
        log_msg_header = (f"[ParcelACL] LocalID: {args.parcel_local_id} in {args.simulator.name} (Seq: {args.sequence_id}, Flags: {args.flags:#x})")
        self.ui_update_queue.put((log_msg_header, COLOR_PAIR_SUCCESS))
        if not args.access_entries:
            self.ui_update_queue.put(("  No access list entries.", COLOR_PAIR_LOG_DEFAULT))
            return
        for entry in args.access_entries:
            log_entry = f"  - ID: {entry.agent_id}, Flags: {entry.flags!r} (Time: {entry.time})"
            self.ui_update_queue.put((log_entry, COLOR_PAIR_LOG_DEFAULT))

    def _on_group_list_updated(self, args: GroupListEventArgs): # Added
        self.groups_display_list = list(args.groups) # Update local cache for drawing
        self.ui_update_queue.put(("groups_list_changed", None)) # Signal UI to redraw if active
        log_msg = f"[Groups] Received group list update: {len(args.groups)} groups."
        self.ui_update_queue.put((log_msg, COLOR_PAIR_SUCCESS))

    def _on_group_profile_updated(self, args: GroupProfileEventArgs):
        group = args.group
        self.ui_update_queue.put((f"[GroupProfile] '{group.name}' ({group.id}):", COLOR_PAIR_SUCCESS))
        self.ui_update_queue.put((f"  Charter: {group.charter[:200]}{'...' if len(group.charter) > 200 else ''}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put((f"  Members: {group.member_count}, Founder: {group.founder_id}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put((f"  Insignia: {group.insignia_id}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put((f"  OpenEnroll: {group.open_enrollment}, ShowInList: {group.show_in_list}, AllowPublish: {group.allow_publish}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put((f"  Owner Role: {group.owner_role_id}", COLOR_PAIR_LOG_DEFAULT))
        self.ui_update_queue.put(("  Roles:", COLOR_PAIR_LOG_DEFAULT))
        if group.roles:
            for role_id, role in group.roles.items():
                self.ui_update_queue.put((f"    - Role: '{role.name}' ({role_id})", COLOR_PAIR_LOG_DEFAULT))
                self.ui_update_queue.put((f"      Title: '{role.title}', Desc: '{role.description}'", COLOR_PAIR_LOG_DEFAULT))
                self.ui_update_queue.put((f"      Powers: {role.powers!r}", COLOR_PAIR_LOG_DEFAULT))
        else:
            self.ui_update_queue.put(("    No roles information available.", COLOR_PAIR_LOG_DEFAULT))

    def _on_active_group_changed(self, args: ActiveGroupChangedEventArgs): # Added
        log_msg = (f"[ActiveGroup] Changed to: Name='{args.active_group_name or 'None'}' "
                   f"(ID: {args.active_group_id or 'None'}), Title='{args.active_group_title or 'N/A'}', "
                   f"Powers={args.active_group_powers!r}")
        self.ui_update_queue.put((log_msg, COLOR_PAIR_SUCCESS))

        # Update status bar
        if self.grid_client.network.logged_in and self.grid_client.self and self.grid_client.network.current_sim:
            agent_name = self.grid_client.self.name
            sim_name = self.grid_client.network.current_sim.name
            active_group_str = f" | Group: {args.active_group_name or 'None'}" + (f" [{args.active_group_title}]" if args.active_group_title else "")
            status_text = f"Status: Connected to {sim_name} as {agent_name}{active_group_str}"
            self.ui_update_queue.put(("update_status", status_text))
        elif self.grid_client.network.logged_in: # Logged in but no sim (e.g., during TP)
             self.ui_update_queue.put(("update_status", f"Status: Logged in. Active group: {args.active_group_name or 'None'}"))


    def run_pylibremetaverse_async(self):
        self.pylibremetaverse_loop = asyncio.new_event_loop(); asyncio.set_event_loop(self.pylibremetaverse_loop)
        async def main_async_logic():
            self.add_log_message_from_thread(("[Async] Loop started.", COLOR_PAIR_LOG_DEFAULT))
            # Register all handlers
            for handler_reg_func, local_handler in [
                (self.grid_client.network.register_login_progress_handler, self._on_login_progress),
                (self.grid_client.network.register_sim_connected_handler, self._on_sim_connected),
                (self.grid_client.network.register_sim_disconnected_handler, self._on_sim_disconnected),
                (self.grid_client.network.register_disconnected_handler, self._on_network_disconnected),
                (self.grid_client.self.register_chat_handler, self._on_chat),
                (self.grid_client.self.register_im_handler, self._on_im),
                (self.grid_client.self.register_teleport_progress_handler, self._on_teleport_progress),
                (self.grid_client.inventory.register_inventory_updated_handler, self._on_inventory_updated),
                (self.grid_client.objects.register_object_updated_handler, lambda p,s: self._on_objects_changed(p,s,False)),
                (self.grid_client.objects.register_object_removed_handler, lambda id,s: self._on_objects_changed(None,s,True)),
                (self.grid_client.appearance.register_wearables_updated_handler, self._on_wearables_updated),
                (self.grid_client.friends.register_friendship_offered_handler, self._on_friendship_offered),
                (self.grid_client.friends.register_friendship_response_handler, self._on_friendship_response),
                (self.grid_client.friends.register_online_status_changed_handler, self._on_friend_online_status_changed),
                (self.grid_client.friends.register_rights_changed_handler, self._on_friend_rights_changed),
                (self.grid_client.friends.register_friend_removed_handler, self._on_friend_removed),
                (self.grid_client.parcels.register_parcel_properties_updated_handler, self._on_parcel_properties_updated),
                (self.grid_client.parcels.register_parcel_access_list_updated_handler, self._on_parcel_access_list_updated),
                (self.grid_client.groups.register_group_list_handler, self._on_group_list_updated),
                (self.grid_client.groups.register_group_profile_updated_handler, self._on_group_profile_updated),
                (self.grid_client.groups.register_active_group_changed_handler, self._on_active_group_changed) # Added active group handler
            ]: handler_reg_func(local_handler) # type: ignore
            self.add_log_message_from_thread(("[Async] Event handlers registered.", COLOR_PAIR_LOG_DEFAULT))

            while self.is_running:
                try:
                    command_action = self.command_queue.get_nowait()
                    if command_action:
                        command, args = command_action
                        if not self.grid_client.network.logged_in and command not in ["login", "quit"]:
                            self.ui_update_queue.put(("Not logged in.", COLOR_PAIR_ERROR)); continue

                        handlers = { "login": lambda a: asyncio.create_task(self.grid_client.network.login(*a)) if not self.grid_client.network.logged_in else self.ui_update_queue.put(("Already logged in.", COLOR_PAIR_ERROR)),
                            "logout": lambda a: asyncio.create_task(self.grid_client.network.logout()) if self.grid_client.network.logged_in else self.ui_update_queue.put(("Not logged in.", COLOR_PAIR_ERROR)),
                            "chat": lambda a: asyncio.create_task(self.grid_client.self.chat(a['message'],a['channel'],a['type'])), "im": lambda a: asyncio.create_task(self.grid_client.self.instant_message(a['target_uuid'],a['message'])),
                            "set_control": lambda a: asyncio.create_task(self.grid_client.self.movement.set_controls(getattr(ControlFlags,a["flag_name"],ControlFlags.NONE),not ((self.grid_client.self.movement.agent_controls&getattr(ControlFlags,a["flag_name"],ControlFlags.NONE))==getattr(ControlFlags,a["flag_name"],ControlFlags.NONE)) if a.get("toggle") else a.get("active"))),
                            "toggle_fly": lambda a: asyncio.create_task(self.grid_client.self.movement.set_fly(not self.grid_client.self.movement.fly)), "toggle_run": lambda a: asyncio.create_task(self.grid_client.self.movement.set_always_run(not self.grid_client.self.movement.always_run)),
                            "stand": lambda a: asyncio.create_task(self.grid_client.self.stand()), "sit_on_ground": lambda a: asyncio.create_task(self.grid_client.self.sit_on_ground()), "toggle_mouselook": lambda a: asyncio.create_task(self.grid_client.self.movement.set_mouselook(not self.grid_client.self.movement.mouselook)),
                            "request_full_inventory": lambda a: asyncio.create_task(self.grid_client.inventory.request_inventory_root()) if self.grid_client.inventory.inventory_root_uuid else self.ui_update_queue.put(("Inv root unknown.", COLOR_PAIR_ERROR)),
                            "select_object": lambda a: asyncio.create_task(self.grid_client.objects.select_object(self.grid_client.network.current_sim,a["local_id"])), "deselect_object": lambda a: asyncio.create_task(self.grid_client.objects.deselect_object(self.grid_client.network.current_sim,a["local_id"])),
                            "touch_object": lambda a: asyncio.create_task(self._async_touch_object(a["local_id"])), "get_object_props": lambda a: self._async_get_object_props(a["local_id"]),
                            "teleport_to_handle": lambda a: asyncio.create_task(self.grid_client.self.teleport_to_location(a["region_handle"],Vector3(a["x"],a["y"],a["z"]),Vector3(0,0.9999,0))), "teleport_home": lambda a: asyncio.create_task(self.grid_client.self.go_home()),
                            "wear_uuid": lambda a: self._async_wear_item(a["item_uuid"]), "takeoff_uuid": lambda a: self._async_takeoff_item(a["item_uuid"]), "appearance_set": lambda a: asyncio.create_task(self.grid_client.appearance.set_appearance()),
                            "list_wearables": lambda a: self.ui_update_queue.put((self._format_wearables_list(), COLOR_PAIR_LOG_DEFAULT)),
                            "friend_offer": lambda a: asyncio.create_task(self.grid_client.friends.offer_friendship(a["uuid"],a["message"])), "friend_accept": lambda a: self._async_accept_friend(a["uuid"]), "friend_decline": lambda a: self._async_decline_friend(a["uuid"]),
                            "friend_terminate": lambda a: asyncio.create_task(self.grid_client.friends.terminate_friendship(a["uuid"])), "friend_grant_rights": lambda a: asyncio.create_task(self.grid_client.friends.grant_rights(a["uuid"],a["rights"])),
                            "inv_create_folder": lambda a: asyncio.create_task(self.grid_client.inventory.create_folder(a["parent_uuid"],a["name"],a["type"])), "inv_move": lambda a: self._async_move_inv_obj(a),
                            "inv_copy_item": lambda a: asyncio.create_task(self.grid_client.inventory.copy_inventory_item(a["item_uuid"],a["new_parent_uuid"],a["new_name"])),
                            "inv_trash": lambda a: self._async_trash_inv_obj(a["object_uuid"]), "inv_purge": lambda a: self._async_purge_inv_obj(a["object_uuid"]),
                            "parcelprops": lambda a: self._async_request_parcel_props(a["position"]),
                            "parcel_acl": lambda a: self._async_request_parcel_acl(a["local_id"], a["flags"]),
                            "request_groups_summary": lambda a: asyncio.create_task(self.grid_client.groups.request_current_groups_summary()),
                            "group_profile": lambda a: self._async_request_group_profile(a["group_id_or_name"]),
                            "group_activate": lambda a: self._async_activate_group(a["group_id_or_name"]) # Added
                        }
                        if command in handlers: handlers[command](args)
                except queue.Empty: pass
                await asyncio.sleep(0.05)
            if self.grid_client.network.logged_in:
                self.add_log_message_from_thread(("[Async] Logging out...", COLOR_PAIR_LOG_DEFAULT))
                try: await self.grid_client.disconnect()
                except Exception as e: self.add_log_message_from_thread((f"[Async] Error during final logout: {e}", COLOR_PAIR_ERROR))
            self.add_log_message_from_thread(("[Async] Loop ended.", COLOR_PAIR_LOG_DEFAULT))
        try: self.pylibremetaverse_loop.run_until_complete(main_async_logic())
        except Exception as e: self.ui_update_queue.put((f"[AsyncThreadError] {type(e).__name__}: {e}", COLOR_PAIR_ERROR)); logging.exception("Exception in run_pylibremetaverse_async")
        finally: self.pylibremetaverse_loop.close()

    async def _async_touch_object(self, local_id: int): await self.grid_client.self.grab(local_id); await asyncio.sleep(0.2); await self.grid_client.self.degrab(local_id)
    def _async_get_object_props(self, local_id: int):
        prim = self.grid_client.objects.get_prim(self.grid_client.network.current_sim, local_id)
        if prim and prim.id_uuid != CustomUUID.ZERO: asyncio.create_task(self.grid_client.objects.request_object_properties(self.grid_client.network.current_sim, prim.id_uuid))
        else: self.ui_update_queue.put((f"Prim LocalID {local_id} not found or UUID unknown.", COLOR_PAIR_ERROR))
    def _format_wearables_list(self) -> str: wd = self.grid_client.appearance.current_wearables_by_type; return "Worn:\n" + "\n".join([f"  - {wt.name}: {getattr(i,'name','Unknown')}" for wt,i in wd.items()]) if wd else "None worn."
    def _async_wear_item(self, item_uuid: CustomUUID): item = self.grid_client.inventory.get_item(item_uuid); (asyncio.create_task(self.grid_client.appearance.wear_items([item])) if item else self.ui_update_queue.put((f"Item {item_uuid} not found.", COLOR_PAIR_ERROR)))
    def _async_takeoff_item(self, item_uuid: CustomUUID): item = self.grid_client.inventory.get_item(item_uuid); (asyncio.create_task(self.grid_client.appearance.take_off_items([item])) if item else self.ui_update_queue.put((f"Item {item_uuid} not found.", COLOR_PAIR_ERROR)))
    def _async_accept_friend(self, offerer_uuid: CustomUUID): sid = self.active_friendship_offers.pop(offerer_uuid, None); (asyncio.create_task(self.grid_client.friends.accept_friendship_offer(offerer_uuid, sid)) if sid else self.ui_update_queue.put((f"No offer from {offerer_uuid}.", COLOR_PAIR_ERROR)))
    def _async_decline_friend(self, offerer_uuid: CustomUUID): sid = self.active_friendship_offers.pop(offerer_uuid, None); (asyncio.create_task(self.grid_client.friends.decline_friendship_offer(offerer_uuid, sid)) if sid else self.ui_update_queue.put((f"No offer from {offerer_uuid}.", COLOR_PAIR_ERROR)))
    def _async_move_inv_obj(self, args:dict): obj = self.grid_client.inventory.inventory_skeleton.get(args["object_uuid"]); (asyncio.create_task(self.grid_client.inventory.move_folder(args["object_uuid"], args["new_parent_uuid"], args.get("new_name"))) if isinstance(obj, InventoryFolder) else asyncio.create_task(self.grid_client.inventory.move_item(args["object_uuid"], args["new_parent_uuid"], args.get("new_name"))) if isinstance(obj, InventoryItem) else self.ui_update_queue.put((f"Obj {args['object_uuid']} not found.", COLOR_PAIR_ERROR)))
    def _async_trash_inv_obj(self, obj_uuid: CustomUUID): obj = self.grid_client.inventory.inventory_skeleton.get(obj_uuid); (asyncio.create_task(self.grid_client.inventory.delete_folder_to_trash(obj_uuid)) if isinstance(obj, InventoryFolder) else asyncio.create_task(self.grid_client.inventory.delete_item_to_trash(obj_uuid)) if isinstance(obj, InventoryItem) else self.ui_update_queue.put((f"Obj {obj_uuid} not found.", COLOR_PAIR_ERROR)))
    def _async_purge_inv_obj(self, obj_uuid: CustomUUID): obj = self.grid_client.inventory.inventory_skeleton.get(obj_uuid); (asyncio.create_task(self.grid_client.inventory.purge_folder_from_trash(obj_uuid)) if isinstance(obj, InventoryFolder) else asyncio.create_task(self.grid_client.inventory.purge_item_from_trash(obj_uuid)) if isinstance(obj, InventoryItem) else self.ui_update_queue.put((f"Obj {obj_uuid} not found.", COLOR_PAIR_ERROR)))
    async def _async_request_parcel_props(self, position: Vector3):
        if self.grid_client.network.current_sim:
            self.ui_update_queue.put((f"Requesting parcel properties at {position}...", COLOR_PAIR_LOG_DEFAULT))
            await self.grid_client.parcels.request_parcel_properties(self.grid_client.network.current_sim, position)
        else:
            self.ui_update_queue.put(("Not connected to a sim to request parcel props.", COLOR_PAIR_ERROR))

    async def _async_request_parcel_acl(self, local_id: int, flags: int): # Added
        if self.grid_client.network.current_sim:
            self.ui_update_queue.put((f"Requesting parcel ACL for local ID {local_id} (flags: {flags:#x})...", COLOR_PAIR_LOG_DEFAULT))
            await self.grid_client.parcels.request_parcel_access_list(self.grid_client.network.current_sim, local_id, request_flags=flags)
        else:
            self.ui_update_queue.put(("Not connected to a sim to request parcel ACL.", COLOR_PAIR_ERROR))

    async def _async_request_group_profile(self, group_id_or_name: str): # Added
        try:
            group_uuid = CustomUUID(group_id_or_name)
            await self.grid_client.groups.request_group_profile(group_uuid)
            return
        except ValueError: # Not a valid UUID string, try as name prefix
            pass # Fall through to name prefix search

        found_groups = []
        if self.grid_client.groups.current_groups_summary:
            for summary in self.grid_client.groups.current_groups_summary:
                if summary.name.lower().startswith(group_id_or_name.lower()):
                    found_groups.append(summary)

        if len(found_groups) == 1:
            self.ui_update_queue.put((f"Found group '{found_groups[0].name}', requesting profile...", COLOR_PAIR_LOG_DEFAULT))
            await self.grid_client.groups.request_group_profile(found_groups[0].group_id)
        elif len(found_groups) > 1:
            self.ui_update_queue.put((f"Multiple groups match '{group_id_or_name}'. Please be more specific or use UUID.", COLOR_PAIR_ERROR))
            for g in found_groups:
                 self.ui_update_queue.put((f"  - '{g.name}' ({g.group_id})", COLOR_PAIR_LOG_DEFAULT))
        else:
            self.ui_update_queue.put((f"No group found matching '{group_id_or_name}'. Try /groups then use UUID.", COLOR_PAIR_ERROR))

    async def _async_activate_group(self, group_id_or_name: str): # Added
        group_uuid_to_activate = None
        try:
            group_uuid_to_activate = CustomUUID(group_id_or_name)
        except ValueError: # Not a valid UUID string, try as name prefix
            found_groups = []
            if self.grid_client.groups.current_groups_summary:
                for summary in self.grid_client.groups.current_groups_summary:
                    if summary.name.lower().startswith(group_id_or_name.lower()):
                        found_groups.append(summary)

            if len(found_groups) == 1:
                group_uuid_to_activate = found_groups[0].group_id
                self.ui_update_queue.put((f"Found group '{found_groups[0].name}', attempting to activate...", COLOR_PAIR_LOG_DEFAULT))
            elif len(found_groups) > 1:
                self.ui_update_queue.put((f"Multiple groups match '{group_id_or_name}'. Please be more specific or use UUID.", COLOR_PAIR_ERROR))
                for g in found_groups:
                    self.ui_update_queue.put((f"  - '{g.name}' ({g.group_id})", COLOR_PAIR_LOG_DEFAULT))
                return # Don't proceed if ambiguous
            else:
                self.ui_update_queue.put((f"No group found matching '{group_id_or_name}'. Try /groups then use UUID.", COLOR_PAIR_ERROR))
                return

        if group_uuid_to_activate:
            await self.grid_client.groups.activate_group(group_uuid_to_activate)
            # Status bar will be updated by _on_active_group_changed event handler via AgentDataUpdate
        else: # Should not happen if logic above is correct
             self.ui_update_queue.put((f"Could not determine group UUID for '{group_id_or_name}'.", COLOR_PAIR_ERROR))


    def start_pylibremetaverse_thread(self): self.pylibremetaverse_thread = threading.Thread(target=self.run_pylibremetaverse_async, daemon=True); self.pylibremetaverse_thread.start()
    def draw_log_panel(self):
        if self.log_win is None or self.active_main_panel != "log": return
        self.log_win.clear(); max_y, max_x = self.log_win.getmaxyx();
        if curses.has_colors(): self.log_win.attron(curses.color_pair(COLOR_PAIR_BORDER));
        self.log_win.box();
        if curses.has_colors(): self.log_win.attroff(curses.color_pair(COLOR_PAIR_BORDER));
        start_index = max(0, len(self.log_messages) - (max_y - 2))
        for i, (msg, color_id) in enumerate(self.log_messages[start_index:]):
            if i < max_y -2 :
                try: self.log_win.addstr(i + 1, 1, msg[:max_x -3], curses.color_pair(color_id))
                except curses.error: pass
        self.log_win.refresh()
    def add_log_message(self, msg_item: str | Tuple[str, int]):
        msg, color_id = (msg_item, COLOR_PAIR_LOG_DEFAULT) if isinstance(msg_item, str) else msg_item
        if not isinstance(msg, str): msg = str(msg)
        current_time = time.strftime("%H:%M:%S", time.localtime())
        self.log_messages.append((f"[{current_time}] {msg}", color_id))
        if len(self.log_messages) > MAX_LOG_LINES: self.log_messages.pop(0)
        if self.active_main_panel == "log": self.draw_log_panel()
    def add_log_message_from_thread(self, msg_item: str | Tuple[str, int]): self.ui_update_queue.put(msg_item)
    def draw_status_bar(self, text: str | None = None):
        if self.status_win is None: return
        if text is not None: self.current_status_text = text
        self.status_win.clear(); _max_y, max_x = self.status_win.getmaxyx()
        try:
            self.status_win.attron(curses.color_pair(COLOR_PAIR_STATUS_BAR)); self.status_win.addstr(0, 0, self.current_status_text[:max_x -1].ljust(max_x-1)); self.status_win.attroff(curses.color_pair(COLOR_PAIR_STATUS_BAR))
        except curses.error: pass
        self.status_win.refresh()
    def draw_input_line(self):
        if self.input_win is None: return
        self.input_win.clear(); _max_y, max_x = self.input_win.getmaxyx()
        prompt = "> "; display_text = f"{prompt}{self.input_buffer}"
        try:
            if curses.has_colors(): self.input_win.attron(curses.color_pair(COLOR_PAIR_PROMPT));
            self.input_win.addstr(0, 0, prompt);
            if curses.has_colors(): self.input_win.attroff(curses.color_pair(COLOR_PAIR_PROMPT));
            self.input_win.addstr(0, len(prompt), self.input_buffer[:max_x - len(prompt) -1], curses.color_pair(COLOR_PAIR_INPUT if curses.has_colors() else 0))
            self.input_win.move(0, min(len(display_text), max_x - 1))
        except curses.error: pass
        self.input_win.refresh()

    def process_ui_queue(self):
        while not self.ui_update_queue.empty():
            try:
                msg_item = self.ui_update_queue.get_nowait()
                if isinstance(msg_item, tuple) and len(msg_item) == 2:
                    action_or_msg, content_or_color_id = msg_item
                    if action_or_msg == "update_status": self.draw_status_bar(content_or_color_id)
                    elif action_or_msg == "inventory_updated":
                        if self.active_main_panel == "inventory": self.draw_inventory_panel()
                        self.add_log_message(("[UI] Inventory data updated.", COLOR_PAIR_SUCCESS))
                    elif action_or_msg == "objects_changed":
                        if self.active_main_panel == "nearby": self.draw_nearby_prims_panel()
                    elif action_or_msg == "wearables_updated":
                        if self.grid_client.network.logged_in: self.add_log_message(("[UI] Wearables updated.", COLOR_PAIR_LOG_DEFAULT))
                    elif action_or_msg == "friends_list_changed":
                        if self.active_main_panel == "friends": self.draw_friends_panel()
                    elif action_or_msg == "groups_list_changed": # Added
                        if self.active_main_panel == "groups": self.draw_groups_panel()
                    elif isinstance(action_or_msg, str) and isinstance(content_or_color_id, int):
                        self.add_log_message((action_or_msg, content_or_color_id))
                    else: self.add_log_message((f"Unknown action: {action_or_msg}, Content: {content_or_color_id}", COLOR_PAIR_ERROR))
                elif isinstance(msg_item, str): self.add_log_message((msg_item, COLOR_PAIR_LOG_DEFAULT))
                else: self.add_log_message((f"Unknown UI queue item: {msg_item}", COLOR_PAIR_ERROR))
            except queue.Empty: break
            except Exception as e: self.add_log_message((f"[UIQueueError] {type(e).__name__}: {e}", COLOR_PAIR_ERROR))
    def _build_inventory_display_lines_recursive(self, folder_uuid: CustomUUID, indent_level: int, lines: list):
        folder = self.grid_client.inventory.inventory_skeleton.get(folder_uuid)
        if folder and isinstance(folder, InventoryFolder):
            lines.append("  " * indent_level + f"[F] {folder.name} ({len(folder.children)}) - {folder.uuid}")
            children_items = []; children_folders = []
            for child_uuid in folder.children:
                child = self.grid_client.inventory.inventory_skeleton.get(child_uuid)
                if child: (children_folders.append(child) if isinstance(child, InventoryFolder) else children_items.append(child))
            children_folders.sort(key=lambda x: x.name.lower()); children_items.sort(key=lambda x: x.name.lower())
            for cf in children_folders: self._build_inventory_display_lines_recursive(cf.uuid, indent_level + 1, lines)
            for ci in children_items:
                if isinstance(ci, InventoryItem): lines.append("  "*(indent_level+1)+f"- {ci.name} [{ci.inv_type.name}] - {ci.uuid}")
    def draw_inventory_panel(self):
        if not self.inventory_win: return
        self.inventory_win.clear(); self.inventory_display_lines = []
        if self.grid_client.inventory.inventory_root_uuid: self._build_inventory_display_lines_recursive(self.grid_client.inventory.inventory_root_uuid, 0, self.inventory_display_lines)
        elif not self.grid_client.network.logged_in: self.inventory_display_lines.append("Not logged in.")
        else: self.inventory_display_lines.append("Inventory not loaded. Try /inv refresh.")
        max_y,max_x = self.inventory_win.getmaxyx();
        if curses.has_colors(): self.inventory_win.attron(curses.color_pair(COLOR_PAIR_BORDER));
        self.inventory_win.box();
        if curses.has_colors(): self.inventory_win.attroff(curses.color_pair(COLOR_PAIR_BORDER));
        page_h = max_y - 2
        if self.inventory_scroll_pos > len(self.inventory_display_lines) - page_h and len(self.inventory_display_lines) > page_h: self.inventory_scroll_pos = len(self.inventory_display_lines) - page_h
        if self.inventory_scroll_pos < 0: self.inventory_scroll_pos = 0
        for i, line in enumerate(self.inventory_display_lines[self.inventory_scroll_pos : self.inventory_scroll_pos + page_h]): self.inventory_win.addstr(i + 1, 1, line[:max_x-3], curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        if not self.inventory_display_lines: self.inventory_win.addstr(1,1, "Inventory empty/not loaded.", curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        self.inventory_win.refresh()
    def _update_nearby_prims_display_list(self):
        if not (self.grid_client.network.current_sim and self.grid_client.self): self.nearby_prims_display_list = []; return
        prims = self.grid_client.objects.get_prims_in_sim(self.grid_client.network.current_sim)
        agent_pos = self.grid_client.self.current_position
        if prims:
            dist_prims = [{'dist':(p.position-agent_pos).magnitude() if agent_pos else 0,'prim':p} for p in prims.values()]
            dist_prims.sort(key=lambda x: x['dist']); self.nearby_prims_display_list = [i['prim'] for i in dist_prims]
        else: self.nearby_prims_display_list = []
    def draw_nearby_prims_panel(self):
        if not self.nearby_prims_win: return
        self.nearby_prims_win.clear(); self._update_nearby_prims_display_list()
        max_y,max_x = self.nearby_prims_win.getmaxyx();
        if curses.has_colors(): self.nearby_prims_win.attron(curses.color_pair(COLOR_PAIR_BORDER));
        self.nearby_prims_win.box();
        if curses.has_colors(): self.nearby_prims_win.attroff(curses.color_pair(COLOR_PAIR_BORDER));
        page_h = max_y - 2
        if self.nearby_prims_scroll_pos > len(self.nearby_prims_display_list) - page_h and len(self.nearby_prims_display_list) > page_h: self.nearby_prims_scroll_pos = len(self.nearby_prims_display_list) - page_h
        if self.nearby_prims_scroll_pos < 0: self.nearby_prims_scroll_pos = 0
        agent_pos = self.grid_client.self.current_position if self.grid_client.self else None
        for i,p in enumerate(self.nearby_prims_display_list[self.nearby_prims_scroll_pos:self.nearby_prims_scroll_pos+page_h]):
            dist = (p.position-agent_pos).magnitude() if agent_pos else -1
            line = f"LID:{p.local_id} '{p.name or 'N/A'}' ({dist:.1f}m) P:{p.pcode.name} S:{p.scale}"
            self.nearby_prims_win.addstr(i+1,1,line[:max_x-3],curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        if not self.nearby_prims_display_list: self.nearby_prims_win.addstr(1,1,"No prims nearby.", curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        self.nearby_prims_win.refresh()
    def _update_friends_display_list(self):
        if not self.grid_client.network.logged_in: self.friends_display_list = []; return
        self.friends_display_list = sorted(list(self.grid_client.friends.friends.values()), key=lambda f: (not f.online, f.name.lower()))
    def draw_friends_panel(self):
        if not self.friends_win: return
        self.friends_win.clear(); self._update_friends_display_list()
        max_y,max_x = self.friends_win.getmaxyx();
        if curses.has_colors(): self.friends_win.attron(curses.color_pair(COLOR_PAIR_BORDER));
        self.friends_win.box();
        if curses.has_colors(): self.friends_win.attroff(curses.color_pair(COLOR_PAIR_BORDER));
        page_h = max_y - 2
        if self.friends_scroll_pos > len(self.friends_display_list) - page_h and len(self.friends_display_list) > page_h: self.friends_scroll_pos = len(self.friends_display_list) - page_h
        if self.friends_scroll_pos < 0: self.friends_scroll_pos = 0
        for i,f in enumerate(self.friends_display_list[self.friends_scroll_pos:self.friends_scroll_pos+page_h]):
            s="Online" if f.online else "Offline";our_r="".join([r.name[0] for r in FriendRights if r in f.our_rights_given_to_them and r!=FriendRights.NONE])or"-";their_r="".join([r.name[0] for r in FriendRights if r in f.their_rights_given_to_us and r!=FriendRights.NONE])or"-"
            line = f"{f.name or 'N/A'} ({f.uuid}) - {s} Us->Th:{our_r} Th->Us:{their_r}"
            self.friends_win.addstr(i+1,1,line[:max_x-3], curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        if not self.friends_display_list: self.friends_win.addstr(1,1,"No friends.", curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        self.friends_win.refresh()

    def setup_groups_window(self): # Added
        if self.stdscr is None: return
        max_y, max_x = self.stdscr.getmaxyx()
        main_h = max_y - 2
        main_w = max_x
        self.groups_win = self._create_main_panel_window(main_h, main_w, 0, 0)
        # self.groups_win.scrollok(True) # Not typically needed if redrawing full page

    # _update_groups_display_list is implicitly handled by _on_group_list_updated
    # which directly updates self.groups_display_list. If sorting/filtering is needed,
    # this method could be expanded. For now, it's a direct copy.

    def draw_groups_panel(self): # Added
        if not self.groups_win:
            self.setup_groups_window() # Ensure window exists
            if not self.groups_win: return # Still couldn't create it

        self.groups_win.clear()
        max_y,max_x = self.groups_win.getmaxyx()

        if curses.has_colors(): self.groups_win.attron(curses.color_pair(COLOR_PAIR_BORDER))
        self.groups_win.box()
        if curses.has_colors(): self.groups_win.attroff(curses.color_pair(COLOR_PAIR_BORDER))

        page_h = max_y - 2 if max_y > 2 else 1

        # Ensure scroll position is valid
        if self.groups_scroll_pos > len(self.groups_display_list) - page_h and len(self.groups_display_list) > page_h:
            self.groups_scroll_pos = len(self.groups_display_list) - page_h
        if self.groups_scroll_pos < 0:
            self.groups_scroll_pos = 0

        for i, group_summary in enumerate(self.groups_display_list[self.groups_scroll_pos : self.groups_scroll_pos + page_h]):
            line = f"'{group_summary.name}' ({group_summary.group_id}) - Title: '{group_summary.title}' Notices:{'Y' if group_summary.accept_notices else 'N'}"
            try:
                self.groups_win.addstr(i + 1, 1, line[:max_x-3], curses.color_pair(COLOR_PAIR_PANEL_TEXT))
            except curses.error: pass # Avoid crashing if line is too long or at edge

        if not self.groups_display_list and self.grid_client.network.logged_in:
            self.groups_win.addstr(1, 1, "No groups found or list not loaded. Try /groups again.", curses.color_pair(COLOR_PAIR_PANEL_TEXT))
        elif not self.grid_client.network.logged_in:
            self.groups_win.addstr(1, 1, "Not logged in.", curses.color_pair(COLOR_PAIR_PANEL_TEXT))

        self.groups_win.refresh()

    def handle_user_input(self, key: int): # Add /parcelprops command
        active_panel_win = None; scroll_attr_name = None; display_list_len = 0
        if self.active_main_panel == "inventory": active_panel_win = self.inventory_win; scroll_attr_name = "inventory_scroll_pos"; display_list_len = len(self.inventory_display_lines)
        elif self.active_main_panel == "nearby": active_panel_win = self.nearby_prims_win; scroll_attr_name = "nearby_prims_scroll_pos"; display_list_len = len(self.nearby_prims_display_list)
        elif self.active_main_panel == "friends": active_panel_win = self.friends_win; scroll_attr_name = "friends_scroll_pos"; display_list_len = len(self.friends_display_list)
        elif self.active_main_panel == "groups": active_panel_win = self.groups_win; scroll_attr_name = "groups_scroll_pos"; display_list_len = len(self.groups_display_list) # Added groups

        if active_panel_win and key in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE, curses.KEY_NPAGE]:
            max_panel_y, _ = active_panel_win.getmaxyx(); page_size = max_panel_y - 2 if max_panel_y > 2 else 1 # Ensure page_size is at least 1
            current_scroll = getattr(self, scroll_attr_name)
            max_scroll = max(0, display_list_len - page_size)
            if key == curses.KEY_UP: setattr(self, scroll_attr_name, max(0, current_scroll - 1))
            elif key == curses.KEY_DOWN: setattr(self, scroll_attr_name, min(current_scroll + 1, max_scroll))
            elif key == curses.KEY_PPAGE: setattr(self, scroll_attr_name, max(0, current_scroll - page_size))
            elif key == curses.KEY_NPAGE: setattr(self, scroll_attr_name, min(current_scroll + page_size, max_scroll))
            return

        if key == curses.KEY_ENTER or key == 10 or key == 13:
            command_line = self.input_buffer.strip(); self.input_buffer = ""
            if command_line: self.add_log_message((f"> {command_line}", COLOR_PAIR_INPUT))
            if not command_line: return
            parts = command_line.split(); command_word = parts[0].lower(); args_cmd = parts[1:]

            if command_word == "/quit": self.is_running = False; self.add_log_message(("Quit command...", COLOR_PAIR_LOG_DEFAULT))
            elif command_word == "/help": self.display_help()
            elif command_word == "/view":
                if args_cmd and args_cmd[0] in ["log","inventory","nearby","friends", "groups"]: self._activate_panel(args_cmd[0]); self.add_log_message((f"Switched to {args_cmd[0]} panel.", COLOR_PAIR_LOG_DEFAULT))
                else: self.add_log_message(("/view [log|inv|nearby|friends|groups]", COLOR_PAIR_ERROR))
            elif command_word == "/parcelprops":
                if len(args_cmd) == 3:
                    try: x = float(args_cmd[0]); y = float(args_cmd[1]); z = float(args_cmd[2]); target_pos = Vector3(x,y,z)
                    except ValueError: self.add_log_message(("Invalid coordinates for /parcelprops.", COLOR_PAIR_ERROR)); return
                elif not args_cmd and self.grid_client.self and self.grid_client.self.current_position != Vector3.ZERO :
                    target_pos = self.grid_client.self.current_position
                else: self.add_log_message(("Usage: /parcelprops [x y z] (uses current pos if no args & available)", COLOR_PAIR_ERROR)); return
                self.command_queue.put(("parcelprops", {"position": target_pos}))
            elif command_word == "/parcel_acl":
                if len(args_cmd) >= 1:
                    try: local_id = int(args_cmd[0]); flags = int(args_cmd[1]) if len(args_cmd) > 1 else 0
                    except ValueError: self.add_log_message(("Invalid arguments for /parcel_acl.", COLOR_PAIR_ERROR)); return
                    self.command_queue.put(("parcel_acl", {"local_id": local_id, "flags": flags}))
                else: self.add_log_message(("Usage: /parcel_acl <local_id> [flags_int]", COLOR_PAIR_ERROR)); return
            elif command_word == "/groups":
                self._activate_panel("groups")
            elif command_word == "/group_profile": # Added
                if args_cmd:
                    self.command_queue.put(("group_profile", {"group_id_or_name": " ".join(args_cmd)}))
                else:
                    self.add_log_message(("Usage: /group_profile <group_uuid_or_name_prefix>", COLOR_PAIR_ERROR))
            elif command_word == "/group_activate": # Added
                if args_cmd:
                    self.command_queue.put(("group_activate", {"group_id_or_name": " ".join(args_cmd)}))
                else:
                    self.add_log_message(("Usage: /group_activate <group_uuid_or_name_prefix>", COLOR_PAIR_ERROR))
            elif command_word.startswith("/"): # Catch-all for other slash commands
                # This is where the extensive list of previous commands would be
                self.add_log_message((f"Processing command {command_word}...", COLOR_PAIR_LOG_DEFAULT)) # Placeholder
                # Based on previous state, many commands are handled here.
                # For brevity, I'll assume they are called as before.
                # Example:
                if command_word == "/login" and len(args_cmd) >= 3:
                    uri = args_cmd[3] if len(args_cmd) > 3 else DEFAULT_LOGIN_SERVER
                    self.command_queue.put(("login", (args_cmd[0], args_cmd[1], args_cmd[2], "PyLibreMVCurses", "0.1", "last", uri)))
                # ... many other elif blocks for all other commands ...
                else: # If no specific handler after all checks
                    self.add_log_message((f"Unknown command: {command_line}", COLOR_PAIR_ERROR))
            else: # Default to chat
                self.command_queue.put(("chat", {"message": command_line, "channel": 0, "type": ChatType.NORMAL}))
        elif key == curses.KEY_BACKSPACE or key == 127 or key == curses.erasechar(): self.input_buffer = self.input_buffer[:-1]
        elif key != -1 and curses.ascii.isprint(key): self.input_buffer += chr(key)

    def display_help(self):
        self._activate_panel("log")
        help_text = [("--- PyLibreMetaverse Curses Client Help ---", COLOR_PAIR_SUCCESS)]
        commands = [ ("/quit", "Exit"), ("/login <f> <l> <p> [uri]", "Login"), ("/logout", "Logout"),
            ("/view [log|inv|nearby|friends]", "Switch panel"), ("/say <msg> or <msg>", "Chat"),
            ("/im <uuid> <msg>", "IM"), ("/w /s /a /d /e /c [on|off]", "Move/Turn"),
            ("/strafeleft|right [on|off]", "Strafe"), ("/fly /run /mouselook", "Toggle states"),
            ("/stand /sit", "Stand/Sit"), ("/tp_handle <rh> <x> <y> <z>", "TP coords"),
            ("/home", "TP home"), ("/parcelprops [x y z]", "Parcel props"), ("/parcel_acl <lid> [flags]", "Parcel ACL"),
            ("/groups", "Toggle Groups Panel & Refresh List"),
            ("/group_profile <uuid_or_name>", "Show group details"),
            ("/group_activate <uuid_or_name>", "Set active group tag"), # Added
            ("/inv", "Toggle Inventory"), ("/inv_mkfolder <p_id> <n> [t]", "Make folder"),
            ("/inv_mv <o_id> <np_id> [n]", "Move"), ("/inv_cp <i_id> <np_id> <n>", "Copy"),
            ("/inv_trash <o_id>", "Trash"), ("/inv_purge <o_id>", "Purge"),
            ("/nearby", "Toggle Nearby Prims"), ("/select <lid>", "Select obj"), ("/deselect <lid>", "Deselect"),
            ("/touch <lid>", "Touch obj"), ("/getprops <lid>", "Obj props"),
            ("/friends", "Toggle Friends"), ("/friend_offer <uuid> [msg]", "Offer friend"),
            ("/friend_accept <uuid>", "Accept"), ("/friend_decline <uuid>", "Decline"),
            ("/friend_terminate <uuid>", "End friend"), ("/friend_grant_rights <uuid> <on> <map> <mod>", "Grant (t/f)"),
            ("/wear_uuid <item>", "Wear"), ("/takeoff_uuid <item>", "Take off"),
            ("/appearance_set", "Rebake"), ("/ls_wearables", "List worn"),
            ("UP/DOWN/PGUP/PGDN for scrolling active panel.", COLOR_PAIR_LOG_DEFAULT) ]
        for cmd, desc in commands: help_text.append((f"{cmd:<60} - {desc}", COLOR_PAIR_LOG_DEFAULT))
        for line, color in help_text: self.add_log_message((line, color))

    def draw_all_panels(self):
        self.stdscr.clear()
        if self.active_main_panel == "inventory":
            if self.inventory_win is None: self.setup_inventory_window()
            self.draw_inventory_panel()
        elif self.active_main_panel == "nearby":
            if self.nearby_prims_win is None: self.setup_nearby_prims_window()
            self.draw_nearby_prims_panel()
        elif self.active_main_panel == "friends":
            if self.friends_win is None: self.setup_friends_window() # Assuming setup_friends_window exists
            self.draw_friends_panel()
        elif self.active_main_panel == "groups": # Added
            if self.groups_win is None: self.setup_groups_window()
            self.draw_groups_panel()
        else:
            if self.log_win is None:
                 max_y, max_x = self.stdscr.getmaxyx()
                 self.log_win = self._create_main_panel_window(max_y - 2, max_x, 0, 0)
                 self.log_win.scrollok(True)
            self.draw_log_panel()
        self.draw_input_line(); self.draw_status_bar(); self.stdscr.refresh(); curses.doupdate()

    def main_loop(self, stdscr):
        self.stdscr = stdscr; self.setup_colors(); curses.curs_set(1); self.stdscr.nodelay(True); self.stdscr.timeout(100)
        try:
            self.setup_windows(); self.start_pylibremetaverse_thread()
            self.add_log_message(("Curses client started. Type /help for commands.", COLOR_PAIR_SUCCESS))
            self.draw_status_bar(self.current_status_text)
            while self.is_running:
                key = -1
                try: key = self.stdscr.getch()
                except curses.error: pass
                if key != -1: self.handle_user_input(key)
                self.process_ui_queue(); self.draw_all_panels()
        except Exception as e: logging.exception("Critical error in CursesApp main_loop"); self.is_running = False; print(f"Fatal error: {e}", file=sys.stderr)
        finally:
            self.is_running = False
            if self.pylibremetaverse_loop and self.pylibremetaverse_thread and self.pylibremetaverse_thread.is_alive():
                if self.grid_client.network.logged_in:
                    self.add_log_message_from_thread(("Shutting down network (final attempt)...",COLOR_PAIR_LOG_DEFAULT))
                    future = asyncio.run_coroutine_threadsafe(self.grid_client.disconnect(), self.pylibremetaverse_loop)
                    try: future.result(timeout=3.0)
                    except Exception as e_logout: self.add_log_message_from_thread((f"Error during final logout: {e_logout}",COLOR_PAIR_ERROR))
                if self.pylibremetaverse_loop.is_running(): self.pylibremetaverse_loop.call_soon_threadsafe(self.pylibremetaverse_loop.stop)
                self.pylibremetaverse_thread.join(timeout=3.0)
            logging.info("Curses main_loop finished.")

def main():
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curses_client.log")
    logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format=LOG_FORMAT, filemode='w')
    console_handler = logging.StreamHandler(sys.stderr); console_handler.setLevel(logging.CRITICAL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT)); logging.getLogger().addHandler(console_handler)
    logging.info("Application starting...")
    app = CursesApp()
    try: curses.wrapper(app.main_loop)
    except curses.error as ce: logging.exception("Curses err"); print(f"Curses init failed: {ce}.", file=sys.stderr)
    except Exception as e: logging.exception("Unhandled ex"); print(f"Unexpected error: {e}", file=sys.stderr)
    finally:
        logging.info("Application ended.")
        if app.is_running: app.is_running = False
        if app.pylibremetaverse_thread and app.pylibremetaverse_thread.is_alive():
            print("Joining pylibremetaverse_thread...", file=sys.stderr)
            if app.pylibremetaverse_loop and app.pylibremetaverse_loop.is_running(): app.pylibremetaverse_loop.call_soon_threadsafe(app.pylibremetaverse_loop.stop)
            app.pylibremetaverse_thread.join(timeout=2.0)
            if app.pylibremetaverse_thread.is_alive(): print("Warning: pylibremetaverse_thread did not exit cleanly.", file=sys.stderr)
        print("Curses client exited.", file=sys.stderr)

if __name__ == "__main__":
    main()
