import asyncio
import logging
import os
import sys
import datetime
from typing import Dict, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from pylibremetaverse.client import GridClient
from pylibremetaverse.network.login_defs import LoginStatus
from pylibremetaverse.managers.agent_manager import (
    AgentManager, ChatEventArgs, IMEventArgs, TeleportEventArgs,
    AvatarSitResponseEventArgs, TeleportLureEventArgs,
    ScriptDialogEventArgs, ScriptQuestionEventArgs, MuteEntry
)
from pylibremetaverse.network.simulator import Simulator
from pylibremetaverse.types import CustomUUID, Primitive, Vector3, Quaternion
from pylibremetaverse.types.enums import (
    TeleportStatus, TeleportFlags, InstantMessageDialog, ScriptPermission,
    MuteType, MuteFlags, WearableType, ClickAction, # Added ClickAction
    PCode, Material, AddFlags, PathCurve, ProfileCurve, FolderType, ImageType,
    AssetType, InventoryType, SaleType, PermissionMask # Added for notecard creation
)
from pylibremetaverse.types.animations import Animations
from pylibremetaverse.types.color import Color4 # For TE generation
from pylibremetaverse.types.inventory_defs import InventoryBase, InventoryFolder, InventoryItem # For type checking in print_folder_recursive
import struct # For TE generation
# from pylibremetaverse.types.enums import AssetType # Already imported above
# Import Asset base and subclasses for type checking in on_asset_received
from pylibremetaverse.assets import Asset, AssetNotecard, AssetLandmark, AssetScript # Added AssetScript
# Import FriendsManager related types for handlers (though args are passed directly)
from pylibremetaverse.managers.friends_manager import FriendsManager
# Import event args dataclasses from FriendsManager for type hinting
from pylibremetaverse.managers.friends_manager import (
    FriendOnlineStatusEventArgs, FriendRightsEventArgs, FriendRemovedEventArgs
)


test_client_instance: GridClient | None = None

def login_progress_callback(status: LoginStatus, message: str, error_key: str): logging.info(f"[Login] Status:{status.name}, Msg:'{message}'")
def sim_connected_callback(s: Simulator): logging.info(f"[Sim] Connected: {s.name}")
def sim_disconnected_callback(s: Simulator, requested_logout: bool): logging.info(f"[Sim] Disconnected: {s.name if s else 'N/A'}. Logout:{requested_logout}")
def network_disconnected_callback(reason: str): logging.info(f"[Net] Disconnected. Reason: {reason}")
def on_chat_received(c: ChatEventArgs): logging.info(f"[Chat] From:{c.from_name} Type:{c.chat_type.name} Msg:'{c.message}'")
def on_im_received(im: IMEventArgs): logging.info(f"[IM] From:{im.im_data.from_agent_name} Dialog:{im.im_data.dialog.name} Msg:'{im.im_data.message}'")
def on_teleport_progress(tp: TeleportEventArgs): logging.info(f"[Teleport] Status:{tp.status.name} Msg:'{tp.message}'")
def on_avatar_sit_response(sr: AvatarSitResponseEventArgs): logging.info(f"[SitResponse] ObjID:{sr.object_id} Pos:{sr.sit_position}")
def on_teleport_lure_offered(lure: TeleportLureEventArgs):
    logging.info(f"[TeleportLure] From:{lure.from_agent_name} Msg:'{lure.message}' LureID:{lure.lure_id}")
    if test_client_instance: asyncio.create_task(test_client_instance.self.respond_to_teleport_lure(lure.from_agent_id,lure.lure_id,True))
def on_script_dialog(args: ScriptDialogEventArgs):
    logging.info(f"[ScriptDialog] Obj:{args.object_name}, Msg:'{args.message[:30]}...', Buttons:{args.button_labels}")
    if test_client_instance and args.button_labels: asyncio.create_task(test_client_instance.self.respond_to_script_dialog(args.object_id,args.chat_channel,0,args.button_labels[0],args.simulator))
def on_script_question(args: ScriptQuestionEventArgs):
    logging.info(f"[ScriptQuestion] Obj:{args.object_name}, Perms:{args.questions!r}")
    if test_client_instance: asyncio.create_task(test_client_instance.self.respond_to_script_permission_request(args.task_id,args.item_id,args.questions,args.simulator))
def on_mute_list_updated(mutes: Dict[str,MuteEntry]): logging.info(f"[MuteListUpdated] Count: {len(mutes)}")
def on_wearables_updated(wearables: Dict[WearableType, Tuple[CustomUUID, CustomUUID]]):
    logging.info(f"[WearablesUpdated] Agent wearing {len(wearables)} items: {wearables}")
    if test_client_instance:
        # After wearables are updated (e.g. on login or after wearing/taking off),
        # call set_appearance to update the avatar with the new logic.
        logging.info("Wearables updated, triggering set_appearance to reflect changes.")
        asyncio.create_task(test_client_instance.appearance.set_appearance())

        # --- Test Texture Request (existing logic, can remain) ---
        texture_to_request_item_id: CustomUUID | None = None
        texture_to_request_asset_id: CustomUUID | None = None
        wearable_type_for_texture: WearableType | None = None

        for wear_type, (item_id, asset_id) in wearables.items():
            if asset_id != CustomUUID.ZERO: # Found a wearable with an asset
                texture_to_request_item_id = item_id
                texture_to_request_asset_id = asset_id
                wearable_type_for_texture = wear_type
                break # Request the first one found

        if texture_to_request_asset_id and texture_to_request_item_id and wearable_type_for_texture:
            logging.info(f"Requesting texture asset {texture_to_request_asset_id} for wearable {wearable_type_for_texture.name} (item {texture_to_request_item_id})")
            asyncio.create_task(test_client_instance.assets.request_texture(
                texture_uuid=texture_to_request_asset_id,
                image_type=ImageType.NORMAL, # Or ImageType.BAKED if appropriate
                item_id_for_callback=texture_to_request_item_id, # Use item_id for callback context
                callback_on_complete=on_texture_received
            ))
        else:
            logging.info("No wearable items with textures found to test texture request.")


