import logging
import asyncio
import dataclasses
import time # For xfer tracking
from typing import TYPE_CHECKING, Dict, List, Callable, Tuple, Any, cast

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import AssetType, ChannelType, TargetType, StatusCode, TransferStatus, ImageType # Added ImageType
from pylibremetaverse.network.packets_asset import (
    RequestXferPacket, SendXferPacket, ConfirmXferPacket,
    TransferInfoPacket, TransferPacket,
    RequestImagePacket, ImageDataPacket, ImageNotInDatabasePacket # Added Image packets
)
from pylibremetaverse.network.packet_protocol import IncomingPacket
# Assuming HttpCapsClient might be used if not already part of self.client.network.current_sim.http_caps_client
# import httpx
from pylibremetaverse.network.packets_base import Packet, PacketType


if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class Transfer: # Used for both Xfer and Image UDP transfers
    id: int | CustomUUID # XferID (u64 int for old Xfer) or Asset/TextureID (CustomUUID for new Xfer/Image UDP)
    vfile_id_for_callback: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # VFileID for handler lookup
    asset_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Actual asset UUID, esp. for textures
    asset_type: AssetType = AssetType.Unknown
    image_type: ImageType | None = None # Specific for ImageType requests
    size: int = 0
    received_bytes: int = 0
    data: bytearray = dataclasses.field(default_factory=bytearray)
    status: TransferStatus = TransferStatus.Unknown
    channel: ChannelType = ChannelType.Unknown
    target: TargetType = TargetType.Unknown
    last_packet_num: int = -1 # For SendXferPacket system (UDP Xfer)

    # For UDP Image System
    udp_packets_expected: int = 0
    udp_packets_received: set[int] = dataclasses.field(default_factory=set)
    # Note: ImageDataPacket doesn't have explicit packet numbers for chunks,
    # so udp_packets_received might track byte offsets or assume ordered delivery for now.
    # For simplicity, we'll use received_bytes vs size for completion.

# Import new asset classes
from pylibremetaverse.assets import Asset, AssetNotecard, AssetLandmark

AssetReceivedHandler = Callable[[bool, Asset | bytes | None, AssetType, CustomUUID, CustomUUID | None, str | None], Any]
# Changed `bytes | None` to `Asset | bytes | None` for the data parameter

