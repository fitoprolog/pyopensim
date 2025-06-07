import logging
import asyncio
from typing import TYPE_CHECKING, Dict, Tuple, List, Callable

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.enums import WearableType, AssetType # Added AssetType here explicitly
from pylibremetaverse.types.primitive import Primitive, TextureEntry, TextureEntryFace, MAX_AVATAR_FACES
from pylibremetaverse.network.packets_appearance import (
    AgentWearablesRequestPacket, AgentWearablesUpdatePacket,
    AgentSetAppearancePacket, AvatarAppearancePacket, AgentIsNowWearingPacket
)
from pylibremetaverse.network.packet_protocol import IncomingPacket
from pylibremetaverse.network.packets_base import Packet, PacketType
# from pylibremetaverse.types.enums import AssetType # Already imported
from pylibremetaverse.assets import AssetWearable, AssetTexture # For type checking in callback
# Default Texture UUIDs (replace with actual defaults from SL if known, or use a placeholder)
from pylibremetaverse.types.default_textures import (
    DEFAULT_SKIN_TEXTURE, DEFAULT_EYES_TEXTURE, DEFAULT_HAIR_TEXTURE,
    DEFAULT_SHIRT_TEXTURE, DEFAULT_PANTS_TEXTURE
)


if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator
    from pylibremetaverse.types.inventory_defs import InventoryItem # For type hinting
    from pylibremetaverse.assets import Asset # For type hint in callback

logger = logging.getLogger(__name__)

WearablesUpdatedHandler = Callable[[Dict[WearableType, Tuple[CustomUUID, CustomUUID]]], None]
# Could add AppearanceUpdatedHandler = Callable[[AppearanceManager], None] if needed for full appearance