def on_asset_received(success: bool, asset_obj_or_data: Any, asset_type_enum: AssetType,
                        asset_uuid: CustomUUID, vfile_id_for_callback: CustomUUID | None,
                        error_message: str | None = None):
    """Callback for when an asset is received (or fails)."""
    if success:
        if isinstance(asset_obj_or_data, AssetWearable) and asset_obj_or_data.loaded_successfully:
            logging.info(f"Wearable asset {asset_uuid} (VFile: {vfile_id_for_callback}) received and parsed. Name: '{asset_obj_or_data.name}', Type: {asset_obj_or_data.wearable_type.name}")
            logging.info(f"  Textures: {asset_obj_or_data.textures}")
            logging.info(f"  Parameters: {asset_obj_or_data.parameters}")
        elif isinstance(asset_obj_or_data, AssetNotecard) and asset_obj_or_data.loaded_successfully:
            logging.info(f"Notecard asset {asset_uuid} (VFile: {vfile_id_for_callback}) received and parsed. Name: '{asset_obj_or_data.name}', Body preview: '{asset_obj_or_data.body_text[:100].replace(chr(10), ' ')}...'")
        elif isinstance(asset_obj_or_data, AssetLandmark) and asset_obj_or_data.loaded_successfully:
            logging.info(f"Landmark asset {asset_uuid} (VFile: {vfile_id_for_callback}) received and parsed. Name: '{asset_obj_or_data.name}', Region: {asset_obj_or_data.region_handle}, Pos: {asset_obj_or_data.position}")
        elif isinstance(asset_obj_or_data, Asset) and asset_obj_or_data.loaded_successfully: # Base Asset or other non-specialized parsed type
            logging.info(f"Asset {asset_uuid} (VFile: {vfile_id_for_callback}) of type {asset_type_enum.name} received. Data length: {len(asset_obj_or_data.raw_data)}. Parsed as: {type(asset_obj_or_data).__name__}")
        elif isinstance(asset_obj_or_data, bytes): # Raw bytes for unparsed or simple types (like textures for now)
            logging.info(f"Asset {asset_uuid} (VFile: {vfile_id_for_callback}) of type {asset_type_enum.name} received as raw data. Length: {len(asset_obj_or_data)} bytes.")
            if asset_type_enum == AssetType.Texture:
                 # Here you could save the texture data, try to decode if J2K, etc.
                 pass
        else: # Should not happen if success is true and data is None
            logging.warning(f"Asset {asset_uuid} (VFile: {vfile_id_for_callback}) received successfully but data is None or unexpected type: {type(asset_obj_or_data)}")
    else:
        logging.error(f"Failed to receive asset {asset_uuid} (VFile: {vfile_id_for_callback}), Type: {asset_type_enum.name}. Error: {error_message}")


def on_object_updated(prim: Primitive, simulator: Simulator):
    logging.info(f"[ObjectUpdate] Sim:{simulator.name}, PrimLID:{prim.local_id}, Name:'{prim.name}', Pos:{prim.position}, Owner:{prim.owner_id if prim.owner_id != CustomUUID.ZERO else ''}")
    if test_client_instance and (prim.owner_id == CustomUUID.ZERO or prim.name == "Object"):
        if not hasattr(prim, '_properties_requested') or not prim._properties_requested:
            logging.info(f"Requesting props for prim {prim.local_id} (FullID: {prim.id_uuid}) in {simulator.name}")
            # asyncio.create_task(test_client_instance.objects.request_object_properties(simulator, prim.id_uuid)) # Disabled for now
            prim._properties_requested = True

    # One-time manipulation test for a specific object
    # Ensure your test avatar has permissions to modify this object in the sim.
    # You might need to rez a prim and name it "TestPrimForManipulation" or similar.
    if prim.name == "TestPrimForManipulation" and not hasattr(prim, '_manipulated_once'):
        prim._manipulated_once = True # Mark that we've started manipulation for this instance
        logging.info(f"--- Attempting one-time manipulation for prim {prim.local_id} ({prim.name}) ---")

        async def manipulate_object():
            await asyncio.sleep(1) # Small delay before starting manipulation sequence

            # 1. Move
            original_pos = prim.position
            new_pos = Vector3(original_pos.x + 0.5, original_pos.y, original_pos.z)
            logging.info(f"Moving prim {prim.local_id} from {original_pos} to {new_pos}")
            await test_client_instance.objects.move_object(simulator, prim.local_id, new_pos)
            await asyncio.sleep(2) # Wait for move to (hopefully) apply

            # 2. Scale (assuming original scale is known or fetched, e.g., Vector3(0.5, 0.5, 0.5))
            # For testing, let's just try to set a new scale.
            # Be cautious with scale values; very small or large can be problematic.
            original_scale = prim.scale # This might be Vector3.ZERO if not fully updated yet
            if original_scale.magnitude_squared() < 1e-6: original_scale = Vector3(0.5, 0.5, 0.5) # Guess default
            new_scale = Vector3(original_scale.x * 1.2, original_scale.y * 1.2, original_scale.z * 1.2)
            logging.info(f"Scaling prim {prim.local_id} from {original_scale} to {new_scale}")
            await test_client_instance.objects.scale_object(simulator, prim.local_id, new_scale)
            await asyncio.sleep(2)

            # 3. Rotate
            original_rot = prim.rotation # Might be Quaternion.IDENTITY
            # Apply a small additional rotation (e.g., 45 degrees around Z axis)
            additional_rotation = Quaternion.from_axis_angle(Vector3(0, 0, 1), angle_rad=0.7854) # 45 degrees
            new_rot = original_rot * additional_rotation
            new_rot.normalize() # Important for quaternions
            logging.info(f"Rotating prim {prim.local_id} from {original_rot} to {new_rot}")
            await test_client_instance.objects.rotate_object(simulator, prim.local_id, new_rot)
            logging.info(f"--- Geometric manipulations for prim {prim.local_id} sent. ---")

            # Test setting text properties and click action
            if not hasattr(prim, '_text_set_once'):
                prim._text_set_once = True # Ensure this block runs only once per object instance
                await asyncio.sleep(1) # Pause before next set of changes

                new_name = "PyTestCube"
                new_desc = "Programmatically set description."
                new_text = "Hovering with PyLibreMV!"
                new_action = ClickAction.SIT

                logging.info(f"Setting name for {prim.local_id} to '{new_name}'")
                await test_client_instance.objects.set_object_name(simulator, prim.local_id, new_name)
                await asyncio.sleep(1)

                logging.info(f"Setting description for {prim.local_id} to '{new_desc}'")
                await test_client_instance.objects.set_object_description(simulator, prim.local_id, new_desc)
                await asyncio.sleep(1)

                logging.info(f"Setting text for {prim.local_id} to '{new_text}'")
                await test_client_instance.objects.set_object_text(simulator, prim.local_id, new_text)
                await asyncio.sleep(1)

                logging.info(f"Setting click action for {prim.local_id} to {new_action.name}")
                await test_client_instance.objects.set_object_click_action(simulator, prim.local_id, new_action)
                logging.info(f"--- Text/Action manipulations for prim {prim.local_id} sent. ---")


        asyncio.create_task(manipulate_object())