class AssetManager:
    def __init__(self, client: 'GridClient'):
        self.client = client
        self.current_xfers: Dict[int | CustomUUID, Transfer] = {}
        self._asset_received_handlers: Dict[CustomUUID, List[AssetReceivedHandler]] = {}

        if self.client.network:
            reg = self.client.network.register_packet_handler
            reg(PacketType.TransferInfo, self._on_transfer_info_wrapper)
            reg(PacketType.TransferPacket, self._on_transfer_packet_wrapper)
            reg(PacketType.SendXferPacket, self._on_send_xfer_wrapper)
            # Register handlers for UDP image packets
            reg(PacketType.ImageData, self._on_image_data_wrapper)
            reg(PacketType.ImageNotInDatabase, self._on_image_not_in_database_wrapper)
        else: logger.error("AssetManager: NetworkManager not available at init.")

    def _on_transfer_info_wrapper(self,s,p): isinstance(p,TransferInfoPacket) and self._on_transfer_info(s,p)
    def _on_transfer_packet_wrapper(self,s,p): isinstance(p,TransferPacket) and self._on_transfer_packet(s,p)
    def _on_send_xfer_wrapper(self,s,p): isinstance(p,SendXferPacket) and self._on_send_xfer(s,p)
    def _on_image_data_wrapper(self,s,p): isinstance(p,ImageDataPacket) and self._on_image_data(s,p)
    def _on_image_not_in_database_wrapper(self,s,p): isinstance(p,ImageNotInDatabasePacket) and self._on_image_not_in_database(s,p)


    def register_asset_received_handler(self, vfile_id: CustomUUID, callback: AssetReceivedHandler):
        if vfile_id not in self._asset_received_handlers: self._asset_received_handlers[vfile_id] = []
        if callback not in self._asset_received_handlers[vfile_id]: self._asset_received_handlers[vfile_id].append(callback)

    def unregister_asset_received_handler(self, vfile_id: CustomUUID, callback: AssetReceivedHandler):
        if vfile_id in self._asset_received_handlers and callback in self._asset_received_handlers[vfile_id]:
            self._asset_received_handlers[vfile_id].remove(callback)
            if not self._asset_received_handlers[vfile_id]: del self._asset_received_handlers[vfile_id]

    def _fire_asset_received(self, vfile_id_for_callback: CustomUUID, success: bool, data: bytes | None,
                             asset_type_enum: AssetType, asset_uuid: CustomUUID,
                             error_message: str | None = None):
        # asset_uuid is the actual ID of the asset, vfile_id_for_callback is the key used for handler lookup

        parsed_asset_obj: Asset | bytes | None = None # Initialize to None or raw data

        if success and data:
            if asset_type_enum == AssetType.Notecard:
                parsed_asset_obj = AssetNotecard(asset_id=asset_uuid, asset_type=asset_type_enum)
            elif asset_type_enum == AssetType.Landmark:
                parsed_asset_obj = AssetLandmark(asset_id=asset_uuid, asset_type=asset_type_enum)
            # Add elif for AssetTexture, AssetSound etc. here when those classes are defined
            # For example:
            # elif asset_type_enum == AssetType.Texture:
            #     parsed_asset_obj = AssetTexture(asset_id=asset_uuid, asset_type=asset_type_enum)
            else: # Default for unspecialized types or if specific parsing not yet implemented
                parsed_asset_obj = Asset(asset_id=asset_uuid, asset_type=asset_type_enum)

            if isinstance(parsed_asset_obj, Asset): # Check if it's one of our asset classes
                if not parsed_asset_obj.from_bytes(data): # from_bytes does the actual parsing
                    logger.warning(f"Failed to parse {asset_type_enum.name} asset {asset_uuid}. Passing raw data to callback.")
                    # parsed_asset_obj.loaded_successfully will be False, callback can check this
                    # Or, pass raw data instead if parsing fails badly:
                    # parsed_asset_obj = data
                else:
                    logger.info(f"Successfully parsed {asset_type_enum.name} asset {asset_uuid} into {type(parsed_asset_obj).__name__}")
            else: # Should not happen if logic above is correct
                parsed_asset_obj = data # Fallback to raw data if instantiation failed
        else: # Not successful, or no data
            parsed_asset_obj = data # Pass None or potentially error data if any

        if vfile_id_for_callback in self._asset_received_handlers:
            handlers_to_call = self._asset_received_handlers.pop(vfile_id_for_callback, [])
            for handler in handlers_to_call:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(success, parsed_asset_obj, asset_type_enum, asset_uuid, vfile_id_for_callback, error_message))
                    else:
                        handler(success, parsed_asset_obj, asset_type_enum, asset_uuid, vfile_id_for_callback, error_message)
                except Exception as e: logger.error(f"Error in asset_received_handler for {vfile_id_for_callback} (Asset: {asset_uuid}): {e}")
        else:
            logger.debug(f"No specific handlers for asset VFileID {vfile_id_for_callback} (Asset: {asset_uuid}). Success: {success}. Parsed type: {type(parsed_asset_obj).__name__ if parsed_asset_obj else 'N/A'}")

    def _on_transfer_info(self, source_sim: 'Simulator', packet: TransferInfoPacket):
        logger.debug(f"Rcvd TransferInfo: ID={packet.transfer_id}, Chan={packet.channel_type.name}, Target={packet.target_type.name}, Status={packet.status_code.name}, Size={packet.size}, Params='{packet.params_str}'")

        # TransferInfo's packet.transfer_id is the VFileID (often item_id)
        transfer = self.current_xfers.get(packet.transfer_id)
        if not transfer: # Should have been created by request_asset_xfer or request_texture (if UDP path was taken first)
            # This case implies TransferInfo came for an unsolicited or untracked transfer.
            transfer = Transfer(
                id=packet.transfer_id, # For Xfers, id is VFileID. For UDP Image, id is texture_uuid.
                vfile_id_for_callback=packet.transfer_id,
                asset_uuid = packet.transfer_id, # Assuming it's the asset itself if not otherwise known
                size=packet.size,
                channel=packet.channel_type,
                target=packet.target_type,
                status=TransferStatus.WaitingForInfo
            )
            # AssetType needs to be inferred or set if a generic request_asset was made.
            # For textures, request_texture would set it.
            self.current_xfers[packet.transfer_id] = transfer
            logger.info(f"New transfer initiated by TransferInfo: VFileID={packet.transfer_id}, Size={packet.size}")
        else:
            transfer.size = packet.size
            transfer.channel = packet.channel_type
            transfer.target = packet.target_type
            logger.info(f"Updated existing transfer with TransferInfo: VFileID={packet.transfer_id} (Asset: {transfer.asset_uuid})")

        if packet.status_code not in [StatusCode.OK, StatusCode.CREATED, StatusCode.NO_CONTENT]:
            logger.warning(f"TransferInfo problem: Status={packet.status_code.name}. Transfer for {packet.transfer_id} (Asset: {transfer.asset_uuid}) might fail/end.")
            transfer.status = TransferStatus.Error
            self._fire_asset_received(transfer.vfile_id_for_callback, False, None, transfer.asset_type, transfer.asset_uuid,
                                      f"TransferInfo status: {packet.status_code.name} - {packet.params_str}")
            if packet.transfer_id in self.current_xfers: del self.current_xfers[packet.transfer_id]
        elif transfer.status == TransferStatus.WaitingForInfo :
             transfer.status = TransferStatus.Queued

    def _on_transfer_packet(self, source_sim: 'Simulator', packet: TransferPacket):
        logger.debug(f"Rcvd TransferPacket: ID={packet.transfer_id}, Chan={packet.channel_type.name}, DataLen={len(packet.data)}")
        transfer = self.current_xfers.get(packet.transfer_id)
        if not transfer:
            logger.warning(f"TransferPacket for unknown TransferID {packet.transfer_id}. Implicitly creating.")
            transfer = Transfer(
                id=packet.transfer_id,
                vfile_id_for_callback=packet.transfer_id,
                asset_uuid=packet.transfer_id, # Assuming direct asset if no prior context
                channel=packet.channel_type,
                status=TransferStatus.InProgress
            )
            self.current_xfers[packet.transfer_id] = transfer

        transfer.data.extend(packet.data); transfer.received_bytes += len(packet.data)
        transfer.status = TransferStatus.InProgress

        is_complete = False
        if transfer.size > 0 and transfer.received_bytes >= transfer.size: is_complete = True
        elif transfer.size == 0 and not packet.data: is_complete = True

        if is_complete:
            transfer.status = TransferStatus.Done
            logger.info(f"Transfer complete for VFileID {transfer.vfile_id_for_callback} (Asset: {transfer.asset_uuid}). Total bytes: {transfer.received_bytes}")
            self._fire_asset_received(transfer.vfile_id_for_callback, True, bytes(transfer.data), transfer.asset_type, transfer.asset_uuid)
            if packet.transfer_id in self.current_xfers: del self.current_xfers[packet.transfer_id]


    def _on_send_xfer(self, source_sim: 'Simulator', packet: SendXferPacket):
        logger.debug(f"Rcvd SendXferPacket: XferID={packet.xfer_id}, PktNum={packet.packet_num}, DataLen={len(packet.data)}")
        transfer = self.current_xfers.get(cast(int, packet.xfer_id)) # XferID is int for this old system
        if not transfer:
            logger.warning(f"SendXferPacket for unknown XferID {packet.xfer_id}. Creating new (old system).")
            # VFileID and AssetType might be unknown here if TransferInfo was not received.
            transfer = Transfer(id=packet.xfer_id, status=TransferStatus.InProgress)
            self.current_xfers[packet.xfer_id] = transfer

        if packet.packet_num <= transfer.last_packet_num and transfer.last_packet_num != -1:
            logger.warning(f"Duplicate/out-of-order SendXfer PktNum {packet.packet_num} for XferID {packet.xfer_id}.")
        else:
            transfer.data.extend(packet.data); transfer.received_bytes += len(packet.data)
            transfer.last_packet_num = packet.packet_num
        transfer.status = TransferStatus.InProgress

        confirm = ConfirmXferPacket(xfer_id=packet.xfer_id, packet_num=packet.packet_num)
        asyncio.create_task(self.client.network.send_packet(confirm, source_sim))

        if not packet.data: # End of Xfer signaled by empty data chunk
            transfer.status = TransferStatus.Done
            logger.info(f"Transfer complete (SendXfer) for XferID {transfer.id} (VFileID: {transfer.vfile_id_for_callback}, Asset: {transfer.asset_uuid}). Bytes: {transfer.received_bytes}")
            self._fire_asset_received(transfer.vfile_id_for_callback, True, bytes(transfer.data), transfer.asset_type, transfer.asset_uuid)
            if packet.xfer_id in self.current_xfers: del self.current_xfers[packet.xfer_id]


    async def request_asset_xfer(self, filename: str, use_big_packets: bool,
                                 vfile_id: CustomUUID, vfile_type: AssetType,
                                 item_id_for_callback: CustomUUID | None = None, # This is the vfile_id_for_callback
                                 delete_on_completion: bool = False
                                 ) -> int:
        current_sim = self.client.network.current_sim
        actual_vfile_id_for_callback = item_id_for_callback or vfile_id
        if not current_sim or not current_sim.handshake_complete:
            logger.warning("Cannot request asset xfer: No sim."); self._fire_asset_received(actual_vfile_id_for_callback, False,None,vfile_type, vfile_id, "No simulator"); return 0

        # Client generates a u64 XferID for RequestXfer, often random or pseudo-random.
        # Server might use this in SendXfer system, or ignore it for TransferInfo/TransferPacket system.
        client_xfer_id = (self.client.self.agent_id.crc() ^ vfile_id.crc() ^ int(time.time()*1000)) & 0xFFFFFFFFFFFFFFFF

        req_packet = RequestXferPacket(filename, delete_on_completion, use_big_packets, vfile_id, vfile_type)
        req_packet.xfer_id = client_xfer_id


        req_packet = RequestXferPacket(filename, delete_on_completion, use_big_packets, vfile_id, vfile_type)
        req_packet.xfer_id = client_xfer_id

        # Create a Transfer object to track this request, keyed by VFileID for new system,
        # and potentially also by client_xfer_id if old system is used.
        # The `id` field of Transfer will store client_xfer_id for old system, or vfile_id for new.
        if actual_vfile_id_for_callback in self._asset_received_handlers or True: # Always create if making request
            if actual_vfile_id_for_callback not in self.current_xfers:
                transfer_obj = Transfer(
                    id=vfile_id, # For new system, TransferID is VFileID
                    vfile_id_for_callback=actual_vfile_id_for_callback,
                    asset_uuid=vfile_id, # The actual asset being fetched
                    asset_type=vfile_type,
                    status=TransferStatus.Queued
                )
                self.current_xfers[vfile_id] = transfer_obj # Key by VFileID
                # If old system (SendXfer) might use client_xfer_id, map it too
                # but ensure it doesn't overwrite a VFileID entry if they are coincidentally same
                if client_xfer_id != vfile_id and client_xfer_id not in self.current_xfers:
                     # This is tricky; old system is keyed by XferID (int). New by TransferID (UUID).
                     # For now, assume new system is primary and current_xfers keys are UUIDs.
                     # If SendXfer arrives, it uses an int XferID.
                     # Let's make a specific entry for client_xfer_id if it's different.
                     # This means _on_send_xfer should use this int key.
                     old_sys_transfer_obj_ref = Transfer(
                         id=client_xfer_id, # Store the int XferID here
                         vfile_id_for_callback=actual_vfile_id_for_callback,
                         asset_uuid=vfile_id,
                         asset_type=vfile_type,
                         status=TransferStatus.Queued
                     )
                     self.current_xfers[client_xfer_id] = old_sys_transfer_obj_ref


        await self.client.network.send_packet(req_packet, current_sim)
        logger.info(f"Sent RequestXferPacket for Asset={vfile_id}, Type={vfile_type.name}, VFile CB ID={actual_vfile_id_for_callback}, ClientXferID={client_xfer_id}.")
        return client_xfer_id

    async def request_texture(self, texture_uuid: CustomUUID,
                              image_type: ImageType = ImageType.NORMAL,
                              priority: float = 100.0,
                              item_id_for_callback: CustomUUID | None = None, # Renamed for clarity
                              callback_on_complete: AssetReceivedHandler | None = None) -> bool:
        """
        Requests a texture asset. Primarily tries via "GetTexture" CAPS.
        Falls back to UDP RequestImagePacket if CAPS fails or is unavailable.
        """
        actual_vfile_id_for_callback = item_id_for_callback or texture_uuid
        if callback_on_complete:
            self.register_asset_received_handler(actual_vfile_id_for_callback, callback_on_complete)

        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.connected:
            logger.warning(f"Cannot request texture {texture_uuid}: No connected simulator.")
            self._fire_asset_received(actual_vfile_id_for_callback, False, None, AssetType.Texture, texture_uuid, "No connected simulator")
            return False

        caps_client = current_sim.http_caps_client
        error_msg_from_caps = "CAPS client not available" # Default error if caps_client is None

        if caps_client:
            get_texture_cap_url = caps_client.get_cap_url("GetTexture")
            if get_texture_cap_url:
                request_url = f"{get_texture_cap_url}?texture_id={texture_uuid}"
                logger.debug(f"Requesting texture {texture_uuid} via GetTexture CAP: {request_url}")
                try:
                    success, response_data, status_code = await caps_client.caps_get_bytes(request_url)
                    if success and response_data:
                        logger.info(f"Texture {texture_uuid} received via GetTexture CAP, {len(response_data)} bytes.")
                        self._fire_asset_received(actual_vfile_id_for_callback, True, response_data, AssetType.Texture, texture_uuid)
                        return True
                    else:
                        error_msg_from_caps = f"GetTexture CAP failed with status {status_code}"
                        logger.warning(f"GetTexture CAP request for {texture_uuid} failed. Status: {status_code}. Response: {response_data[:200] if response_data else 'N/A'}")
                except Exception as e:
                    error_msg_from_caps = f"GetTexture CAP exception: {e!r}"
                    logger.exception(f"Exception during GetTexture CAPS request for {texture_uuid}: {e}")
            else: # GetTexture CAP not available
                error_msg_from_caps = "GetTexture CAP not available"
                logger.warning(f"{error_msg_from_caps} for texture {texture_uuid}.")
        # --- Fallback to UDP RequestImage ---
        logger.warning(f"GetTexture CAP failed or not available for {texture_uuid} (Reason: {error_msg_from_caps}). Attempting UDP fallback.")

        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.error("Cannot send RequestImagePacket: AgentID not set for UDP request.")
            self._fire_asset_received(actual_vfile_id_for_callback, False, None, AssetType.Texture, texture_uuid, "AgentID not set for UDP fallback")
            return False

        # Create a Transfer object for UDP tracking, keyed by texture_uuid
        if texture_uuid not in self.current_xfers:
            transfer = Transfer(
                id=texture_uuid, # For image UDP, main ID is texture_uuid
                vfile_id_for_callback=actual_vfile_id_for_callback,
                asset_uuid=texture_uuid,
                asset_type=AssetType.Texture,
                image_type=image_type,
                status=TransferStatus.Queued
            )
            self.current_xfers[texture_uuid] = transfer
        else: # Already an ongoing transfer for this texture_uuid (e.g. retrying)
            transfer = self.current_xfers[texture_uuid]
            transfer.status = TransferStatus.Queued # Reset status for new attempt
            transfer.data.clear()
            transfer.received_bytes = 0
            transfer.udp_packets_expected = 0
            transfer.udp_packets_received.clear()
            transfer.image_type = image_type # Update image type if different

        image_request_block = {
            'Image': texture_uuid,
            'Type': image_type.value,
            'DiscardLevel': 0, # Request highest quality
            'DownloadPriority': priority,
            'Packet': 0, # Start packet number for this image request
            'ExtraInfo': 0 # Server will fill size for J2K in ImageData response
        }
        req_packet = RequestImagePacket(
            self.client.self.agent_id,
            self.client.self.session_id,
            [image_request_block]
        )
        req_packet.header.reliable = False # Image requests are typically unreliable

        asyncio.create_task(self.client.network.send_packet(req_packet, current_sim))
        logger.info(f"Sent RequestImagePacket for texture {texture_uuid} (Type: {image_type.name}) via UDP to {current_sim.name}.")
        # Return False for now, as success is determined by receiving ImageData packets.
        # The callback will be fired when data is complete or ImageNotInDatabase is received.
        # If we want to signal that the request was *sent*, this could return True.
        # However, returning based on actual download is more accurate.
        # For now, the _fire_asset_received in UDP handlers will determine final outcome.
        return True # Indicate request was successfully initiated (sent)

    # --- UDP Image Packet Handlers (Stubs) ---
    def _on_image_not_in_database(self, source_sim: 'Simulator', packet: ImageNotInDatabasePacket):
        texture_uuid = packet.image_id_block.ID # Corrected from image_id to texture_uuid for clarity
        logger.warning(f"Received ImageNotInDatabase for {texture_uuid} from {source_sim.name}.")

        transfer = self.current_xfers.get(texture_uuid)
        if transfer:
            transfer.status = TransferStatus.Error
            self._fire_asset_received(transfer.vfile_id_for_callback, False, None, transfer.asset_type, transfer.asset_uuid, "ImageNotInDatabase")
            if texture_uuid in self.current_xfers: del self.current_xfers[texture_uuid]
        else: # No existing transfer, fire generic failure if possible (though no vfile_id_for_callback here)
            self._fire_asset_received(texture_uuid, False, None, AssetType.Texture, texture_uuid, "ImageNotInDatabase for untracked request")


    def _on_image_data(self, source_sim: 'Simulator', packet: ImageDataPacket):
        texture_uuid = packet.image_id_block.ID # Corrected
        size = packet.image_id_block.Size
        codec = packet.image_id_block.Codec
        data_chunk = packet.image_data_block.Data
        logger.debug(f"Rcvd ImageData for {texture_uuid} from {source_sim.name}. Size: {size}, Codec: {codec}, ChunkLen: {len(data_chunk)}")

        transfer = self.current_xfers.get(texture_uuid)
        if not transfer:
            logger.warning(f"ImageData for unknown or untracked transfer {texture_uuid}. Discarding chunk.")
            return

        if transfer.status == TransferStatus.ERROR: # e.g. previously marked NotInDatabase
            logger.warning(f"ImageData for transfer {texture_uuid} already marked as ERROR. Discarding.")
            return
        if transfer.status == TransferStatus.Done: # Already completed
            logger.warning(f"ImageData for already completed transfer {texture_uuid}. Discarding.")
            return

        if transfer.size == 0 and size > 0: # First packet with size info
            transfer.size = size
            # Assuming 1000 bytes per data chunk for UDP image packets (common, but not fixed)
            # This is a rough estimate and might not match actual packet numbers if server uses different chunking.
            transfer.udp_packets_expected = (size + 999) // 1000
            logger.info(f"UDP Texture {texture_uuid}: Total size set to {size}, expecting approx {transfer.udp_packets_expected} UDP chunks.")

        transfer.data.extend(data_chunk)
        transfer.received_bytes += len(data_chunk)
        transfer.status = TransferStatus.InProgress

        # Packet sequence / chunk tracking for UDP images is complex.
        # ImageDataPacket itself doesn't have a sequence number for the chunk relative to the image.
        # The client might need to track byte offsets or rely on ordered delivery (not guaranteed by UDP).
        # For a robust implementation, RequestImage might need to specify ranges, or a more complex ack system would be used.
        # For now, relying on received_bytes >= size for completion.

        if transfer.size > 0 and transfer.received_bytes >= transfer.size:
            logger.info(f"UDP Texture {texture_uuid} download complete. Received {transfer.received_bytes}/{transfer.size} bytes.")
            completed_transfer = self.current_xfers.pop(texture_uuid, None)
            if completed_transfer: # Should always be true here
                self._fire_asset_received(completed_transfer.vfile_id_for_callback, True, bytes(completed_transfer.data),
                                          completed_transfer.asset_type, completed_transfer.asset_uuid)
        elif transfer.size == 0 and len(data_chunk) == 0 : # Workaround for some servers sending empty last packet for unknown size.
             logger.info(f"UDP Texture {texture_uuid} assumed complete (empty last packet, unknown initial size). Received {transfer.received_bytes} bytes.")
             completed_transfer = self.current_xfers.pop(texture_uuid, None)
             if completed_transfer:
                 self._fire_asset_received(completed_transfer.vfile_id_for_callback, True, bytes(completed_transfer.data),
                                           completed_transfer.asset_type, completed_transfer.asset_uuid)
        else:
            logger.debug(f"ImageData for {texture_uuid}: Got {len(data_chunk)}, total {transfer.received_bytes}/{transfer.size if transfer.size > 0 else 'unknown'}")