class AppearanceManager:
    VISUAL_PARAM_COUNT = 256

    # SL Avatar Face Indices (referencing common bake layer names)
    # These must map to indices 0 to MAX_AVATAR_FACES-1
    AVATAR_FACE_HEAD = 0
    AVATAR_FACE_UPPER_BODY = 1 # Includes chest, back, stomach
    AVATAR_FACE_LOWER_BODY = 2 # Includes pelvis, legs
    AVATAR_FACE_EYES = 3       # Iris
    AVATAR_FACE_HAIR = 4
    AVATAR_FACE_UPPER_ARM = 5  # Shoulders / Upper sleeves area
    AVATAR_FACE_LOWER_ARM = 6  # Forearms / Gloves area
    AVATAR_FACE_HANDS = 7      # Hands (often part of lower arm texture)
    AVATAR_FACE_UPPER_LEG = 8  # Upper part of legs (pants)
    AVATAR_FACE_LOWER_LEG = 9  # Lower part of legs (boots/shoes)
    AVATAR_FACE_FOOT = 10      # Feet (often part of lower leg texture)
    AVATAR_FACE_SKIRT = 11     # Skirt bake layer
    # Auxiliary faces (12-20) can be used for tattoos, alpha layers, physics layers, etc.
    AVATAR_FACE_AUX_1 = 12 # Example placeholder for aux layers
    AVATAR_FACE_AUX_2 = 13
    AVATAR_FACE_AUX_3 = 14
    # ... up to MAX_AVATAR_FACES - 1 (which is 21 if MAX_AVATAR_FACES is 22)

    AVATAR_FACE_COUNT = MAX_AVATAR_FACES # Use the definition from primitive.py (currently 22)


    # Refined mapping from WearableType to a list of avatar face indices
    # This mapping determines which TextureEntryFace(s) a wearable's texture should apply to.
    WEARABLE_TO_FACE_INDICES_MAP: Dict[WearableType, List[int]] = {
        WearableType.Skin: [AVATAR_FACE_HEAD, AVATAR_FACE_UPPER_BODY, AVATAR_FACE_LOWER_BODY,
                            AVATAR_FACE_UPPER_ARM, AVATAR_FACE_LOWER_ARM, AVATAR_FACE_HANDS,
                            AVATAR_FACE_UPPER_LEG, AVATAR_FACE_LOWER_LEG, AVATAR_FACE_FOOT],
        WearableType.Eyes: [AVATAR_FACE_EYES],
        WearableType.Hair: [AVATAR_FACE_HAIR],
        WearableType.Shirt: [AVATAR_FACE_UPPER_BODY, AVATAR_FACE_UPPER_ARM], # Shirt often covers upper body and upper arms
        WearableType.Pants: [AVATAR_FACE_LOWER_BODY, AVATAR_FACE_UPPER_LEG, AVATAR_FACE_LOWER_LEG], # Pants cover general lower body and legs
        WearableType.Shoes: [AVATAR_FACE_FOOT, AVATAR_FACE_LOWER_LEG], # Shoes typically cover feet and part of lower leg
        WearableType.Socks: [AVATAR_FACE_FOOT, AVATAR_FACE_LOWER_LEG], # Socks are similar to shoes coverage
        WearableType.Jacket: [AVATAR_FACE_UPPER_BODY, AVATAR_FACE_UPPER_ARM, AVATAR_FACE_LOWER_ARM], # Jacket can cover more of arms
        WearableType.Gloves: [AVATAR_FACE_HANDS, AVATAR_FACE_LOWER_ARM],
        WearableType.Undershirt: [AVATAR_FACE_UPPER_BODY], # Typically just torso
        WearableType.Underpants: [AVATAR_FACE_LOWER_BODY], # Typically just pelvis area
        WearableType.Skirt: [AVATAR_FACE_SKIRT, AVATAR_FACE_LOWER_BODY], # Skirt layer and potentially part of lower body
        WearableType.Tattoo: [AVATAR_FACE_HEAD, AVATAR_FACE_UPPER_BODY, AVATAR_FACE_LOWER_BODY,
                              AVATAR_FACE_UPPER_ARM, AVATAR_FACE_LOWER_ARM], # Tattoos can apply broadly
        WearableType.Alpha: [], # Alpha layers don't set textures but control transparency, handled differently
        # Shape and Physics don't directly map to textures in TextureEntry this way.
    }


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

        # After updating self.wearables, request the actual wearable assets
        for wear_type, (item_id, asset_id) in self.wearables.items():
            if asset_id != CustomUUID.ZERO and item_id != CustomUUID.ZERO:
                # Determine AssetType based on WearableType
                # This is a simplified mapping. Bodyparts like shape, skin, hair, eyes are AssetType.Bodypart.
                # Others are AssetType.Clothing.
                asset_type_for_request = AssetType.Unknown
                if wear_type in [WearableType.Shape, WearableType.Skin, WearableType.Hair, WearableType.Eyes]:
                    asset_type_for_request = AssetType.Bodypart
                elif wear_type != WearableType.Invalid: # Most other wearables are Clothing
                    asset_type_for_request = AssetType.Clothing

                if asset_type_for_request != AssetType.Unknown:
                    logger.debug(f"Requesting wearable asset {asset_id} (type: {asset_type_for_request.name}) for item {item_id} (slot: {wear_type.name})")
                    asyncio.create_task(self.client.assets.request_asset_xfer(
                        filename=str(asset_id), # Filename is not strictly used by modern Xfer, but pass asset_id
                        use_big_packets=False, # Not relevant for CAPS-based Xfer usually expected for assets
                        vfile_id=asset_id, # The actual asset UUID to fetch
                        vfile_type=asset_type_for_request,
                        item_id_for_callback=item_id, # Use inventory item ID for context in callback
                        callback_on_complete=self._handle_wearable_asset_download
                    ))
                else:
                    logger.warning(f"Cannot determine AssetType for WearableType {wear_type.name} to request asset {asset_id}.")

        for handler in self._wearables_updated_handlers:
            try: handler(self.wearables.copy()) # Handlers still get the (ItemID, AssetID) dict
            except Exception as e: logger.error(f"Error in wearables_updated_handler: {e}")

    def _handle_wearable_asset_download(self, success: bool, asset_obj_or_data: Any, # Asset | bytes | None
                                        asset_type_enum: AssetType, asset_uuid: CustomUUID,
                                        vfile_id_for_callback: CustomUUID | None,
                                        error_message: str | None = None):
        item_id = vfile_id_for_callback # This was the inventory item_id
        if not item_id:
            logger.error(f"Received wearable asset download callback for asset {asset_uuid} but no item_id context.")
            return

        if success:
            if isinstance(asset_obj_or_data, AssetWearable) and asset_obj_or_data.loaded_successfully:
                # Find the WearableType slot this item_id corresponds to
                wear_type_slot: WearableType | None = None
                for wt, (i_id, a_id) in self.wearables.items():
                    if i_id == item_id:
                        wear_type_slot = wt
                        break

                if wear_type_slot:
                    # Replace InventoryItem placeholder with actual parsed AssetWearable
                    self.current_wearables_by_type[wear_type_slot] = asset_obj_or_data
                    logger.info(f"Successfully parsed and stored wearable asset {asset_uuid} (Type: {asset_obj_or_data.wearable_type.name}) for item {item_id} in slot {wear_type_slot.name}.")
                    # TODO: Potentially fire an event indicating a wearable's details are now fully known
                else:
                    logger.warning(f"Received parsed AssetWearable {asset_uuid} for item {item_id}, but couldn't find its WearableType slot in self.wearables.")

            elif isinstance(asset_obj_or_data, AssetTexture) and asset_obj_or_data.loaded_successfully:
                # This might be for a skin/tattoo/alpha if they are directly textures rather than AssetWearable LLSD
                logger.info(f"Received AssetTexture {asset_uuid} for item {item_id} (AssetType: {asset_type_enum.name}). AppearanceManager might need to handle this if it's part of appearance (e.g. skin).")
                # For now, current_wearables_by_type expects AssetWearable or InventoryItem.
                # If a wearable slot (like Skin) is directly an AssetTexture, this logic needs adjustment
                # or AssetManager needs to wrap it in a simple AssetWearable if appropriate.

            elif isinstance(asset_obj_or_data, self.client.assets.Asset) and asset_obj_or_data.loaded_successfully:
                 logger.info(f"Received generic parsed asset {asset_uuid} (Type: {asset_type_enum.name}) for item {item_id}. Raw data stored.")
            elif isinstance(asset_obj_or_data, bytes):
                 logger.info(f"Received raw asset data for {asset_uuid} (Type: {asset_type_enum.name}) for item {item_id}. Length: {len(asset_obj_or_data)}.")
            else:
                logger.warning(f"Wearable asset download for {asset_uuid} (item {item_id}) was successful but data is unexpected type: {type(asset_obj_or_data)}")
        else:
            logger.warning(f"Failed to download/parse wearable asset {asset_uuid} for item {item_id}. Error: {error_message}")


    async def set_appearance(self,
                             visual_params_override: list[float] | None = None,
                             size_override: Vector3 | None = None):
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.handshake_complete: logger.warning("Cannot set appearance: No sim."); return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO: logger.warning("Cannot set appearance: AgentID not set."); return

        self.serial_num = (self.serial_num + 1) & 0xFFFFFFFF

        # Construct TextureEntry
        new_te = TextureEntry() # Initializes with default face and MAX_AVATAR_FACES of None

        # Apply default base textures (skin, eyes, hair)
        # These will be overridden by worn items if they exist for these slots.
        default_skin_face = TextureEntryFace(texture_id=DEFAULT_SKIN_TEXTURE)
        default_eyes_face = TextureEntryFace(texture_id=DEFAULT_EYES_TEXTURE)
        default_hair_face = TextureEntryFace(texture_id=DEFAULT_HAIR_TEXTURE)

        # Default mapping for base avatar parts - this is highly simplified.
        # A full system considers multiple faces for skin, etc.
        # For now, map to primary bake indices.
        head_face_idx = self._map_wearable_type_to_avatar_face_index(WearableType.Shape) # Head
        eyes_face_idx = self._map_wearable_type_to_avatar_face_index(WearableType.Eyes)
        hair_face_idx = self._map_wearable_type_to_avatar_face_index(WearableType.Hair)

        # Apply default base textures (skin, eyes, hair)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_HEAD)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_UPPER_BODY)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_LOWER_BODY)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_UPPER_ARM)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_LOWER_ARM)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_HANDS)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_UPPER_LEG)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_LOWER_LEG)
        self._apply_default_texture_to_face(new_te, DEFAULT_SKIN_TEXTURE, self.AVATAR_FACE_FOOT)
        # Eyes and Hair defaults
        self._apply_default_texture_to_face(new_te, DEFAULT_EYES_TEXTURE, self.AVATAR_FACE_EYES)
        self._apply_default_texture_to_face(new_te, DEFAULT_HAIR_TEXTURE, self.AVATAR_FACE_HAIR)

        # Layer wearables (simple layering: higher WearableType value overrides lower for same face)
        # Sorting ensures that items like jackets are applied after shirts.
        sorted_wearables = sorted(self.current_wearables_by_type.items(), key=lambda item: item[0].value)

        for wear_type, wearable_item in sorted_wearables:
            # We need the parsed AssetWearable for its texture dictionary
            if not isinstance(wearable_item, AssetWearable) or not wearable_item.loaded_successfully:
                logger.debug(f"Skipping wearable {wear_type.name}: not a loaded AssetWearable (Type: {type(wearable_item).__name__}).")
                continue # Skip if not a parsed AssetWearable

            wearable_asset: AssetWearable = wearable_item
            target_face_indices = self._get_target_face_indices_for_wearable(wear_type)

            if not target_face_indices:
                logger.debug(f"No target faces defined for wearable type {wear_type.name}. Skipping.")
                continue

            # Get primary texture from wearable. For SL, textures are usually indexed 0, 1, ...
            # We'll try to get texture by index 0 as a common case for the "main" texture.
            # More complex wearables might use named keys or multiple indices.
            primary_texture_uuid = wearable_asset.textures.get(0)
            if not primary_texture_uuid and wearable_asset.textures: # Fallback to the first texture if index 0 is not present
                primary_texture_uuid = next(iter(wearable_asset.textures.values()), None)

            if primary_texture_uuid and primary_texture_uuid != CustomUUID.ZERO:
                for face_idx in target_face_indices:
                    if 0 <= face_idx < MAX_AVATAR_FACES:
                        # Get or create the TextureEntryFace
                        face = new_te.face_textures[face_idx]
                        if face is None:
                            face = TextureEntryFace()
                            new_te.face_textures[face_idx] = face

                        face.texture_id = primary_texture_uuid
                        # TODO: Apply color tint from wearable_asset.parameters if applicable.
                        # Example: if 77 in wearable_asset.parameters: face.color.R = wearable_asset.parameters[77]
                        # This requires TextureEntryFace to have a color attribute and for param IDs to be known.
                        logger.debug(f"Applied texture {primary_texture_uuid} from wearable {wearable_asset.name} (Type: {wear_type.name}) to avatar face {face_idx}")
                    else:
                        logger.warning(f"Invalid face index {face_idx} for wearable {wear_type.name}.")
            else:
                logger.debug(f"Wearable {wearable_asset.name} (Type: {wear_type.name}) has no primary texture or it's a zero UUID.")

        # If self.texture_entry_bytes (from AvatarAppearance) is available and parsing it is an option,
        # it could be used as a base. However, this subtask focuses on constructing a new one.

        # Use the new to_avatar_appearance_bytes method
        # This requires a map of default textures for each face index.
        # This map should be available in DefaultTextures.
        if not hasattr(DefaultTextures, 'DEFAULT_AVATAR_TEXTURES_MAP') or \
           not isinstance(DefaultTextures.DEFAULT_AVATAR_TEXTURES_MAP, dict):
            logger.error("DefaultTextures.DEFAULT_AVATAR_TEXTURES_MAP is not defined or not a dict. Cannot create TE.")
            # Fallback to a very basic TE or the last known good one if absolutely necessary
            if self.texture_entry_bytes:
                 current_te_bytes = self.texture_entry_bytes
                 logger.warning("Using last known TE bytes due to missing default map.")
            else: # Absolute fallback: minimal TE with all zeros (likely to make avatar invisible or grey)
                 current_te_bytes = bytes([0] * (self.AVATAR_FACE_COUNT * 17))
                 logger.error("Critical: Default avatar texture map missing and no prior TE. Sending zeroed TE.")
        else:
            texture_entry_bytes = new_te.to_avatar_appearance_bytes(DefaultTextures.DEFAULT_AVATAR_TEXTURES_MAP)
            logger.info(f"Constructed Avatar TextureEntry for AgentSetAppearance, {len(texture_entry_bytes)} bytes.")
            if len(texture_entry_bytes) != self.AVATAR_FACE_COUNT * 17: # 17 bytes per face (16 UUID + 1 MediaFlag)
                logger.warning(f"Generated TE size {len(texture_entry_bytes)} is not expected {self.AVATAR_FACE_COUNT * 17} bytes.")
            current_te_bytes = texture_entry_bytes

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

    def get_wearable_item(self,wt:WearableType)->Tuple[CustomUUID,CustomUUID]|None:return self.wearables.get(wt) # This returns ItemID, AssetID tuple
    def get_visual_param_value(self,idx:int)->float:return self.visual_params[idx] if 0<=idx<len(self.visual_params) else 0.0

    def _get_target_face_indices_for_wearable(self, wear_type: WearableType) -> List[int] | None:
        """
        Maps a WearableType to a list of corresponding avatar face indices for TextureEntry.
        Returns None if the wearable type does not directly map to face textures (e.g., Shape, Physics).
        """
        return self.WEARABLE_TO_FACE_INDICES_MAP.get(wear_type)

    def _apply_default_texture_to_face(self, te_obj: TextureEntry, texture_uuid: CustomUUID, face_index: int):
        """Helper to apply a default texture to a specific face index in a TextureEntry object."""
        if 0 <= face_index < MAX_AVATAR_FACES:
            if te_obj.face_textures[face_index] is None:
                te_obj.face_textures[face_index] = TextureEntryFace()
            # Only apply if not already set by a wearable, or if it's still the very base default.
            # For initial setup, this is fine. Layering logic in set_appearance will override.
            te_obj.face_textures[face_index].texture_id = texture_uuid
        else:
            logger.warning(f"Cannot apply default texture: face index {face_index} is out of range.")

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