def on_object_removed(local_id: int, simulator: Simulator):
    logging.info(f"[ObjectRemoved] Sim: {simulator.name}, Prim LocalID: {local_id}")

def on_inventory_updated(inventory_items: Dict[CustomUUID, InventoryBase]):
    """Called when the inventory skeleton is updated."""
    logging.info(f"[InventoryUpdated] Inventory skeleton potentially updated. Current total: {len(inventory_items)} items/folders.")

    if test_client_instance:
        inventory_mgr = test_client_instance.inventory

        # --- Test Create Folder ---
        # Run this test only once, e.g., by checking a flag on the client or a specific condition
        if inventory_mgr.inventory_root_uuid and not hasattr(test_client_instance, '_folder_created_test_done'):
            test_client_instance._folder_created_test_done = True # Set flag to run once

            async def inventory_manipulation_tests():
                # --- Create Folder Test ---
                await asyncio.sleep(5) # Wait a bit after initial inventory load for inventory to (hopefully) be somewhat stable
                logging.info("--- Attempting to create a new folder in inventory root... ---")
                new_folder_name = f"PyLibreMV Test Folder {datetime.datetime.now().strftime('%H%M%S')}"
                try:
                    created_folder = await inventory_mgr.create_folder(
                        inventory_mgr.inventory_root_uuid,
                        new_folder_name,
                        FolderType.NONE
                    )
                    if created_folder:
                        logging.info(f"Successfully created folder: {created_folder.name} ({created_folder.uuid}) in parent {created_folder.parent_uuid}")

                        # Now, try to create a sub-folder and then move it
                        await asyncio.sleep(1) # Give server a moment
                        sub_folder_name = f"My Test SubFolder {datetime.datetime.now().strftime('%H%M%S')}"
                        logging.info(f"Attempting to create sub-folder '{sub_folder_name}' in '{created_folder.name}'...")
                        created_sub_folder = await inventory_mgr.create_folder(
                            created_folder.uuid,
                            sub_folder_name,
                            FolderType.TEXTURE # Example type
                        )

                        if created_sub_folder:
                            logging.info(f"Successfully created sub-folder: {created_sub_folder.name} ({created_sub_folder.uuid}) in {created_sub_folder.parent_uuid}")
                            await asyncio.sleep(1)

                            # Attempt to move the sub-folder to the inventory root
                            if inventory_mgr.inventory_root_uuid:
                                logging.info(f"Attempting to move sub-folder '{created_sub_folder.name}' to inventory root ({inventory_mgr.inventory_root_uuid})...")
                                move_success = await inventory_mgr.move_folder(
                                    created_sub_folder.uuid,
                                    inventory_mgr.inventory_root_uuid,
                                    # new_name=f"{created_sub_folder.name} (Moved)" # Optional rename
                                )
                                if move_success:
                                    logging.info(f"Successfully moved folder '{created_sub_folder.name}'. New parent: {inventory_mgr.inventory_root_uuid}.")
                                    # To see changes reflected in print_folder_recursive_local, a new fetch would be needed,
                                    # or ensure on_inventory_updated is re-triggered by move_folder's _fire_inventory_update.

                                    # Test Copy Item: Find first available item in root to copy into the moved sub-folder (which is now in root)
                                    item_to_copy = None
                                    if inventory_mgr.inventory_root_uuid:
                                        for item_uuid_in_root, item_obj_in_root in inventory_mgr.inventory_skeleton.items():
                                            if isinstance(item_obj_in_root, InventoryItem) and item_obj_in_root.parent_uuid == inventory_mgr.inventory_root_uuid:
                                                item_to_copy = item_obj_in_root
                                                break

                                    if item_to_copy and created_sub_folder: # Copy into the sub-folder (which is now in root)
                                        logging.info(f"Attempting to copy item '{item_to_copy.name}' into '{created_sub_folder.name}' (now in root)...")
                                        copied_item = await inventory_mgr.copy_inventory_item(
                                            item_to_copy.uuid, created_sub_folder.uuid, f"Copy of {item_to_copy.name}"
                                        )
                                        if copied_item:
                                            logging.info(f"Copied item successfully: {copied_item.name} ({copied_item.uuid}) in folder {copied_item.parent_uuid}")
                                        else:
                                            logging.error(f"Failed to copy item '{item_to_copy.name}'.")
                                    else:
                                        logging.warning("Could not find a suitable item to copy or target folder for copy test.")

                                else: # move_success for sub_folder
                                    logging.error(f"Failed to move folder '{created_sub_folder.name}'.")
                            else: # inventory_root_uuid check for move
                                logging.warning("Cannot test move_folder as inventory_root_uuid is not available.")
                        else: # created_sub_folder
                            logging.error(f"Failed to create sub-folder '{sub_folder_name}'.")

                        # Test moving the original created_folder (parent of sub-folder initially) to trash
                        if created_folder: # The first folder we made in root ("PyLibreMV Test Folder ...")
                            await asyncio.sleep(1)
                            logging.info(f"Attempting to move folder '{created_folder.name}' to trash...")
                            moved_to_trash = await inventory_mgr.delete_folder_to_trash(created_folder.uuid)
                            if moved_to_trash:
                                logging.info(f"Moved '{created_folder.name}' to trash.")
                                await asyncio.sleep(1)
                                # Test purging it from trash
                                logging.info(f"Attempting to purge '{created_folder.name}' ({created_folder.uuid}) from trash...")
                                purged = await inventory_mgr.purge_folder_from_trash(created_folder.uuid)
                                if purged:
                                    logging.info(f"Purged '{created_folder.name}' successfully.")
                                else:
                                    logging.error(f"Failed to purge '{created_folder.name}'.")
                            else:
                                logging.error(f"Failed to move '{created_folder.name}' to trash.")

                    else: # created_folder (initial top-level test folder)
                        logging.error(f"Failed to create folder '{new_folder_name}'.")
                except Exception as e:
                    logging.exception(f"Exception during create_folder: {e}")

                # --- Create Notecard Test (Chained after folder tests) ---
                if test_client_instance and test_client_instance.inventory.inventory_root_uuid:
                    await asyncio.sleep(2) # Pause before notecard test
                    logging.info("--- Attempting to create a new notecard... ---")
                    notecard_text = f"Hello from PyLibreMetaverse!\nThis is a test notecard created at {datetime.datetime.now()}."
                    notecard_bytes = notecard_text.encode('utf-8')

                    upload_success_event = asyncio.Event()
                    new_asset_uuid_store = {}

                    def asset_upload_cb(success_upload, asset_uuid_from_cb, asset_type_enum_from_cb):
                        nonlocal new_asset_uuid_store # To modify the outer scope dict
                        if success_upload:
                            logging.info(f"Asset uploaded successfully via callback: {asset_uuid_from_cb} (type {asset_type_enum_from_cb})")
                            new_asset_uuid_store['uuid'] = asset_uuid_from_cb
                        else:
                            logging.error("Asset upload failed via callback.")
                        upload_success_event.set()

                    # Use the transaction_id returned by upload_asset to manage the callback context more explicitly if needed,
                    # but AssetManager's _last_upload_transaction_id_for_callback should handle it for single uploads.
                    # For this test, we directly await the event that the callback sets.
                    logging.info("Calling client.assets.upload_asset for notecard...")
                    transaction_id = await test_client_instance.assets.upload_asset(
                        notecard_bytes, AssetType.Notecard, callback=asset_upload_cb
                    )

                    if transaction_id != CustomUUID.ZERO:
                        logging.info(f"AssetUploadRequest sent with TransactionID: {transaction_id}. Waiting for callback...")
                        try:
                            await asyncio.wait_for(upload_success_event.wait(), timeout=30.0) # Wait for upload to complete
                        except asyncio.TimeoutError:
                            logging.error("Timeout waiting for asset upload callback.")

                        new_asset_uuid = new_asset_uuid_store.get('uuid')
                        if new_asset_uuid:
                            logging.info(f"Creating inventory item for notecard asset {new_asset_uuid}")
                            default_permissions = {
                                'base': PermissionMask.ALL, 'owner': PermissionMask.ALL,
                                'group': PermissionMask.ALL, 'everyone': PermissionMask.NONE,
                                'next_owner': PermissionMask.ALL & ~PermissionMask.COPY & ~PermissionMask.TRANSFER
                            }
                            created_item = await inventory_mgr.create_inventory_item(
                                inventory_mgr.inventory_root_uuid, # Create in root for test
                                f"My PyLibreMV Notecard {datetime.datetime.now().strftime('%H%M%S')}",
                                "Test notecard created by PyLibreMV.",
                                AssetType.Notecard, InventoryType.Notecard, new_asset_uuid,
                                permissions=default_permissions
                            )
                            if created_item:
                                logging.info(f"Notecard inventory item CREATED AND CONFIRMED: {created_item.name} (Server ItemID: {created_item.uuid}, CRC: {created_item.crc32}, AssetID: {created_item.asset_uuid})")
                            else:
                                logging.error("Failed to create notecard inventory item (create_inventory_item returned None or failed).")
                        else:
                            logging.error("Asset UUID not received after upload callback, cannot create inventory item.")
                    else:
                        logging.error("Failed to send AssetUploadRequest (transaction_id was ZERO).")

                # --- Create Script Test ---
                await asyncio.sleep(2) # Pause before script test
                await create_test_script(inventory_mgr)


            asyncio.create_task(inventory_manipulation_tests())

        # --- Recursive print example ---
        # Local helper function to avoid passing client instance around or making it global in this scope
        # Uses type names directly for isinstance checks
        def print_folder_recursive_local(folder_uuid: CustomUUID, indent: str = ""):
            folder = inventory_mgr.inventory_skeleton.get(folder_uuid)
            if folder and isinstance(folder, InventoryFolder):
                logging.info(f"{indent}[Folder] {folder.name} ({folder.uuid}) - Children in skeleton: {len(folder.children)}")

                for child_uuid in folder.children:
                    child_item = inventory_mgr.inventory_skeleton.get(child_uuid)
                    if child_item and isinstance(child_item, InventoryFolder):
                        print_folder_recursive_local(child_uuid, indent + "  ")
                    elif child_item and isinstance(child_item, InventoryItem):
                        logging.info(f"{indent}  L {child_item.name} ({child_item.inv_type.name if hasattr(child_item, 'inv_type') and child_item.inv_type else 'N/A'}) ({child_item.uuid})")
                    elif child_item:
                        logging.info(f"{indent}  ? {child_item.name} ({type(child_item).__name__}) ({child_item.uuid})")
                    else:
                        logging.info(f"{indent}  ! Child UUID {child_uuid} not found in skeleton (ghost child).")
            elif folder and isinstance(folder, InventoryItem): # If a root UUID points to an item somehow
                 logging.info(f"{indent}Item (not folder): {folder.name} ({folder.uuid})")
            else:
                logging.info(f"{indent}Folder/Item UUID {folder_uuid} not found in skeleton or not a folder.")

        if inventory_mgr.inventory_root_uuid:
            logging.info("--- Recursive Inventory Print (Root) ---")
            print_folder_recursive_local(inventory_mgr.inventory_root_uuid)
            logging.info("--- End of Recursive Inventory Print (Root) ---")

        # Optionally, print library too if populated
        # if inventory_mgr.library_root_uuid:
        #     logging.info("--- Recursive Inventory Print (Library) ---")
        #     print_folder_recursive_local(inventory_mgr.library_root_uuid)
        #     logging.info("--- End of Recursive Inventory Print (Library) ---")

        # Attempt to find and wear a wearable item (existing logic)
        wearable_item_to_test = None
        target_wearable_types = [WearableType.Shirt, WearableType.Pants, WearableType.Jacket] # Prioritize these

        for item_obj in inventory_items.values():
            if hasattr(item_obj, 'wearable_type'): # Check if it's an InventoryItem with the property
                item_wearable_type = item_obj.wearable_type
                if item_wearable_type in target_wearable_types:
                    wearable_item_to_test = item_obj
                    logging.info(f"Found suitable wearable to test: {wearable_item_to_test.name} (Type: {item_wearable_type.name}, UUID: {wearable_item_to_test.uuid})")
                    break

        if wearable_item_to_test:
            logging.info(f"Attempting to wear item: {wearable_item_to_test.name} ({wearable_item_to_test.uuid})")
            async def wear_and_log():
                await asyncio.sleep(2) # Give a moment for inventory processing to settle if needed

                logging.info(f"--- Attempting to wear: {wearable_item_to_test.name} ---")
                await test_client_instance.appearance.wear_items([wearable_item_to_test])
                logging.info(f"wear_items called for {wearable_item_to_test.name}. Calling set_appearance...")
                await asyncio.sleep(1) # Give a moment for internal state
                await test_client_instance.appearance.set_appearance() # Update appearance after wearing

                logging.info(f"--- Waiting for 10 seconds after wearing {wearable_item_to_test.name} ---")
                await asyncio.sleep(10)

                logging.info(f"--- Attempting to take off: {wearable_item_to_test.name} ---")
                await test_client_instance.appearance.take_off_items([wearable_item_to_test])
                logging.info(f"take_off_items called for {wearable_item_to_test.name}. Calling set_appearance...")
                await asyncio.sleep(1) # Give a moment for internal state
                await test_client_instance.appearance.set_appearance() # Update appearance after taking off

            asyncio.create_task(wear_and_log())
        else:
            logging.info("No suitable wearable item (Shirt, Pants, Jacket) found in inventory to test wearing.")


