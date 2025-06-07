import logging
import asyncio
from typing import TYPE_CHECKING, Dict, Tuple, List, Callable

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.enums import WearableType
from pylibremetaverse.types.primitive import Primitive
from pylibremetaverse.network.packets_appearance import (
    AgentWearablesRequestPacket, AgentWearablesUpdatePacket,
    AgentSetAppearancePacket, AvatarAppearancePacket, AgentIsNowWearingPacket
)
from pylibremetaverse.network.packet_protocol import IncomingPacket
from pylibremetaverse.network.packets_base import Packet, PacketType


if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator
    from pylibremetaverse.types.inventory_defs import InventoryItem # For type hinting

logger = logging.getLogger(__name__)

WearablesUpdatedHandler = Callable[[Dict[WearableType, Tuple[CustomUUID, CustomUUID]]], None]
# Could add AppearanceUpdatedHandler = Callable[[AppearanceManager], None] if needed for full appearance

class AppearanceManager:
    VISUAL_PARAM_COUNT = 256

    def __init__(self, client: 'GridClient'):
        self.client = client
        self.wearables: Dict[WearableType, Tuple[CustomUUID, CustomUUID]] = {}
        self.visual_params: List[float] = [0.0] * self.VISUAL_PARAM_COUNT
        self.texture_entry_bytes: bytes | None = None
        self.serial_num: int = 0
        self.agent_size: Vector3 = Vector3(0.45, 0.6, 1.8) # Typical default

        # New attributes for managing current outfit with full InventoryItem details
        self.current_outfit_folder_uuid: CustomUUID | None = None # TODO: To be fetched via CAPS eventually
        self.current_wearables_by_type: Dict[WearableType, InventoryItem] = {}

        self._wearables_updated_handlers: List[WearablesUpdatedHandler] = []
        # self._appearance_updated_handlers: List[AppearanceUpdatedHandler] = [] # For AvatarAppearance

        if self.client.network:
             self.client.network.register_packet_handler(
                 PacketType.AgentWearablesUpdate, self._on_agent_wearables_update_wrapper)
             self.client.network.register_packet_handler(
                 PacketType.AvatarAppearance, self._on_avatar_appearance_wrapper)
        else: logger.error("AppearanceManager: NetworkManager not available at init.")

    def _on_agent_wearables_update_wrapper(self, source_sim: 'Simulator', packet: Packet):
        if isinstance(packet, AgentWearablesUpdatePacket): self._on_agent_wearables_update(source_sim, packet)
        else: logger.warning(f"AppearanceManager: Bad packet type {type(packet).__name__} for wearables wrapper.")

    def _on_avatar_appearance_wrapper(self, source_sim: 'Simulator', packet: Packet):
        if isinstance(packet, AvatarAppearancePacket): self._on_avatar_appearance(source_sim, packet)
        else: logger.warning(f"AppearanceManager: Bad packet type {type(packet).__name__} for avatar appearance wrapper.")

    def register_wearables_updated_handler(self, callback: WearablesUpdatedHandler):
        if callback not in self._wearables_updated_handlers: self._wearables_updated_handlers.append(callback)
    def unregister_wearables_updated_handler(self, callback: WearablesUpdatedHandler):
        if callback in self._wearables_updated_handlers: self._wearables_updated_handlers.remove(callback)

    async def request_wearables(self):
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.handshake_complete: logger.warning("Cannot request wearables: No sim."); return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO: logger.warning("Cannot request wearables: AgentID not set."); return
        req = AgentWearablesRequestPacket(self.client.self.agent_id, self.client.self.session_id)
        await self.client.network.send_packet(req, current_sim); logger.info("Sent AgentWearablesRequestPacket.")

    def _on_agent_wearables_update(self, source_sim: 'Simulator', packet: AgentWearablesUpdatePacket):
        if packet.agent_data.AgentID != self.client.self.agent_id: logger.debug(f"Ignoring wearables for other agent: {packet.agent_data.AgentID}"); return

        self.serial_num = packet.agent_data.SerialNum
        # Store visual_version if needed: self.visual_version = packet.agent_data.VisualVersion
        logger.info(f"Rcvd AgentWearablesUpdate. Serial:{self.serial_num}, VisualVer:{packet.agent_data.VisualVersion}")

        new_wearables_id_pairs: Dict[WearableType, Tuple[CustomUUID, CustomUUID]] = {}
        for wb in packet.wearable_data:
            try:
                wear_type = WearableType(wb.WearableType)
                new_wearables_id_pairs[wear_type] = (wb.ItemID, wb.AssetID)
            except ValueError:
                logger.warning(f"Unknown WearableType value: {wb.WearableType}")
        self.wearables = new_wearables_id_pairs # This stores (ItemID, AssetID)

        # Populate self.current_wearables_by_type by fetching InventoryItem for each wearable
        logger.info("Received AgentWearablesUpdate. Attempting to update current_wearables_by_type.")

        # Synchronous placeholder using client.inventory.get_item():
        if self.client.inventory:
            # Create a temporary dictionary to build the new state
            updated_current_wearables_by_type: Dict[WearableType, InventoryItem] = {}
            for wt, (item_id, asset_id) in self.wearables.items():
                inv_item = self.client.inventory.get_item(item_id) # Try synchronous get first
                if inv_item:
                    updated_current_wearables_by_type[wt] = inv_item
                    logger.debug(f"Updated current_wearables_by_type for {wt.name} with fetched item {inv_item.name}")
                else:
                    # If not found, it might not be in the skeleton yet, or fetch_item (async) would be needed.
                    # For now, we log and might have an incomplete current_wearables_by_type.
                    # If an item previously in current_wearables_by_type is no longer reported by AgentWearablesUpdate,
                    # it will be implicitly removed by assigning the new dictionary.
                    logger.info(f"Placeholder: InventoryItem for ItemID: {item_id} (AssetID: {asset_id}, Type: {wt.name}) not found synchronously. Full fetch would be async.")
            self.current_wearables_by_type = updated_current_wearables_by_type
        else:
            logger.warning("InventoryManager not available, cannot populate full current_wearables_by_type.")


        if len(packet.visual_param) > 0:
            max_idx = min(len(packet.visual_param), self.VISUAL_PARAM_COUNT)
            for i in range(max_idx): self.visual_params[i] = (packet.visual_param[i].ParamValue & 0xFF) / 255.0
            if len(packet.visual_param) != self.VISUAL_PARAM_COUNT and len(packet.visual_param) != 0:
                 logger.warning(f"AgentWearablesUpdate: Expected {self.VISUAL_PARAM_COUNT} VPs, got {len(packet.visual_param)}")

        logger.info(f"Updated wearables (ID pairs): {len(self.wearables)} items. Visuals updated (first 5: {[f'{x:.2f}' for x in self.visual_params[:5]]}). current_wearables_by_type has {len(self.current_wearables_by_type)} items.")
        for handler in self._wearables_updated_handlers:
            try: handler(self.wearables.copy()) # Handlers still get the (ItemID, AssetID) dict
            except Exception as e: logger.error(f"Error in wearables_updated_handler: {e}")

    async def set_appearance(self, texture_entry_override: bytes | None = None,
                             visual_params_override: list[float] | None = None,
                             size_override: Vector3 | None = None):
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.handshake_complete: logger.warning("Cannot set appearance: No sim."); return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO: logger.warning("Cannot set appearance: AgentID not set."); return

        self.serial_num = (self.serial_num + 1) & 0xFFFFFFFF

        current_te = texture_entry_override if texture_entry_override is not None else self.texture_entry_bytes
        if current_te is None:
            logger.warning("No TE data for AgentSetAppearance. Sending default empty TE.")
            current_te = bytes([0] * Primitive.TEXTURE_ENTRY_DEFAULT_SIZE)

        current_vp_float = visual_params_override if visual_params_override is not None else self.visual_params
        vp_bytes_list: List[int] = [(max(0, min(255, int(v * 255.0)))) for v in current_vp_float]
        if len(vp_bytes_list) != self.VISUAL_PARAM_COUNT: # Ensure correct length
            vp_bytes_list.extend([0] * (self.VISUAL_PARAM_COUNT - len(vp_bytes_list)))
            vp_bytes_list = vp_bytes_list[:self.VISUAL_PARAM_COUNT]

        current_size = size_override if size_override is not None else self.agent_size
        if current_size.magnitude_squared() < 1e-5 : current_size = Vector3(0.45, 0.6, 1.8)

        set_packet = AgentSetAppearancePacket(
            agent_id=self.client.self.agent_id, session_id=self.client.self.session_id,
            serial_num=self.serial_num, size_vec=current_size,
            texture_entry_bytes=current_te, visual_params_bytes=vp_bytes_list
        )
        await self.client.network.send_packet(set_packet, current_sim)
        logger.info(f"Sent AgentSetAppearancePacket (Serial: {self.serial_num}).")

    def _on_avatar_appearance(self, source_sim: 'Simulator', packet: AvatarAppearancePacket):
        if packet.sender.ID == self.client.self.agent_id:
            logger.info(f"Received self AvatarAppearancePacket. IsTrial: {packet.sender.IsTrial}")
            self.texture_entry_bytes = packet.object_data.TextureEntry

            new_vp: List[float] = [0.0] * self.VISUAL_PARAM_COUNT
            if len(packet.visual_param) > 0:
                max_idx = min(len(packet.visual_param), self.VISUAL_PARAM_COUNT)
                for i in range(max_idx): new_vp[i] = (packet.visual_param[i].ParamValue & 0xFF) / 255.0
                if len(packet.visual_param) != self.VISUAL_PARAM_COUNT and len(packet.visual_param) != 0 :
                     logger.warning(f"Own AvatarAppearance: VPs count {len(packet.visual_param)} vs {self.VISUAL_PARAM_COUNT}")
            self.visual_params = new_vp
            logger.info(f"Own appearance updated via AvatarAppearance. TE len: {len(self.texture_entry_bytes if self.texture_entry_bytes else [])}. "
                        f"Visuals (first 5: {[f'{x:.2f}' for x in self.visual_params[:5]]}).")
            # TODO: Fire general appearance_updated event if needed
        else:
            logger.debug(f"Rcvd AvatarAppearance for other: {packet.sender.ID}. TE len: {len(packet.object_data.TextureEntry)}. VP count: {len(packet.visual_param)}")

    def get_wearable_item(self,wt:WearableType)->Tuple[CustomUUID,CustomUUID]|None:return self.wearables.get(wt)
    def get_visual_param_value(self,idx:int)->float:return self.visual_params[idx] if 0<=idx<len(self.visual_params) else 0.0

    async def _send_is_now_wearing(self, final_wearables_for_packet: List[Tuple[CustomUUID, WearableType]]):
        """Helper to construct and send AgentIsNowWearingPacket."""
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.handshake_complete:
            logger.warning("Cannot send AgentIsNowWearing: No sim or not connected.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot send AgentIsNowWearing: AgentID not set.")
            return

        packet = AgentIsNowWearingPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            items=final_wearables_for_packet
        )
        await self.client.network.send_packet(packet, current_sim)
        logger.info(f"Sent AgentIsNowWearingPacket with {len(final_wearables_for_packet)} items.")

        # Optionally, trigger a standard AgentSetAppearance to encourage server-side rebake/update.
        # This uses the currently stored TE and VPs.
        # This might be heavy-handed if AgentIsNowWearing is sufficient.
        # await self.set_appearance()
        # logger.info("Followed AgentIsNowWearing with AgentSetAppearance.")


    async def wear_items(self, items_to_wear: List[InventoryItem]):
        """
        Puts on the specified wearable items.
        This simplified version sends AgentIsNowWearing and relies on the server for baking.
        """
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot wear items: AgentID not set."); return
        if not items_to_wear:
            logger.info("wear_items: No items specified to wear.")
            return

        # Start with a copy of the current wearables
        new_outfit = self.current_wearables_by_type.copy()
        logger.debug(f"wear_items: Starting with {len(new_outfit)} items in current_wearables_by_type. Items to wear: {len(items_to_wear)}")

        changed = False
        for item in items_to_wear:
            wear_type = item.wearable_type
            if wear_type is None or wear_type == WearableType.Invalid:
                logger.warning(f"Item '{item.name}' (UUID: {item.uuid}, InvType: {item.inv_type}) is not a valid wearable type for wearing.")
                continue

            if item.uuid == CustomUUID.ZERO or item.asset_uuid == CustomUUID.ZERO:
                logger.warning(f"Item '{item.name}' has zero ItemID or AssetID, cannot wear.")
                continue

            if wear_type not in new_outfit or new_outfit[wear_type].uuid != item.uuid:
                logger.info(f"Adding/replacing {wear_type.name} with item {item.name} ({item.uuid})")
                new_outfit[wear_type] = item
                changed = True
            else:
                logger.info(f"Item {item.name} ({wear_type.name}) is already the current item in that slot.")

        if not changed:
            logger.info("wear_items: No changes to current outfit.")
            # If nothing changed, we could skip sending AgentIsNowWearing,
            # but sending it ensures server is in sync with client's view of current_wearables_by_type.
            # For now, send anyway to ensure sync, or return if strict no-op is desired.
            # return

        # Prepare list for AgentIsNowWearingPacket: (ItemID, WearableType enum member)
        final_wearables_for_packet: List[Tuple[CustomUUID, WearableType]] = []
        for wt, inv_item in new_outfit.items():
            final_wearables_for_packet.append((inv_item.uuid, wt)) # wt is already WearableType enum

        await self._send_is_now_wearing(final_wearables_for_packet)

        # Update the internal state
        self.current_wearables_by_type = new_outfit
        # Also update self.wearables (ItemID, AssetID dict) for consistency with AgentWearablesUpdate
        self.wearables = {wt: (inv_item.uuid, inv_item.asset_uuid) for wt, inv_item in new_outfit.items()}

        logger.info(f"wear_items: Completed. Current outfit has {len(self.current_wearables_by_type)} items.")

    async def take_off_items(self, items_to_take_off: List[InventoryItem]):
        """
        Takes off the specified wearable items.
        This simplified version sends AgentIsNowWearing and relies on the server for baking.
        """
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot take off items: AgentID not set."); return
        if not items_to_take_off:
            logger.info("take_off_items: No items specified to take off.")
            return

        new_outfit = self.current_wearables_by_type.copy()
        logger.debug(f"take_off_items: Starting with {len(new_outfit)} items. Items to take off: {len(items_to_take_off)}")

        items_actually_removed_count = 0
        for item_to_remove in items_to_take_off:
            wear_type_to_remove = item_to_remove.wearable_type
            if wear_type_to_remove is None or wear_type_to_remove == WearableType.Invalid:
                logger.warning(f"Item '{item_to_remove.name}' (InvType: {item_to_remove.inv_type}) cannot be taken off by type.")
                continue

            if wear_type_to_remove in new_outfit:
                # Check if it's the exact item or just any item in that slot
                if new_outfit[wear_type_to_remove].uuid == item_to_remove.uuid:
                    logger.info(f"Removing {wear_type_to_remove.name} (item {item_to_remove.name}, {item_to_remove.uuid})")
                    del new_outfit[wear_type_to_remove]
                    items_actually_removed_count +=1
                else:
                    logger.info(f"Item {item_to_remove.name} not found in slot {wear_type_to_remove.name} (current: {new_outfit[wear_type_to_remove].name}). Not removing.")
            else:
                logger.info(f"No item in slot {wear_type_to_remove.name} to remove for {item_to_remove.name}.")

        if items_actually_removed_count == 0 and len(items_to_take_off) > 0 : # Only skip if items were given but none were relevant
            logger.info("take_off_items: No specified items were actually worn in those slots or removed.")
            # If no items were effectively removed, sending AgentIsNowWearing might be redundant
            # unless the goal is to strictly enforce self.current_wearables_by_type on the server.
            # For now, if nothing changed from the list of items to take off, we can skip sending.
            if not any(item.wearable_type in self.current_wearables_by_type and self.current_wearables_by_type[item.wearable_type].uuid == item.uuid for item in items_to_take_off):
                 return


        final_wearables_for_packet: List[Tuple[CustomUUID, WearableType]] = []
        for wt, inv_item in new_outfit.items():
            final_wearables_for_packet.append((inv_item.uuid, wt))

        await self._send_is_now_wearing(final_wearables_for_packet)

        self.current_wearables_by_type = new_outfit
        self.wearables = {wt: (inv_item.uuid, inv_item.asset_uuid) for wt, inv_item in new_outfit.items()}
        logger.info(f"take_off_items: Completed. Current outfit has {len(self.current_wearables_by_type)} items.")
