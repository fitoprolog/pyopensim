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
    PCode, Material, AddFlags, PathCurve, ProfileCurve, FolderType, ImageType
)
from pylibremetaverse.types.animations import Animations
from pylibremetaverse.types.color import Color4 # For TE generation
from pylibremetaverse.types.inventory_defs import InventoryBase, InventoryFolder, InventoryItem # For type checking in print_folder_recursive
import struct # For TE generation
from pylibremetaverse.types.enums import AssetType # For on_asset_received type hint
# Import Asset base and subclasses for type checking in on_asset_received
from pylibremetaverse.assets import Asset, AssetNotecard, AssetLandmark

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
    # if test_client_instance and test_client_instance.appearance.wearables: # Check if wearables are populated
    #     placeholder_te = bytes([0]*Primitive.TEXTURE_ENTRY_DEFAULT_SIZE)
    #     asyncio.create_task(test_client_instance.appearance.set_appearance(texture_entry_override=placeholder_te))

    # --- Test Texture Request ---
    if test_client_instance:
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
        if isinstance(asset_obj_or_data, AssetNotecard) and asset_obj_or_data.loaded_successfully:
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

def on_inventory_updated(inventory_items: Dict[CustomUUID, InventoryBase]): # Added
    """Called when the inventory skeleton is updated."""
    logging.info(f"[InventoryUpdated] Inventory skeleton potentially updated. Current total: {len(inventory_items)} items/folders.")

    if test_client_instance:
        inventory_mgr = test_client_instance.inventory

        # --- Test Create Folder ---
        # Run this test only once, e.g., by checking a flag on the client or a specific condition
        if inventory_mgr.inventory_root_uuid and not hasattr(test_client_instance, '_folder_created_test_done'):
            test_client_instance._folder_created_test_done = True # Set flag to run once

            async def create_folder_test():
                await asyncio.sleep(5) # Wait a bit after initial inventory load
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

            asyncio.create_task(create_folder_test())

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
                logging.info(f"wear_items called for {wearable_item_to_test.name}. Check server/viewer for appearance change.")

                logging.info(f"--- Waiting for 10 seconds after wearing {wearable_item_to_test.name} ---")
                await asyncio.sleep(10)

                logging.info(f"--- Attempting to take off: {wearable_item_to_test.name} ---")
                await test_client_instance.appearance.take_off_items([wearable_item_to_test])
                logging.info(f"take_off_items called for {wearable_item_to_test.name}. Check server/viewer for appearance change.")

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
                logging.info("Client will now idle for 20 seconds to observe potential appearance changes.")
                await asyncio.sleep(20)
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