async def main():
    global test_client_instance
    client = GridClient(); test_client_instance = client
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s-%(name)s-%(levelname)s-%(threadName)s-%(message)s')
    logging.getLogger("pylibremetaverse").setLevel(logging.DEBUG)

    creds={"first":os.getenv("PYLIBREMV_FIRSTNAME","Test"),"last":os.getenv("PYLIBREMV_LASTNAME","Bot"),"pass":os.getenv("PYLIBREMV_PASSWORD","password"),"uri":os.getenv("PYLIBREMV_LOGINURI",client.settings.AGNI_LOGIN_SERVER)}
    if creds["first"]=="Test": logging.warning("Using default credentials. Set PYLIBREMV_* env vars.")

    client.network.register_login_progress_handler(login_progress_callback)
    client.network.register_sim_connected_handler(sim_connected_callback)
    client.network.register_sim_disconnected_handler(sim_disconnected_callback)
    client.network.register_disconnected_handler(network_disconnected_callback)
    client.self.register_chat_handler(on_chat_received); client.self.register_im_handler(on_im_received)
    client.self.register_teleport_progress_handler(on_teleport_progress)
    client.self.register_avatar_sit_response_handler(on_avatar_sit_response)
    client.self.register_teleport_lure_offered_handler(on_teleport_lure_offered)
    client.self.register_script_dialog_handler(on_script_dialog)
    client.self.register_script_question_handler(on_script_question)
    client.self.register_mute_list_updated_handler(on_mute_list_updated)
    client.appearance.register_wearables_updated_handler(on_wearables_updated)
    client.objects.register_object_updated_handler(on_object_updated)
    client.objects.register_object_removed_handler(on_object_removed)
    client.inventory.register_inventory_updated_handler(on_inventory_updated)
    # FriendsManager handlers
    client.friends.register_friendship_offered_handler(on_friendship_offered)
    client.friends.register_friendship_response_handler(on_friendship_response)
    client.friends.register_online_status_changed_handler(on_friend_online_status_changed)
    client.friends.register_rights_changed_handler(on_friend_rights_changed) # Added
    client.friends.register_friend_removed_handler(on_friend_removed) # Added

    logging.info(f"Login: {creds['first']} {creds['last']} to {creds['uri']}...")
    success = False
    try:
        success = await client.network.login(creds["first"],creds["last"],creds["pass"], "PyLibreMVTest","0.1.0","last",creds["uri"])
        if success and client.network.logged_in:
            logging.info(f"Login OK! Agent: {client.network.agent_id}, Sim: {client.network.current_sim.name if client.network.current_sim else 'N/A'}")
            if client.network.current_sim and client.network.current_sim.handshake_complete:
                logging.info("Test actions...")
                await client.self.play_animation(Animations.WAVE); await asyncio.sleep(3); await client.self.stop_animation(Animations.WAVE)

                # --- Test ObjectAdd (Rez a prim) ---
                if client.network.current_sim: # Ensure sim is still valid
                    logging.info("--- Attempting to rez a default prim (cube) ---")
                    # Define default texture entry (can be more specific if needed)
                    # A simple TE with a blank texture UUID for all faces
                    blank_texture_uuid = CustomUUID("00000000-0000-0000-0000-000000000000") # Or a known valid one
                    num_faces = 1 # For a simple non-torus/sphere prim. More complex prims need more faces.
                                  # For a default box (PCode.Prim), it's 6 faces in some contexts, but ObjectAdd TE might be simpler.
                                  # C# ObjectAddPacket uses a single DefaultTexture field in its TextureEntryBlock.
                                  # For now, a minimal TE.
                    te_bytes_list = []
                    for i in range(num_faces):
                        te_bytes_list.extend(blank_texture_uuid.get_bytes()) # TextureID
                        te_bytes_list.extend(Color4(1.0,1.0,1.0,1.0).get_bytes_rgba()) # Color
                        te_bytes_list.extend(struct.pack('<ff', 1.0, 1.0)) # RepeatsU, RepeatsV
                        te_bytes_list.extend(struct.pack('<f', 0.0))      # OffsetU
                        te_bytes_list.extend(struct.pack('<f', 0.0))      # OffsetV
                        te_bytes_list.extend(struct.pack('<B', 0))        # TexFlags (was uint, now byte in some contexts)
                        te_bytes_list.extend(struct.pack('<B', 255))      # Bump (was uint, now byte) - 255 for shiny
                        te_bytes_list.extend(struct.pack('<B', 0))        # MediaFlags (byte)
                        # Total per face: 16 (UUID) + 4 (Color) + 8 (Repeats) + 8 (Offset) + 1 (Flags) + 1 (Bump) + 1 (Media) = 39 bytes.
                        # This doesn't match Primitive.TEXTURE_ENTRY_DEFAULT_SIZE (470) or C# TE structure for ObjectAdd.
                        # C# ObjectAddPacket.TextureEntryBlock is 17 bytes: DefaultTexture (16) + MediaFlags (1)

                    # Using C# ObjectAddPacket.TextureEntryBlock structure: 16 byte UUID + 1 byte MediaFlags
                    default_te_bytes = blank_texture_uuid.get_bytes() + bytes([0]) # Default texture ID + media flags (0)

                    # Path parameters for a default prim
                    path_p = {
                        'curve': PathCurve.LINE, 'begin': 0.0, 'end': 1.0,
                        'scale_x': 1.0, 'scale_y': 1.0, 'shear_x': 0.0, 'shear_y': 0.0,
                        'twist': 0.0, 'twist_begin': 0.0, 'radius_offset': 0.0,
                        'taper_x': 0.0, 'taper_y': 0.0, 'revolutions': 1.0, 'skew': 0.0
                    }
                    # Profile parameters for a default cube
                    profile_p = {'curve': ProfileCurve.SQUARE, 'begin': 0.0, 'end': 1.0, 'hollow': 0.0}

                    rez_scale = Vector3(0.5, 0.5, 0.5)
                    rez_rot = Quaternion.IDENTITY
                    # Position for add_prim is the target for raycast end if bypass_raycast is True
                    # The actual rez position will be ray_end_offset from agent
                    rez_target_pos = client.self.movement.position + Vector3(2.0, 0.0, 0.0) # Target in front of agent

                    await client.objects.add_prim(
                        simulator=client.network.current_sim,
                        pcode=PCode.Primitive, # Box
                        material=Material.WOOD,
                        add_flags=AddFlags.CREATE_SELECTED, # Rez selected
                        path_params=path_p,
                        profile_params=profile_p,
                        position=rez_target_pos, # Target for raycast
                        scale=rez_scale,
                        rotation=rez_rot,
                        texture_entry_bytes=default_te_bytes,
                        ray_end_offset=Vector3(2.0, 0.0, 0.0) # Rez 2m in front of agent
                    )
                    logging.info("--- ObjectAddPacket sent for a cube. Check in-world. ---")
                    await asyncio.sleep(2) # Give time for object to appear and be updated

                # Example Object Interaction (Commented out, requires known LocalIDs from logs)
                # objects_in_sim = client.objects.get_prims_in_sim(client.network.current_sim)
                # if objects_in_sim:
                #     target_prim_to_select = None
                #     # Try to find a prim named "MyTestPrim" or take the first one otherwise
                #     for p in objects_in_sim:
                #         if p.name == "MyTestPrim": target_prim_to_select = p; break
                #     if not target_prim_to_select and objects_in_sim: target_prim_to_select = objects_in_sim[0]

                #     if target_prim_to_select:
                #         logging.info(f"Attempting to select object LID: {target_prim_to_select.local_id} ({target_prim_to_select.name})")
                #         await client.objects.select_object(client.network.current_sim, target_prim_to_select.local_id)
                #         await asyncio.sleep(2)
                #         logging.info(f"Attempting to deselect object LID: {target_prim_to_select.local_id}")
                #         await client.objects.deselect_object(client.network.current_sim, target_prim_to_select.local_id)
                #         await asyncio.sleep(1)

                #     # To test linking, you'd need at least two known local IDs (e.g. from selecting them first)
                #     # if len(objects_in_sim) >= 2:
                #     #    root_prim = objects_in_sim[0]
                #     #    child_prim = objects_in_sim[1]
                #     #    logging.info(f"Attempting to link LIDs: {root_prim.local_id} and {child_prim.local_id}")
                #     #    await client.objects.link_objects(client.network.current_sim, [root_prim.local_id, child_prim.local_id])
                #     #    await asyncio.sleep(5)
                #     #    logging.info(f"Attempting to delink LID: {root_prim.local_id}")
                #     #    await client.objects.delink_objects(client.network.current_sim, [root_prim.local_id])
                # else:
                #     logging.info("No objects found in sim to test selection/linking.")

                # Extended idle time to observe wearable changes if any
                logging.info("Client will now idle for 10 seconds before friendship test.")
                await asyncio.sleep(10)

                # --- Test Friendship Offer ---
                # Replace with a known UUID of an alt or another bot for testing.
                # Ensure the target avatar is online and can receive friendship offers.
                target_friend_uuid_str = os.getenv("PYLIBREMV_FRIEND_TEST_UUID", "00000000-0000-0000-0000-000000000000")
                if target_friend_uuid_str != "00000000-0000-0000-0000-000000000000":
                    target_friend_uuid = CustomUUID(target_friend_uuid_str)
                    logging.info(f"--- Attempting to offer friendship to {target_friend_uuid} ---")
                    await client.friends.offer_friendship(target_friend_uuid, "Hello from PyLibreMetaverse test client!")
                    # Wait for a response or timeout (handled by IMs and logged by handlers)
                    await asyncio.sleep(10) # Wait to see if response comes in
                else:
                    logging.warning("PYLIBREMV_FRIEND_TEST_UUID not set. Skipping friendship offer test.")

                # Request online status for all known friends after a short delay
                await asyncio.sleep(2) # Ensure buddy list might have been processed
                if client.friends.friends: # Check if there are any friends
                    friend_uuids_to_query = list(client.friends.friends.keys())
                    logging.info(f"--- Requesting online status for {len(friend_uuids_to_query)} friends... ---")
                    asyncio.create_task(client.friends.request_online_statuses(friend_uuids_to_query))
                else:
                    logging.info("No friends in the list to query for online status.")

                # --- Test Grant Rights and Terminate Friendship ---
                # This needs a specific friend UUID to target.
                # For safety, use a dedicated test alt or bot UUID.
                # You might want to run this part conditionally based on an env var.
                # Example: PYLIBREMV_FRIEND_MODIFY_UUID
                modify_friend_uuid_str = os.getenv("PYLIBREMV_FRIEND_MODIFY_UUID")
                if modify_friend_uuid_str:
                    modify_friend_uuid = CustomUUID(modify_friend_uuid_str)
                    if client.friends.is_friend(modify_friend_uuid):
                        logging.info(f"--- Testing rights management for friend {modify_friend_uuid} ---")
                        # Grant additional rights (e.g., modify objects)
                        new_rights = FriendRights.CAN_SEE_ONLINE | FriendRights.CAN_SEE_ON_MAP | FriendRights.CAN_MODIFY_OBJECTS
                        logging.info(f"Granting rights {new_rights!r} to {modify_friend_uuid}")
                        await client.friends.grant_rights(modify_friend_uuid, new_rights)
                        await asyncio.sleep(5) # Wait for potential updates or just to observe logs

                        # Example: Terminate friendship (use with extreme caution on real accounts)
                        terminate_this_friend = os.getenv("PYLIBREMV_TERMINATE_FRIEND_TEST", "false").lower() == "true"
                        if terminate_this_friend:
                            logging.info(f"--- Attempting to terminate friendship with {modify_friend_uuid} ---")
                            await client.friends.terminate_friendship(modify_friend_uuid)
                            await asyncio.sleep(2)
                        else:
                            logging.info(f"Skipping terminate_friendship test for {modify_friend_uuid} (PYLIBREMV_TERMINATE_FRIEND_TEST not true).")
                    else:
                        logging.warning(f"Cannot test rights/terminate: {modify_friend_uuid} is not currently a friend.")
                else:
                    logging.info("PYLIBREMV_FRIEND_MODIFY_UUID not set. Skipping grant_rights/terminate_friendship tests.")


                logging.info("Client will now idle for another 10 seconds.")
                await asyncio.sleep(10)

            else: logging.warning("No handshaked sim. Skipping test actions."); await asyncio.sleep(5)
            logging.info("Attempting logout..."); await client.network.logout(); await asyncio.sleep(2)
        else: logging.error(f"Login failed. Status: {client.network.login_status.name if client.network.login_status else 'N/A'}, Msg: {client.network.login_message}")
    except Exception as e: logging.exception(f"Client op error: {e}")
    finally:
        logging.info("Client session ending.");
        if client.network.logged_in : await client.network.logout()
        else: client.network.shutdown("ClientTestEnd","Test ended")
        await asyncio.sleep(1); test_client_instance=None; logging.info("Client shut down.")

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logging.info("Terminated by user.")
    except Exception as e: logging.exception(f"Unhandled exception: {e}")
    finally: logging.info("Exiting.")


