import logging
import asyncio
import uuid # For parsing inventory skeleton if it uses standard UUIDs
from typing import TYPE_CHECKING, Dict, List, Callable, Optional, Any # Added Any

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import AssetType, InventoryType, SaleType, PermissionMask, InventoryItemFlags, FolderType
from pylibremetaverse.types.inventory_defs import InventoryBase, InventoryFolder, InventoryItem
from pylibremetaverse.structured_data import OSDMap, OSDArray
from pylibremetaverse.structured_data.osd import (
    OSDBoolean, OSDUUID as OSDCustomUUID, OSDInteger, OSDString, OSD # Added OSD base
)
# Assuming httpx is available via self.client.network.current_sim.caps.caps_post_llsd() or similar
# import httpx

import datetime

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator

logger = logging.getLogger(__name__)

InventoryUpdateHandler = Callable[[Dict[CustomUUID, InventoryBase]], None]

class InventoryManager:
    """Manages the agent's inventory structure and items."""

    def __init__(self, client: 'GridClient'):
        self.client = client
        self.inventory_root_uuid: CustomUUID | None = None
        self.library_root_uuid: CustomUUID | None = None
        self.trash_folder_uuid: CustomUUID | None = None # New attribute for Trash folder
        self.inventory_skeleton: Dict[CustomUUID, InventoryBase] = {}
        self._inventory_updated_handlers: List[InventoryUpdateHandler] = []
        self._library_updated_handlers: List[InventoryUpdateHandler] = [] # Separate for library if needed
        self._caps_in_progress: Dict[str, asyncio.Future] = {}

    def register_inventory_updated_handler(self, callback: InventoryUpdateHandler):
        if callback not in self._inventory_updated_handlers: self._inventory_updated_handlers.append(callback)
    def unregister_inventory_updated_handler(self, callback: InventoryUpdateHandler):
        if callback in self._inventory_updated_handlers: self._inventory_updated_handlers.remove(callback)

    def register_library_updated_handler(self, callback: InventoryUpdateHandler): # If separate events desired
        if callback not in self._library_updated_handlers: self._library_updated_handlers.append(callback)
    def unregister_library_updated_handler(self, callback: InventoryUpdateHandler):
        if callback in self._library_updated_handlers: self._library_updated_handlers.remove(callback)

    def _fire_inventory_update(self, is_library: bool = False):
        handlers = self._library_updated_handlers if is_library else self._inventory_updated_handlers
        for handler in handlers:
            try: handler(self.inventory_skeleton.copy()) # Send copy to prevent modification
            except Exception as e: logger.error(f"Error in inventory_updated_handler (is_library={is_library}): {e}")

    def _parse_inventory_folder_data(self, folder_data: OSDMap, owner_id: CustomUUID) -> InventoryFolder | None:
        try:
            folder_uuid = folder_data.get('folder_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid()

            # Try to get existing folder to preserve children list if it's just an update to the folder's own properties
            existing_folder = self.inventory_skeleton.get(folder_uuid)
            if isinstance(existing_folder, InventoryFolder):
                folder = existing_folder
                # Update properties from folder_data
                folder.parent_uuid=folder_data.get('parent_id', OSDCustomUUID(folder.parent_uuid)).as_uuid() # Keep old if not present
                folder.name=folder_data.get('name', OSDString(folder.name)).as_string()
                folder.owner_id=owner_id # Owner might change, update it
                folder.version = folder_data.get('version', OSDInteger(folder.version)).as_integer()
                folder.descendent_count = folder_data.get('descendents', OSDInteger(folder.descendent_count)).as_integer()
            else: # New folder
                folder = InventoryFolder(
                    uuid=folder_uuid,
                    parent_uuid=folder_data.get('parent_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid(),
                    name=folder_data.get('name', OSDString("")).as_string(),
                    owner_id=owner_id
                )
                folder.version = folder_data.get('version', OSDInteger(0)).as_integer()
                folder.descendent_count = folder_data.get('descendents', OSDInteger(0)).as_integer()

            try:
                pt_str = folder_data.get('preferred_type', OSDString("unknown")).as_string().upper()
                # Handle cases like "texture" vs "Texture"
                folder.preferred_type = AssetType[pt_str] if hasattr(AssetType, pt_str) else AssetType.Unknown
            except (KeyError, AttributeError, ValueError): folder.preferred_type = AssetType.Unknown

            # Check if this is the trash folder
            if folder.name == "Trash" or folder.preferred_type == AssetType.Trash: # C# FolderType.Trash maps to AssetType.Trash
                 # Check if it's the main inventory's trash, not a sub-folder named Trash by user
                if owner_id == (self.client.self.agent_id if self.client.self else CustomUUID.ZERO): # Basic check
                    if not self.trash_folder_uuid or self.trash_folder_uuid == folder.uuid : # Prioritize if already set, else set
                        self.trash_folder_uuid = folder.uuid
                        logger.info(f"Identified Trash folder: {folder.name} ({folder.uuid})")
            return folder
        except Exception as e: logger.error(f"Error parsing folder data: {e}. Data: {folder_data}"); return None

    def _parse_inventory_item_data(self, item_data: OSDMap, owner_id: CustomUUID) -> InventoryItem | None:
        try:
            item = InventoryItem(
                uuid=item_data.get('item_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid(),
                parent_uuid=item_data.get('parent_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid(),
                name=item_data.get('name', OSDString("")).as_string(),
                owner_id=owner_id
            )
            item.asset_uuid = item_data.get('asset_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid()
            try:
                at_str = item_data.get('asset_type', OSDString("unknown")).as_string().upper()
                it_str = item_data.get('inv_type', OSDString("unknown")).as_string().upper()
                st_val = item_data.get('sale_type', OSDInteger(SaleType.NOT_FOR_SALE.value)).as_integer() # Corrected key
                item.asset_type = AssetType[at_str] if hasattr(AssetType, at_str) else AssetType.Unknown
                item.inv_type = InventoryType[it_str] if hasattr(InventoryType, it_str) else InventoryType.Unknown
                item.sale_type = SaleType(st_val)
            except (KeyError, ValueError, AttributeError) as e: logger.debug(f"Enum conversion error for item {item.name}: {e}")

            item.description = item_data.get('desc', OSDString("")).as_string()
            item.flags = InventoryItemFlags(item_data.get('flags', OSDInteger(0)).as_integer())
            item.creation_date = datetime.datetime.fromtimestamp(item_data.get('created_at', OSDInteger(int(time.time()))).as_integer(), tz=datetime.timezone.utc)
            item.sale_price = item_data.get('sale_price', OSDInteger(0)).as_integer() # Corrected key
            item.group_id = item_data.get('group_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid()
            item.group_owned = item_data.get('group_owned', OSDBoolean(False)).as_boolean()
            item.creator_id = item_data.get('creator_id', OSDCustomUUID(CustomUUID.ZERO)).as_uuid()

            permissions = item_data.get('permissions')
            if isinstance(permissions, OSDMap):
                item.base_mask = PermissionMask(permissions.get('base_mask', OSDInteger(0)).as_integer())
                item.owner_mask = PermissionMask(permissions.get('owner_mask', OSDInteger(0)).as_integer())
                item.group_mask = PermissionMask(permissions.get('group_mask', OSDInteger(0)).as_integer())
                item.everyone_mask = PermissionMask(permissions.get('everyone_mask', OSDInteger(0)).as_integer())
                item.next_owner_mask = PermissionMask(permissions.get('next_owner_mask', OSDInteger(0)).as_integer())
            return item
        except Exception as e: logger.error(f"Error parsing item data: {e}. Data: {item_data}"); return None

    def _process_inventory_descendents(self, descendents_array: OSDArray, owner_id: CustomUUID, parent_folder_uuid: CustomUUID, is_library: bool):
        processed_count = 0
        if not isinstance(descendents_array, OSDArray):
            logger.warning(f"_process_inventory_descendents expected OSDArray for parent {parent_folder_uuid}, got {type(descendents_array)}")
            return

        # Clear existing children for this parent folder if we are about to (re-)populate it.
        parent_obj = self.inventory_skeleton.get(parent_folder_uuid)
        if isinstance(parent_obj, InventoryFolder):
            logger.debug(f"Clearing {len(parent_obj.children)} existing children of folder {parent_folder_uuid} ('{parent_obj.name}') before processing new descendents.")
            parent_obj.children.clear()
        elif parent_folder_uuid != CustomUUID.ZERO : # Don't warn for initial skeleton if parent_folder_uuid is ZERO
             logger.warning(f"Parent folder {parent_folder_uuid} not found or not an InventoryFolder when processing its descendents.")


        for item_llsd in descendents_array:
            if not isinstance(item_llsd, OSDMap): continue
            item_type_str = item_llsd.get('type', OSDString("item")).as_string().lower()
            inv_object = None
            if item_type_str == "category" or item_type_str == "folder":
                inv_object = self._parse_inventory_folder_data(item_llsd, owner_id)
            else:
                inv_object = self._parse_inventory_item_data(item_llsd, owner_id)

            if inv_object:
                # Ensure parent_uuid of the child matches the folder being processed, if not already set (e.g. from skeleton)
                if inv_object.parent_uuid == CustomUUID.ZERO and parent_folder_uuid != CustomUUID.ZERO:
                    inv_object.parent_uuid = parent_folder_uuid

                self.inventory_skeleton[inv_object.uuid] = inv_object
                processed_count += 1

                # Update parent's children list
                if parent_obj and isinstance(parent_obj, InventoryFolder): # Re-check parent_obj after it might have been created by _parse_inventory_folder_data
                    if inv_object.uuid not in parent_obj.children:
                        parent_obj.children.append(inv_object.uuid)

        if parent_obj and isinstance(parent_obj, InventoryFolder):
            logger.debug(f"Folder {parent_folder_uuid} ('{parent_obj.name}') now has {len(parent_obj.children)} children after processing.")

        logger.info(f"Processed {processed_count} inventory descendents for parent {parent_folder_uuid}. Total skeleton size: {len(self.inventory_skeleton)}")
        # Consider moving _fire_inventory_update to after a full recursive fetch, or making it more granular.
        # For now, it fires after each folder's descendents are processed.
        self._fire_inventory_update(is_library)

    async def request_inventory_descendents(self, folder_id: CustomUUID, owner_id: CustomUUID,
                                            fetch_folders: bool, fetch_items: bool,
                                            sort_order: str, # "by_name" or "by_date"
                                            is_library: bool):
        caps_client = self.client.network.current_sim.http_caps_client if self.client.network.current_sim else None
        if not caps_client: logger.warning("Cannot request inventory: No CAPS client."); return

        cap_name = "FetchInventoryDescendents2"; inv_cap_url = caps_client.get_cap_url(cap_name)
        if not inv_cap_url: logger.error(f"'{cap_name}' cap not found."); return

        # Convert sort_order string to int expected by CAP (0 for by_name, 1 for by_date)
        sort_order_int = 0 if sort_order.lower() == "by_name" else 1

        request_body = OSDMap({
            "folders": OSDArray([ OSDMap({
                    "folder_id": OSDCustomUUID(folder_id),
                    "owner_id": OSDCustomUUID(owner_id), # Required by FetchInventoryDescendents2
                    "fetch_folders": OSDBoolean(fetch_folders),
                    "fetch_items": OSDBoolean(fetch_items),
                    "sort_order": OSDInteger(sort_order_int)
            }) ])
        })
        logger.debug(f"Requesting descendents for folder {folder_id}, owner {owner_id} via {inv_cap_url}")
        try:
            response_osd = await caps_client.caps_post_llsd(inv_cap_url, request_body)
            if response_osd and isinstance(response_osd, OSDMap) and \
               response_osd.get("folders") and isinstance(response_osd["folders"], OSDArray):
                for folder_response in response_osd["folders"]: # Should be one per requested folder
                    if isinstance(folder_response, OSDMap):
                        desc_array = folder_response.get("descendents", OSDArray())
                        # Pass folder_id as parent_folder_uuid
                        self._process_inventory_descendents(desc_array, owner_id, folder_id, is_library)
            else: logger.error(f"Failed to parse FetchInventoryDescendents2 response: {response_osd}")
        except Exception as e: logger.exception(f"Error in FetchInventoryDescendents2 request for folder {folder_id}: {e}")

    async def fetch_folder_recursively(self, folder_uuid: CustomUUID, owner_id: CustomUUID,
                                     is_library: bool = False, depth: int = 0, max_depth: int = 10):
        """
        Fetches the contents of a folder and recursively fetches its sub-folders.
        """
        if folder_uuid == CustomUUID.ZERO:
            logger.warning("fetch_folder_recursively called with ZERO UUID, skipping.")
            return
        if depth >= max_depth:
            logger.warning(f"Max recursion depth ({max_depth}) reached for inventory fetch at folder {folder_uuid}.")
            return

        current_folder_obj_initial = self.inventory_skeleton.get(folder_uuid)
        folder_name_for_log = current_folder_obj_initial.name if isinstance(current_folder_obj_initial, InventoryFolder) else "Unknown/Not Yet Parsed"
        logger.debug(f"Fetching contents for folder: {folder_uuid} ('{folder_name_for_log}'), depth: {depth}")

        await self.request_inventory_descendents(
            folder_id=folder_uuid,
            owner_id=owner_id,
            fetch_folders=True,
            fetch_items=True,
            sort_order="by_name",
            is_library=is_library
        )

        # After request_inventory_descendents, the current_folder_obj should have its children list populated by _process_inventory_descendents
        current_folder_obj = self.inventory_skeleton.get(folder_uuid)

        if current_folder_obj and isinstance(current_folder_obj, InventoryFolder):
            child_uuids_to_check = list(current_folder_obj.children) # Iterate over a copy
            logger.debug(f"Folder {folder_uuid} ('{current_folder_obj.name}') has {len(child_uuids_to_check)} children to check for recursion.")

            for child_uuid in child_uuids_to_check:
                child_item = self.inventory_skeleton.get(child_uuid)
                if child_item and isinstance(child_item, InventoryFolder):
                    # Check if this child folder has already been fetched to this depth or deeper to prevent re-fetching cycles in odd scenarios
                    # (Basic depth limiting is the primary guard)
                    await self.fetch_folder_recursively(child_item.uuid, owner_id, is_library, depth + 1, max_depth)
        elif not current_folder_obj:
            logger.warning(f"Folder {folder_uuid} ('{folder_name_for_log}') not found in skeleton after fetching its descendents.")
        # else: current_folder_obj is not an InventoryFolder (e.g. an item), so no children to recurse into.

    async def request_inventory_root(self):
        if self.inventory_root_uuid and self.client.self and self.client.self.agent_id != CustomUUID.ZERO:
            logger.info(f"Starting recursive fetch for inventory root: {self.inventory_root_uuid}")
            await self.fetch_folder_recursively(self.inventory_root_uuid, self.client.self.agent_id, is_library=False)
            logger.info(f"Completed recursive fetch for inventory root: {self.inventory_root_uuid}")
            # Fire one update after the full recursive fetch is initiated.
            # Note: _fire_inventory_update is also called by _process_inventory_descendents for each folder.
            # This behavior might lead to multiple updates. Consider a flag to suppress intermediate updates during recursion.
            self._fire_inventory_update(is_library=False)
        else:
            logger.warning("Inventory root UUID or agent ID not known. Cannot fetch main inventory.")

    async def request_library_root(self):
        library_owner_id = self.client.self.agent_id # Default if no specific library owner ID available
        # A more robust way to get library_owner_id would be from login response or a config.
        # For now, using agent_id as a common case for "My Library" items.
        # if hasattr(self.client, 'library_owner_id') and self.client.library_owner_id:
        #     library_owner_id = self.client.library_owner_id

        if self.library_root_uuid and library_owner_id != CustomUUID.ZERO:
            logger.info(f"Starting recursive fetch for library root: {self.library_root_uuid} with owner {library_owner_id}")
            await self.fetch_folder_recursively(self.library_root_uuid, library_owner_id, is_library=True)
            logger.info(f"Completed recursive fetch for library root: {self.library_root_uuid}")
            self._fire_inventory_update(is_library=True)
        else:
            logger.warning("Library root UUID or Library Owner ID not known/valid. Cannot fetch library.")

    def _parse_initial_skeleton(self, inv_skeleton_data: list, lib_skeleton_data: list, lib_owner_id: CustomUUID):
        logger.debug(f"Parsing initial inventory skeleton. Inventory: {len(inv_skeleton_data)}, Library: {len(lib_skeleton_data)}")

        agent_id = self.client.self.agent_id if self.client.self else CustomUUID.ZERO
        if agent_id == CustomUUID.ZERO:
            logger.error("Agent ID is ZERO during _parse_initial_skeleton. Inventory owner will be incorrect.")

        # For initial skeleton, parent_folder_uuid is effectively ZERO as these are root/top-level folders given by login
        # The `_process_inventory_descendents` will handle parsing them into the skeleton.
        # The children of these roots will be populated by later calls to request_inventory_descendents.
        if inv_skeleton_data:
            self._process_inventory_descendents(OSDArray(inv_skeleton_data), agent_id, CustomUUID.ZERO, False)
        if lib_skeleton_data:
            self._process_inventory_descendents(OSDArray(lib_skeleton_data), lib_owner_id, CustomUUID.ZERO, True)


    def get_item(self,iu:CustomUUID)->InventoryItem|None:item=self.inventory_skeleton.get(iu);return item if isinstance(item,InventoryItem)else None
    def get_folder(self,fu:CustomUUID)->InventoryFolder|None:f=self.inventory_skeleton.get(fu);return f if isinstance(f,InventoryFolder)else None
    def get_folder_contents(self,fu:CustomUUID)->List[InventoryBase]:return[i for i in self.inventory_skeleton.values()if i.parent_uuid==fu]

    async def create_folder(self, parent_uuid: CustomUUID, name: str,
                            folder_type: FolderType = FolderType.NONE,
                            owner_id: CustomUUID | None = None) -> InventoryFolder | None:
        """
        Creates a new inventory folder using CAPS.
        """
        if not self.client.self or not self.client.network.current_sim or not self.client.network.current_sim.http_caps_client:
            logger.error("Cannot create folder: Not connected or CAPS client not available.")
            return None

        actual_owner_id = owner_id or (self.client.self.agent_id if self.client.self else CustomUUID.ZERO)
        if actual_owner_id == CustomUUID.ZERO:
            logger.error("Cannot create folder: owner_id not specified and agent_id is not available.")
            return None

        caps_client = self.client.network.current_sim.http_caps_client
        cap_url = caps_client.get_cap_url("CreateInventoryFolder2") or caps_client.get_cap_url("CreateInventoryFolder")

        if not cap_url:
            logger.error("Cannot create folder: 'CreateInventoryFolder2' or 'CreateInventoryFolder' CAP not available.")
            return None

        payload = OSDMap({
            "folder_name": OSDString(name),
            "parent_id": OSDCustomUUID(parent_uuid),
            "type": OSDInteger(folder_type.value) # The type field expects an integer (sbyte in C# FolderType)
        })

        logger.debug(f"Creating folder '{name}' in parent {parent_uuid} via CAPS: {cap_url}")
        try:
            response_osd = await caps_client.caps_post_llsd(cap_url, payload)

            if response_osd and isinstance(response_osd, OSDMap) and response_osd.get('__type') != 'error':
                # The response itself is usually the folder data for the new folder
                new_folder = self._parse_inventory_folder_data(response_osd, actual_owner_id)
                if new_folder:
                    self.inventory_skeleton[new_folder.uuid] = new_folder

                    # Add to parent's children list
                    parent_folder = self.inventory_skeleton.get(parent_uuid)
                    if isinstance(parent_folder, InventoryFolder):
                        if new_folder.uuid not in parent_folder.children:
                            parent_folder.children.append(new_folder.uuid)

                    logger.info(f"Successfully created folder: {new_folder.name} ({new_folder.uuid})")
                    self._fire_inventory_update(is_library=False) # Assuming user inventory for now
                    return new_folder
                else:
                    logger.error(f"Failed to parse created folder data from response: {response_osd}")
                    return None
            else:
                error_msg = response_osd.get('message', OSDString('Unknown error')).as_string() if isinstance(response_osd, OSDMap) else "Unknown error"
                logger.error(f"Failed to create folder '{name}'. Server response: {error_msg} Full: {response_osd}")
                return None
        except Exception as e:
            logger.exception(f"Exception during create_folder CAPS request: {e}")
            return None

    async def move_inventory_objects(self, objects_to_move: list[dict[str, Any]],
                                     owner_id: CustomUUID | None = None) -> bool:
        """
        Moves one or more inventory items/folders to a new parent folder, optionally renaming them.
        Assumes all objects in the list are of the same type (all items or all folders)
        for determining the CAPS payload key.
        """
        if not self.client.self or not self.client.network.current_sim or not self.client.network.current_sim.http_caps_client:
            logger.error("Cannot move inventory objects: Not connected or CAPS client not available.")
            return False
        if not objects_to_move:
            logger.info("No objects specified to move.")
            return True # No action needed, considered success

        actual_owner_id = owner_id or (self.client.self.agent_id if self.client.self else CustomUUID.ZERO)
        if actual_owner_id == CustomUUID.ZERO:
            logger.error("Cannot move inventory objects: owner_id not specified and agent_id is not available.")
            return False

        caps_client = self.client.network.current_sim.http_caps_client
        # "MoveInventoryFolder" is often used for both items and folders, with different payload structures.
        # C# uses "MoveInventoryNode" which might be an abstraction over "MoveInventoryFolder" or similar.
        # Let's assume "MoveInventoryFolder" is the target CAP.
        cap_url = caps_client.get_cap_url("MoveInventoryFolder")

        if not cap_url:
            logger.error("Cannot move inventory objects: 'MoveInventoryFolder' CAP not available.")
            return False

        osd_array_to_move = OSDArray()
        payload_key = "" # "folders_to_move" or "items_to_move"

        for i, obj_info in enumerate(objects_to_move):
            obj_id = obj_info['id']
            new_parent_id = obj_info['new_parent_id']
            new_name = obj_info.get('new_name') # Optional
            is_folder = obj_info['is_folder']

            if i == 0: # Determine payload key based on the first item
                payload_key = "folders_to_move" if is_folder else "items_to_move"
            elif (is_folder and payload_key == "items_to_move") or \
                 (not is_folder and payload_key == "folders_to_move"):
                logger.error("Cannot move mixed items and folders in a single call with this simplified implementation. Aborting move.")
                # A more robust implementation could split into multiple CAPS calls.
                return False

            obj_osd_map = OSDMap()
            if is_folder:
                obj_osd_map['folder_id'] = OSDCustomUUID(obj_id)
            else: # is_item
                obj_osd_map['item_id'] = OSDCustomUUID(obj_id)

            obj_osd_map['parent_id'] = OSDCustomUUID(new_parent_id) # C# uses 'parent_id' for folders, 'folder_id' for items' new parent.
                                                                 # The "MoveInventoryFolder" CAP might be flexible or expect parent_id.
                                                                 # Let's stick to parent_id for now, assuming CAP handles it.
                                                                 # If item moves fail, this could be 'folder_id'.

            if new_name:
                obj_osd_map['name'] = OSDString(new_name)

            osd_array_to_move.append(obj_osd_map)

        if not payload_key: # Should not happen if objects_to_move is not empty
            logger.error("Could not determine payload key for move operation.")
            return False

        payload = OSDMap({payload_key: osd_array_to_move})

        logger.debug(f"Moving inventory objects via CAPS: {cap_url} with payload {payload}")
        try:
            response_osd = await caps_client.caps_post_llsd(cap_url, payload)

            # Successful response for MoveInventoryFolder is often just an empty OSDMap or {'success': true}
            # Or it might return the new details of the moved items/folders.
            # For now, assume success if no error type in response.
            if response_osd is not None and (not isinstance(response_osd, OSDMap) or response_osd.get('__type') != 'error'):
                logger.info(f"Move operation reported success by server. Updating local skeleton for {len(objects_to_move)} objects.")
                for obj_info in objects_to_move:
                    obj_id = obj_info['id']
                    new_parent_id = obj_info['new_parent_id']
                    new_name = obj_info.get('new_name')

                    item_or_folder = self.inventory_skeleton.get(obj_id)
                    if not item_or_folder:
                        logger.warning(f"Moved object {obj_id} not found in local skeleton. Cannot update old parent.")
                        continue

                    old_parent_uuid = item_or_folder.parent_uuid

                    # Remove from old parent's children list
                    if old_parent_uuid and old_parent_uuid != CustomUUID.ZERO:
                        old_parent_folder = self.inventory_skeleton.get(old_parent_uuid)
                        if isinstance(old_parent_folder, InventoryFolder) and obj_id in old_parent_folder.children:
                            old_parent_folder.children.remove(obj_id)

                    # Update item/folder properties
                    item_or_folder.parent_uuid = new_parent_id
                    if new_name:
                        item_or_folder.name = new_name

                    # Add to new parent's children list
                    new_parent_folder = self.inventory_skeleton.get(new_parent_id)
                    if isinstance(new_parent_folder, InventoryFolder):
                        if obj_id not in new_parent_folder.children:
                            new_parent_folder.children.append(obj_id)

                self._fire_inventory_update(is_library=False) # Assuming user inventory for now
                return True
            else:
                error_msg = response_osd.get('message', OSDString('Unknown error')).as_string() if isinstance(response_osd, OSDMap) else "Unknown error or empty response"
                logger.error(f"Failed to move inventory objects. Server response: {error_msg}. Full: {response_osd}")
                return False
        except Exception as e:
            logger.exception(f"Exception during move_inventory_objects CAPS request: {e}")
            return False

    async def move_item(self, item_uuid: CustomUUID, new_parent_uuid: CustomUUID,
                        new_name: str | None = None, owner_id: CustomUUID | None = None) -> bool:
        """Moves an inventory item to a new parent folder, optionally renaming it."""
        return await self.move_inventory_objects(
            objects_to_move=[{'id': item_uuid, 'new_parent_id': new_parent_uuid, 'new_name': new_name, 'is_folder': False}],
            owner_id=owner_id
        )

    async def purge_inventory_objects(self, objects_to_purge: list[dict[str, Any]],
                                      owner_id: CustomUUID | None = None) -> bool:
        """
        Permanently purges one or more inventory items/folders (typically from trash).
        """
        if not self.client.self or not self.client.network.current_sim or not self.client.network.current_sim.http_caps_client:
            logger.error("Cannot purge inventory objects: Not connected or CAPS client not available.")
            return False
        if not objects_to_purge:
            logger.info("No objects specified to purge.")
            return True

        actual_owner_id = owner_id or (self.client.self.agent_id if self.client.self else CustomUUID.ZERO)
        if actual_owner_id == CustomUUID.ZERO: # Should not happen if client.self is available
            logger.error("Cannot purge inventory objects: owner_id not determined.")
            return False

        caps_client = self.client.network.current_sim.http_caps_client
        # Common CAP for this is "PurgeInventoryDescendents", but some grids might use "RemoveInventoryFolder" / "RemoveInventoryItem"
        # "PurgeInventoryDescendents" typically takes arrays of item_ids and folder_ids.
        cap_url = caps_client.get_cap_url("PurgeInventoryDescendents")
        if not cap_url:
            # Fallback: Check for individual removal CAPS if PurgeInventoryDescendents is not found.
            # This would require sending individual requests, which is less efficient.
            # For this implementation, we'll assume PurgeInventoryDescendents is the primary target.
            logger.error("Cannot purge inventory objects: 'PurgeInventoryDescendents' CAP not available.")
            return False

        item_ids_to_purge = OSDArray()
        folder_ids_to_purge = OSDArray()

        for obj_info in objects_to_purge:
            obj_id = obj_info['id']
            is_folder = obj_info['is_folder']
            if is_folder:
                folder_ids_to_purge.append(OSDCustomUUID(obj_id))
            else:
                item_ids_to_purge.append(OSDCustomUUID(obj_id))

        payload_parts = {}
        if folder_ids_to_purge: # Add only if there are folders to purge
            payload_parts["folder_ids"] = folder_ids_to_purge
        if item_ids_to_purge: # Add only if there are items to purge
            payload_parts["item_ids"] = item_ids_to_purge

        if not payload_parts: # Nothing to purge
            logger.info("No valid items or folders specified for purging after filtering.")
            return True

        payload = OSDMap(payload_parts)

        logger.debug(f"Purging inventory objects via CAPS: {cap_url} with payload {payload}")
        try:
            response_osd = await caps_client.caps_post_llsd(cap_url, payload)

            # Successful response is often an empty OSDMap or {'success': true}
            if response_osd is not None and (not isinstance(response_osd, OSDMap) or response_osd.get('__type') != 'error'):
                logger.info(f"Purge operation reported success by server for {len(objects_to_purge)} specified objects.")

                for obj_info in objects_to_purge:
                    obj_id = obj_info['id']
                    item_or_folder = self.inventory_skeleton.get(obj_id)
                    if item_or_folder:
                        # Remove from old parent's (trash folder's) children list
                        old_parent_uuid = item_or_folder.parent_uuid
                        if old_parent_uuid and old_parent_uuid != CustomUUID.ZERO:
                            old_parent_folder = self.inventory_skeleton.get(old_parent_uuid)
                            if isinstance(old_parent_folder, InventoryFolder) and obj_id in old_parent_folder.children:
                                old_parent_folder.children.remove(obj_id)

                        # Remove from skeleton itself
                        del self.inventory_skeleton[obj_id]
                        logger.debug(f"Removed {obj_id} from local inventory skeleton after purge.")
                    else:
                        logger.warning(f"Purged object {obj_id} not found in local skeleton for removal.")

                self._fire_inventory_update(is_library=False) # Assuming user inventory
                return True
            else:
                error_msg = response_osd.get('message', OSDString('Unknown error')).as_string() if isinstance(response_osd, OSDMap) else "Unknown error or empty response"
                logger.error(f"Failed to purge inventory objects. Server response: {error_msg}. Full: {response_osd}")
                return False
        except Exception as e:
            logger.exception(f"Exception during purge_inventory_objects CAPS request: {e}")
            return False

    async def purge_item_from_trash(self, item_uuid: CustomUUID, owner_id: CustomUUID | None = None) -> bool:
        """Permanently purges a single inventory item (expected to be in trash)."""
        return await self.purge_inventory_objects(
            objects_to_purge=[{'id': item_uuid, 'is_folder': False}],
            owner_id=owner_id
        )

    async def purge_folder_from_trash(self, folder_uuid: CustomUUID, owner_id: CustomUUID | None = None) -> bool:
        """Permanently purges a single inventory folder (and its contents, expected to be in trash)."""
        if folder_uuid == self.trash_folder_uuid:
            logger.error("Cannot purge the main Trash folder itself via this method.")
            return False
        return await self.purge_inventory_objects(
            objects_to_purge=[{'id': folder_uuid, 'is_folder': True}],
            owner_id=owner_id
        )

    async def delete_item_to_trash(self, item_uuid: CustomUUID, owner_id: CustomUUID | None = None) -> bool:
        """Moves a single inventory item to the trash folder."""
        if not self.trash_folder_uuid:
            logger.error("Trash folder UUID not known. Cannot move item to trash.")
            return False
        return await self.move_item(item_uuid, self.trash_folder_uuid, owner_id=owner_id)

    async def delete_folder_to_trash(self, folder_uuid: CustomUUID, owner_id: CustomUUID | None = None) -> bool:
        """Moves a single inventory folder (and its contents) to the trash folder."""
        if not self.trash_folder_uuid:
            logger.error("Trash folder UUID not known. Cannot move folder to trash.")
            return False
        if folder_uuid == self.trash_folder_uuid:
            logger.error("Cannot move the Trash folder itself into the Trash folder.")
            return False
        # Note: The `move_folder` (and underlying `move_inventory_objects`) CAP implies
        # the server handles moving contents of the folder.
        return await self.move_folder(folder_uuid, self.trash_folder_uuid, owner_id=owner_id)

    async def copy_inventory_item(self, item_to_copy_uuid: CustomUUID,
                                  new_parent_uuid: CustomUUID,
                                  new_name: str,
                                  owner_id: CustomUUID | None = None) -> InventoryItem | None:
        """Copies an inventory item to a new folder with a new name using CAPS."""
        if not self.client.self or not self.client.network.current_sim or not self.client.network.current_sim.http_caps_client:
            logger.error("Cannot copy item: Not connected or CAPS client not available.")
            return None

        actual_owner_id = owner_id or (self.client.self.agent_id if self.client.self else CustomUUID.ZERO)
        if actual_owner_id == CustomUUID.ZERO:
            logger.error("Cannot copy item: owner_id not specified and agent_id is not available.")
            return None

        item_to_copy = self.get_item(item_to_copy_uuid)
        if not item_to_copy:
            logger.error(f"Cannot copy item: Original item {item_to_copy_uuid} not found in local skeleton.")
            return None

        caps_client = self.client.network.current_sim.http_caps_client
        cap_url = caps_client.get_cap_url("CopyInventoryItem")

        if not cap_url:
            logger.error("Cannot copy item: 'CopyInventoryItem' CAP not available.")
            return None

        # Construct payload based on common patterns (item_id of original, folder_id for new parent, new_name)
        # C# CopyInventoryItem takes: agentID, sessionID, itemID, newFolderID, newName
        # The payload for the CAPS request is typically an OSDMap.
        payload = OSDMap({
            "item_id": OSDCustomUUID(item_to_copy_uuid),
            "folder_id": OSDCustomUUID(new_parent_uuid), # This is the new parent folder
            "new_name": OSDString(new_name)
            # "owner_id": OSDCustomUUID(actual_owner_id) # Usually not needed, server uses agent's session
        })

        logger.debug(f"Copying item {item_to_copy_uuid} to parent {new_parent_uuid} as '{new_name}' via CAPS: {cap_url}")
        try:
            response_osd = await caps_client.caps_post_llsd(cap_url, payload)

            # Successful response is an OSDArray containing an OSDMap of the new item's data
            if isinstance(response_osd, OSDArray) and len(response_osd) > 0 and isinstance(response_osd[0], OSDMap):
                new_item_data = response_osd[0]
                new_item = self._parse_inventory_item_data(new_item_data, actual_owner_id)

                if new_item:
                    self.inventory_skeleton[new_item.uuid] = new_item

                    parent_folder = self.inventory_skeleton.get(new_parent_uuid)
                    if isinstance(parent_folder, InventoryFolder):
                        if new_item.uuid not in parent_folder.children:
                            parent_folder.children.append(new_item.uuid)

                    logger.info(f"Successfully copied item: {new_item.name} ({new_item.uuid}) into folder {new_parent_uuid}")
                    self._fire_inventory_update(is_library=False) # Assuming user inventory
                    return new_item
                else:
                    logger.error(f"Failed to parse copied item data from response: {new_item_data}")
                    return None
            else:
                error_msg = "Unknown error or malformed response"
                if isinstance(response_osd, OSDMap) and response_osd.get('__type') == 'error':
                    error_msg = response_osd.get('message', OSDString(error_msg)).as_string()
                logger.error(f"Failed to copy item '{item_to_copy_uuid}'. Server response: {error_msg}. Full: {response_osd}")
                return None
        except Exception as e:
            logger.exception(f"Exception during copy_inventory_item CAPS request: {e}")
            return None

    async def move_folder(self, folder_uuid: CustomUUID, new_parent_uuid: CustomUUID,
                          new_name: str | None = None, owner_id: CustomUUID | None = None) -> bool:
        """Moves an inventory folder to a new parent folder, optionally renaming it."""
        return await self.move_inventory_objects(
            objects_to_move=[{'id': folder_uuid, 'new_parent_id': new_parent_uuid, 'new_name': new_name, 'is_folder': True}],
            owner_id=owner_id
        )
