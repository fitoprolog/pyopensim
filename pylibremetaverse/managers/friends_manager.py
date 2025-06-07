import logging
import asyncio
from typing import TYPE_CHECKING, Dict, List, Callable, Any

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.friends_defs import FriendInfo, FriendRights, BuddyListEntry
import dataclasses # Added for FriendOnlineStatusEventArgs
from pylibremetaverse.types.enums import InstantMessageDialog, PacketType
from pylibremetaverse.network.packets_friends import (
    OfferFriendshipPacket, AcceptFriendshipPacket,
    OnlineNotificationPacket, OfflineNotificationPacket, FindAgentPacket, AgentOnlineStatusPacket,
    ChangeUserRightsPacket, TerminateFriendshipPacket # Added new packets
)


if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.managers.agent_manager import IMEventArgs
    from pylibremetaverse.network.simulator import Simulator # For packet handler type hints

logger = logging.getLogger(__name__)

# --- Event Argument Dataclasses (Optional but good practice) ---
@dataclasses.dataclass(slots=True)
class FriendOnlineStatusEventArgs:
    friend_uuid: CustomUUID
    is_online: bool

@dataclasses.dataclass(slots=True)
class FriendRightsEventArgs:
    friend_uuid: CustomUUID
    their_rights_to_us: FriendRights
    our_rights_to_them: FriendRights

@dataclasses.dataclass(slots=True)
class FriendRemovedEventArgs:
    friend_uuid: CustomUUID

# Define Handler Types
FriendshipOfferedHandler = Callable[[CustomUUID, str, str, CustomUUID], Any]
FriendshipResponseHandler = Callable[[CustomUUID, bool], Any]
OnlineStatusChangedHandler = Callable[[FriendOnlineStatusEventArgs], Any]
RightsChangedHandler = Callable[[FriendRightsEventArgs], Any] # Using dataclass
FriendRemovedHandler = Callable[[FriendRemovedEventArgs], Any] # Using dataclass