# --- Friendship Handlers ---
def on_friendship_offered(offerer_uuid: CustomUUID, offerer_name: str, message: str, session_id: CustomUUID):
    logging.info(f"[FriendshipOffered] From: {offerer_name} ({offerer_uuid}), Message: '{message}', SessionID: {session_id}")
    # Example: Automatically accept offers from a specific test agent or if a keyword is in the message
    # For general testing, you might want to log and manually decide or have a more complex auto-accept rule.
    auto_accept_offer = os.getenv("PYLIBREMV_AUTO_ACCEPT_FRIENDSHIP", "false").lower() == "true"

    if auto_accept_offer and test_client_instance:
        logging.info(f"Auto-accepting friendship offer from {offerer_name} ({offerer_uuid}).")
        asyncio.create_task(test_client_instance.friends.accept_friendship_offer(offerer_uuid, session_id))
    # To decline:
    # asyncio.create_task(test_client_instance.friends.decline_friendship_offer(offerer_uuid, session_id))

def on_friendship_response(friend_uuid: CustomUUID, accepted: bool):
    logging.info(f"[FriendshipResponse] From: {friend_uuid}, Accepted: {accepted}")
    if accepted:
        logging.info(f"Friendship with {friend_uuid} is now active (or was already).")
    else:
        logging.info(f"Friendship with {friend_uuid} was declined or terminated.")

def on_friend_online_status_changed(args: FriendOnlineStatusEventArgs):
    logging.info(f"[FriendOnlineStatus] Friend: {args.friend_uuid}, Online: {args.is_online}")
    # You could add more logic here, e.g., update a local UI or list of online friends.

def on_friend_rights_changed(args: FriendRightsEventArgs):
    logging.info(f"[FriendRightsChanged] Friend: {args.friend_uuid}, TheirRightsToUs: {args.their_rights_to_us!r}, OurRightsToThem: {args.our_rights_to_them!r}")

def on_friend_removed(args: FriendRemovedEventArgs):
    logging.info(f"[FriendRemoved] Friend: {args.friend_uuid} has been removed from friends list.")


async def create_test_script(inventory_mgr: InventoryManager):
    """Tests creating and uploading a new LSL script asset and then creating an inventory item for it."""
    if not test_client_instance or not test_client_instance.assets or not inventory_mgr.inventory_root_uuid:
        logging.error("Cannot create test script: Client, AssetManager, or inventory root not available.")
        return

    logging.info("--- Attempting to create and upload a new LSL script... ---")
    # Make the script larger than SMALL_ASSET_THRESHOLD_BYTES (1024) to test Xfer path
    lsl_code_base = "default { state_entry() { llSay(0, \"Hello, PyLibreMetaverse Script! This is a test script designed to be larger than 1KB to test the Xfer upload mechanism. Padding... Padding... Padding...\"); } }"
    padding_needed = 1024 - len(lsl_code_base) + 50 # Ensure it's definitely over
    if padding_needed < 0: padding_needed = 0
    lsl_code = lsl_code_base + (" " * padding_needed) + "\n// End of padding."

    logging.info(f"Test script content generated (Length: {len(lsl_code)} bytes). Target threshold: {test_client_instance.assets.SMALL_ASSET_THRESHOLD_BYTES if test_client_instance else 'N/A'}")

    script_asset = AssetScript(script_text=lsl_code)
    script_asset.name = f"PyTestScript_Xfer_{datetime.datetime.now().strftime('%H%M%S')}"
    script_asset.description = "A test script (potentially large) created by PyLibreMetaverse test client."
    # AssetType.LSLText is set by default in AssetScript __post_init__

    logging.info(f"Attempting to upload script asset: Name='{script_asset.name}', Size={len(script_asset.to_upload_bytes())}, Type={script_asset.asset_type.name}")

    try:
        upload_success, new_asset_uuid, uploaded_asset_type = await test_client_instance.assets.upload_asset_object(
            script_asset
        )

        logging.info(f"upload_asset_object result: Success={upload_success}, AssetUUID={new_asset_uuid}, AssetType={uploaded_asset_type.name if uploaded_asset_type else 'N/A'}")

        if upload_success and new_asset_uuid:
            logging.info(f"Script asset uploaded successfully. New Asset UUID: {new_asset_uuid}. Now creating inventory item...")

            # Define permissions for the new script item
            # Full perms for owner, typically Copy/Mod/Trans for next owner for scripts.
            # No perms for group or everyone by default unless specified.
            default_permissions = {
                'base_mask': PermissionMask.ALL, # Base perms of the item itself (usually not directly relevant for scripts as they use next_owner)
                'owner_mask': PermissionMask.ALL,
                'group_mask': PermissionMask.NONE,
                'everyone_mask': PermissionMask.NONE,
                'next_owner_mask': PermissionMask.COPY | PermissionMask.MODIFY | PermissionMask.TRANSFER,
            }
            logging.info(f"Using permissions for new script item: Owner={default_permissions['owner_mask']!r}, NextOwner={default_permissions['next_owner_mask']!r}")

            created_item = await inventory_mgr.create_inventory_item(
                parent_folder_uuid=inventory_mgr.inventory_root_uuid,
                name=script_asset.name,
                description=script_asset.description,
                asset_type=AssetType.LSLText,
                inv_type=InventoryType.LSL,
                asset_uuid=new_asset_uuid, # Use the UUID from the successful asset upload
                permissions=default_permissions
            )

            if created_item:
                logging.info(f"Script inventory item CREATED AND CONFIRMED: Name='{created_item.name}', ItemID='{created_item.uuid}', AssetID='{created_item.asset_uuid}', CRC={created_item.crc32}")
                logging.info(f"  Full details: {created_item}")
            else:
                logging.error(f"Failed to create script inventory item for asset {new_asset_uuid} (create_inventory_item returned None).")
        else:
            logging.error(f"Failed to upload script asset. Success: {upload_success}, Asset UUID: {new_asset_uuid}, Type: {uploaded_asset_type.name if uploaded_asset_type else 'N/A'}")
    except Exception as e:
        logging.exception(f"Exception during script creation/upload: {e}")