class FriendsManager:
    def __init__(self, client: 'GridClient'):
        self.client = client
        self.friends: Dict[CustomUUID, FriendInfo] = {}

        self._friendship_offered_handlers: List[FriendshipOfferedHandler] = []
        self._friendship_response_handlers: List[FriendshipResponseHandler] = []
        self._online_status_changed_handlers: List[OnlineStatusChangedHandler] = []
        self._rights_changed_handlers: List[RightsChangedHandler] = []
        self._friend_removed_handlers: List[FriendRemovedHandler] = []


        # IM Handler registration is done by GridClient after all managers are initialized.

        # Register packet handlers for online status
        if self.client.network:
            reg = self.client.network.register_packet_handler
            reg(PacketType.OnlineNotification, self._on_online_notification_wrapper)
            reg(PacketType.OfflineNotification, self._on_offline_notification_wrapper)
            reg(PacketType.AgentOnlineStatus, self._on_agent_online_status_wrapper)
            logger.debug("FriendsManager registered online status packet handlers.")
        else:
            logger.warning("FriendsManager: NetworkManager not available at init for packet handlers.")


    # --- Wrapper methods for packet handlers ---
    def _on_online_notification_wrapper(self, simulator: 'Simulator', packet: Packet):
        if isinstance(packet, OnlineNotificationPacket):
            self._on_online_notification(simulator, packet)
        else:
            logger.warning(f"Received non-OnlineNotificationPacket for OnlineNotification type: {type(packet)}")

    def _on_offline_notification_wrapper(self, simulator: 'Simulator', packet: Packet):
        if isinstance(packet, OfflineNotificationPacket):
            self._on_offline_notification(simulator, packet)
        else:
            logger.warning(f"Received non-OfflineNotificationPacket for OfflineNotification type: {type(packet)}")

    def _on_agent_online_status_wrapper(self, simulator: 'Simulator', packet: Packet):
        if isinstance(packet, AgentOnlineStatusPacket):
            self._on_agent_online_status(simulator, packet)
        else:
            logger.warning(f"Received non-AgentOnlineStatusPacket for AgentOnlineStatus type: {type(packet)}")


    # --- Handler Registration ---
    def register_friendship_offered_handler(self, callback: FriendshipOfferedHandler):
        if callback not in self._friendship_offered_handlers: self._friendship_offered_handlers.append(callback)
    def unregister_friendship_offered_handler(self, callback: FriendshipOfferedHandler):
        if callback in self._friendship_offered_handlers: self._friendship_offered_handlers.remove(callback)

    def register_friendship_response_handler(self, callback: FriendshipResponseHandler):
        if callback not in self._friendship_response_handlers: self._friendship_response_handlers.append(callback)
    def unregister_friendship_response_handler(self, callback: FriendshipResponseHandler):
        if callback in self._friendship_response_handlers: self._friendship_response_handlers.remove(callback)

    def register_online_status_changed_handler(self, callback: OnlineStatusChangedHandler):
        if callback not in self._online_status_changed_handlers: self._online_status_changed_handlers.append(callback)
    def unregister_online_status_changed_handler(self, callback: OnlineStatusChangedHandler):
        if callback in self._online_status_changed_handlers: self._online_status_changed_handlers.remove(callback)

    def register_rights_changed_handler(self, callback: RightsChangedHandler):
        if callback not in self._rights_changed_handlers: self._rights_changed_handlers.append(callback)
    def unregister_rights_changed_handler(self, callback: RightsChangedHandler):
        if callback in self._rights_changed_handlers: self._rights_changed_handlers.remove(callback)

    def register_friend_removed_handler(self, callback: FriendRemovedHandler):
        if callback not in self._friend_removed_handlers: self._friend_removed_handlers.append(callback)
    def unregister_friend_removed_handler(self, callback: FriendRemovedHandler):
        if callback in self._friend_removed_handlers: self._friend_removed_handlers.remove(callback)


    # --- Event Firing Methods ---
    def _fire_friendship_offered(self, offerer_id: CustomUUID, offerer_name: str, message: str, im_session_id: CustomUUID):
        logger.info(f"Friendship offered by {offerer_name} ({offerer_id}). Message: '{message}', Session: {im_session_id}")
        for handler in self._friendship_offered_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): asyncio.create_task(handler(offerer_id, offerer_name, message, im_session_id))
                else: handler(offerer_id, offerer_name, message, im_session_id)
            except Exception as e: logger.error(f"Error in friendship_offered_handler: {e}", exc_info=True)

    def _fire_friendship_response(self, friend_id: CustomUUID, accepted: bool):
        logger.info(f"Friendship response from {friend_id}: {'Accepted' if accepted else 'Declined'}")
        for handler in self._friendship_response_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): asyncio.create_task(handler(friend_id, accepted))
                else: handler(friend_id, accepted)
            except Exception as e: logger.error(f"Error in friendship_response_handler: {e}", exc_info=True)

    def _fire_online_status_changed(self, friend_uuid: CustomUUID, is_online: bool):
        logger.info(f"Friend online status changed: {friend_uuid} is now {'Online' if is_online else 'Offline'}.")
        args = FriendOnlineStatusEventArgs(friend_uuid, is_online)
        for handler in self._online_status_changed_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): asyncio.create_task(handler(args))
                else: handler(args)
            except Exception as e: logger.error(f"Error in online_status_changed_handler: {e}", exc_info=True)

    def _fire_rights_changed(self, friend_uuid: CustomUUID, their_rights: FriendRights, our_rights: FriendRights):
        logger.info(f"Rights changed for friend {friend_uuid}. Theirs to us: {their_rights!r}, Ours to them: {our_rights!r}")
        args = FriendRightsEventArgs(friend_uuid, their_rights, our_rights)
        for handler in self._rights_changed_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): asyncio.create_task(handler(args))
                else: handler(args)
            except Exception as e: logger.error(f"Error in rights_changed_handler: {e}", exc_info=True)

    def _fire_friend_removed(self, friend_uuid: CustomUUID):
        logger.info(f"Friendship terminated with {friend_uuid}.")
        args = FriendRemovedEventArgs(friend_uuid)
        for handler in self._friend_removed_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): asyncio.create_task(handler(args))
                else: handler(args)
            except Exception as e: logger.error(f"Error in friend_removed_handler: {e}", exc_info=True)


    # --- Packet Processing Methods ---
    def _handle_login_buddylist(self, buddy_list_entries: List[BuddyListEntry] | None):
        if buddy_list_entries is None:
            logger.info("No buddy list provided in login response.")
            return

        logger.info(f"Processing buddy list with {len(buddy_list_entries)} entries.")
        current_friends = {}
        for entry in buddy_list_entries:
            if entry.buddy_id == CustomUUID.ZERO:
                continue

            existing_friend = self.friends.get(entry.buddy_id)
            name = existing_friend.name if existing_friend and existing_friend.name else "" # Preserve name if already known

            friend = FriendInfo(
                uuid=entry.buddy_id,
                name=name,
                our_rights_to_them=entry.our_rights_to_them,
                their_rights_to_us=entry.their_rights_to_us
            )
            current_friends[friend.uuid] = friend
            logger.debug(f"Buddy: {friend.uuid}, OurRightsToThem: {friend.our_rights_to_them!r}, TheirRightsToUs: {friend.their_rights_to_us!r}")

        self.friends = current_friends
        logger.info(f"Friends list populated with {len(self.friends)} friends.")
        # After processing the initial buddy list, we might want to query their online status
        # This could be done here or triggered by an external call after login.
        # For now, let's assume an external call will trigger request_online_statuses if needed.

    def _handle_im_for_friendship(self, im_event_args: 'IMEventArgs'): # Using forward ref for IMEventArgs
        im = im_event_args.im_data

        if im.dialog == InstantMessageDialog.FriendshipOffered:
            self._fire_friendship_offered(im.from_agent_id, im.from_agent_name, im.message, im.im_session_id)

        elif im.dialog == InstantMessageDialog.FriendshipAccepted:
            logger.info(f"Friendship accepted by {im.from_agent_name} ({im.from_agent_id})")
            if im.from_agent_id not in self.friends:
                # This implies that a friendship was accepted by someone not in our buddy list yet.
                # This can happen if the offer was made in a previous session or if login buddy list was incomplete.
                self.friends[im.from_agent_id] = FriendInfo(uuid=im.from_agent_id, name=im.from_agent_name)
                logger.info(f"Friend {im.from_agent_id} added to local list on FriendshipAccepted IM.")
            else: # Update name if it was empty or different
                 self.friends[im.from_agent_id].name = im.from_agent_name

            # Default rights we grant upon accepting their offer.
            # SL typically grants SeeOnline and SeeOnMap by default when a friendship is formed.
            # These are rights WE grant to THEM.
            if friend := self.friends.get(im.from_agent_id):
                original_our_rights = friend.our_rights_given_to_them
                friend.our_rights_given_to_them = FriendRights.CAN_SEE_ONLINE | FriendRights.CAN_SEE_ON_MAP
                if original_our_rights != friend.our_rights_given_to_them:
                    self._fire_rights_changed(friend.uuid, friend.their_rights_given_to_us, friend.our_rights_given_to_them)

            self._fire_friendship_response(im.from_agent_id, True)

        elif im.dialog == InstantMessageDialog.FriendshipDeclined:
            logger.info(f"Friendship declined by {im.from_agent_name} ({im.from_agent_id})")
            self._fire_friendship_response(im.from_agent_id, False)

    def _on_online_notification(self, source_sim: 'Simulator', packet: OnlineNotificationPacket):
        logger.debug(f"Received OnlineNotification from {source_sim.name if source_sim else 'Unknown Sim'}")

        # Process rights updates first, as they might be for friends already marked online
        # Rights they grant us
        for rights_block in packet.buddy_rights_online_array:
            if friend := self.friends.get(rights_block.AgentID):
                new_their_rights = FriendRights(rights_block.Rights)
                if friend.their_rights_given_to_us != new_their_rights:
                    friend.their_rights_given_to_us = new_their_rights
                    self._fire_rights_changed(friend.uuid, friend.their_rights_given_to_us, friend.our_rights_given_to_them)
            else:
                logger.debug(f"RightsOnline for non-friend {rights_block.AgentID} in OnlineNotification.")

        # Rights we grant them
        for rights_block in packet.buddy_rights_friend_array:
            if friend := self.friends.get(rights_block.AgentID):
                new_our_rights = FriendRights(rights_block.Rights)
                if friend.our_rights_given_to_them != new_our_rights:
                    friend.our_rights_given_to_them = new_our_rights
                    self._fire_rights_changed(friend.uuid, friend.their_rights_given_to_us, friend.our_rights_given_to_them)
            else:
                logger.debug(f"RightsFriend for non-friend {rights_block.AgentID} in OnlineNotification.")

        # Process online status for agents listed in agent_block_array
        for agent_block in packet.agent_block_array:
            if friend := self.friends.get(agent_block.AgentID):
                if not friend.online: # Only fire event if status truly changed
                    friend.online = True
                    self._fire_online_status_changed(friend.uuid, True)
            else:
                # This could be a non-friend agent who we have some rights with (e.g. group member)
                # For FriendsManager, we are primarily interested in friends.
                logger.debug(f"OnlineNotification AgentBlock for non-friend {agent_block.AgentID}")


    def _on_offline_notification(self, source_sim: 'Simulator', packet: OfflineNotificationPacket):
        logger.debug(f"Received OfflineNotification from {source_sim.name if source_sim else 'Unknown Sim'}")
        for block in packet.agent_block_array:
            if friend := self.friends.get(block.AgentID):
                if friend.online: # Only fire event if status changed
                    friend.online = False
                    self._fire_online_status_changed(friend.uuid, False)
            else:
                logger.debug(f"OfflineNotification for non-friend {block.AgentID}")

    def _on_agent_online_status(self, source_sim: 'Simulator', packet: AgentOnlineStatusPacket):
        logger.debug(f"Received AgentOnlineStatus from {source_sim.name if source_sim else 'Unknown Sim'}")
        for block in packet.agent_block_array:
            if friend := self.friends.get(block.AgentID):
                if friend.online != block.Online: # Only fire event if status changed
                    friend.online = block.Online
                    self._fire_online_status_changed(friend.uuid, block.Online)
                else: # Status is the same, but update anyway if needed (e.g. from direct query)
                    friend.online = block.Online
            else:
                logger.debug(f"AgentOnlineStatus for non-friend {block.AgentID}: Online={block.Online}")


    # --- Public Methods ---
    async def offer_friendship(self, target_uuid: CustomUUID, message: str = "Will you be my friend?"):
        if not self.client.self or not self.client.network.current_sim:
            logger.error("Cannot offer friendship: Not connected or agent info missing.")
            return False

        packet = OfferFriendshipPacket(
            self.client.self.agent_id,
            self.client.self.session_id,
            target_uuid,
            message
        )
        await self.client.network.send_packet(packet, self.client.network.current_sim)
        logger.info(f"Sent friendship offer to {target_uuid}.")
        return True

    async def accept_friendship_offer(self, offerer_uuid: CustomUUID, im_session_id_as_transaction_id: CustomUUID):
        if not self.client.self or not self.client.network.current_sim or not self.client.inventory or not self.client.inventory.inventory_root_uuid:
            logger.error("Cannot accept friendship: Not connected, agent info, inventory manager or inventory root missing.")
            return False

        packet = AcceptFriendshipPacket(
            self.client.self.agent_id,
            self.client.self.session_id,
            transaction_id=im_session_id_as_transaction_id,
            my_inventory_root=self.client.inventory.inventory_root_uuid
        )
        await self.client.network.send_packet(packet, self.client.network.current_sim)
        logger.info(f"Sent AcceptFriendshipPacket for offer from {offerer_uuid} (Transaction: {im_session_id_as_transaction_id}).")
        # Optimistically add friend or update status; server will confirm with Online/Offline notifications or updated BuddyList
        if offerer_uuid not in self.friends:
            self.friends[offerer_uuid] = FriendInfo(uuid=offerer_uuid) # Name will be updated by IM typically
        # Rights are not known from this action alone, will come from BuddyList update.
        return True

    async def grant_rights(self, friend_uuid: CustomUUID, rights: FriendRights):
        """Grants specified rights to a friend."""
        if not self.client.self or not self.client.network.current_sim:
            logger.error("Cannot grant rights: Not connected or agent info missing.")
            return False

        if friend := self.friends.get(friend_uuid):
            logger.info(f"Granting rights {rights!r} to friend {friend_uuid}.")
            packet = ChangeUserRightsPacket(
                agent_id=self.client.self.agent_id,
                session_id=self.client.self.session_id,
                friend_uuid=friend_uuid,
                new_rights=rights.value # Send the integer value
            )
            await self.client.network.send_packet(packet, self.client.network.current_sim)

            # Optimistically update local state and fire event
            # The server might also send an OnlineNotification to confirm, which would re-assert these.
            if friend.our_rights_given_to_them != rights:
                friend.our_rights_given_to_them = rights
                self._fire_rights_changed(friend.uuid, friend.their_rights_given_to_us, friend.our_rights_given_to_them)
            return True
        else:
            logger.warning(f"Cannot grant rights to non-friend {friend_uuid}")
            return False

    async def terminate_friendship(self, friend_uuid: CustomUUID):
        """Terminates friendship with the specified agent."""
        if not self.client.self or not self.client.network.current_sim:
            logger.error("Cannot terminate friendship: Not connected or agent info missing.")
            return False

        logger.info(f"Terminating friendship with {friend_uuid}.")
        packet = TerminateFriendshipPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            friend_to_remove_uuid=friend_uuid
        )
        await self.client.network.send_packet(packet, self.client.network.current_sim)

        if friend_uuid in self.friends:
            del self.friends[friend_uuid]

        self._fire_friend_removed(friend_uuid)
        return True

    async def request_online_statuses(self, agent_uuids: list[CustomUUID]):
        """Requests the online status for a list of agent UUIDs."""
        if not self.client.self or not self.client.network.current_sim: # Check self for agent_id
            logger.error("Cannot request online statuses: Not connected or AgentManager not available.")
            return
        if not agent_uuids:
            logger.debug("request_online_statuses called with an empty list.")
            return

        # C# LibreMetaverse typically sends one FindAgentPacket per agent ID.
        # However, the packet structure supports multiple. For simplicity and efficiency,
        # this implementation will send them in batches if the packet structure allows,
        # or one by one if that's more stable/aligned with observed server behavior.
        # The FindAgentPacket defined takes a list, implying it can handle multiple.

        logger.info(f"Requesting online status for {len(agent_uuids)} agents.")
        # If servers prefer one agent per packet, loop here:
        # for target_uuid in agent_uuids:
        #     packet = FindAgentPacket(self.client.self.agent_id, [target_uuid])
        #     await self.client.network.send_packet(packet, self.client.network.current_sim)
        # else, send one packet with all:
        packet = FindAgentPacket(self.client.self.agent_id, agent_uuids)
        await self.client.network.send_packet(packet, self.client.network.current_sim)

    def get_friend(self, friend_uuid: CustomUUID) -> FriendInfo | None:
        return self.friends.get(friend_uuid)

    def is_friend(self, agent_uuid: CustomUUID) -> bool:
        return agent_uuid in self.friends
