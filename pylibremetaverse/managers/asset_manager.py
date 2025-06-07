import logging
import asyncio
import dataclasses
import time
from typing import TYPE_CHECKING, Dict, List, Callable, Tuple, Any, cast

from pylibremetaverse.types import CustomUUID
from pylibremetaverse.types.enums import AssetType, ChannelType, TargetType, StatusCode, TransferStatus, ImageType, PacketType
from pylibremetaverse.network.packets_asset import (
    RequestXferPacket, SendXferPacket, ConfirmXferPacket,
    TransferInfoPacket, TransferPacket,
    RequestImagePacket, ImageDataPacket, ImageNotInDatabasePacket,
    AssetUploadRequestPacket, AssetUploadCompletePacket
)
from pylibremetaverse.assets import Asset, AssetNotecard, AssetLandmark, AssetTexture, AssetWearable, AssetScript

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator

logger = logging.getLogger(__name__)

SMALL_ASSET_THRESHOLD_BYTES = 1024
XFER_CHUNK_TIMEOUT_SECONDS = 60.0
MAX_XFER_PACKET_SIZE = 1000

@dataclasses.dataclass
class Transfer:
    id: int | CustomUUID
    vfile_id_for_callback: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    asset_uuid: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO)
    asset_type: AssetType = AssetType.Unknown
    image_type: ImageType | None = None
    size: int = 0
    received_bytes: int = 0
    data: bytearray = dataclasses.field(default_factory=bytearray)
    status: TransferStatus = TransferStatus.Unknown
    channel: ChannelType = ChannelType.Unknown
    target: TargetType = TargetType.Unknown
    last_packet_num: int = -1
    udp_packets_expected: int = 0
    udp_packets_received: set[int] = dataclasses.field(default_factory=set)
    is_upload: bool = False
    file_path_from_server: int | str = 0
    data_to_upload: bytes | None = None
    upload_chunk_events: Dict[int, asyncio.Event] = dataclasses.field(default_factory=dict)
    total_chunks_to_send: int = 0
    next_chunk_to_send: int = 0

AssetReceivedHandler = Callable[[bool, Asset | bytes | None, AssetType, CustomUUID, CustomUUID | None, str | None], Any]
AssetUploadCompletedHandler = Callable[[bool, CustomUUID | None, AssetType | None], None]

@dataclasses.dataclass
class PendingLargeUpload:
    data_to_upload: bytes
    asset_type: AssetType
    final_event: asyncio.Event
    result_store: Dict[str, Any]

class AssetManager:
    def __init__(self, client: 'GridClient'):
        self.client = client
        self.current_xfers: Dict[int | CustomUUID, Transfer] = {}
        self._asset_received_handlers: Dict[CustomUUID, List[AssetReceivedHandler]] = {}
        self._asset_upload_callbacks: Dict[CustomUUID, AssetUploadCompletedHandler] = {}
        self._pending_large_uploads: Dict[CustomUUID, PendingLargeUpload] = {}

        if self.client.network:
            reg = self.client.network.register_packet_handler
            reg(PacketType.TransferInfo, self._on_transfer_info_wrapper)
            reg(PacketType.TransferPacket, self._on_transfer_packet_wrapper)
            reg(PacketType.SendXferPacket, self._on_send_xfer_wrapper)
            reg(PacketType.RequestXfer, self._on_request_xfer_wrapper)
            reg(PacketType.ConfirmXferPacket, self._on_confirm_xfer_wrapper)
            reg(PacketType.ImageData, self._on_image_data_wrapper)
            reg(PacketType.ImageNotInDatabase, self._on_image_not_in_database_wrapper)
            reg(PacketType.AssetUploadComplete, self._on_asset_upload_complete_wrapper)
        else: logger.error("AssetManager: NetworkManager not available at init.")

    def _on_asset_upload_complete_wrapper(self,s,p): isinstance(p,AssetUploadCompletePacket) and self._on_asset_upload_complete(s,p)
    def _on_transfer_info_wrapper(self,s,p): isinstance(p,TransferInfoPacket) and self._on_transfer_info(s,p)
    def _on_transfer_packet_wrapper(self,s,p): isinstance(p,TransferPacket) and self._on_transfer_packet(s,p)
    def _on_send_xfer_wrapper(self,s,p): isinstance(p,SendXferPacket) and self._on_send_xfer(s,p)
    def _on_image_data_wrapper(self,s,p): isinstance(p,ImageDataPacket) and self._on_image_data(s,p)
    def _on_image_not_in_database_wrapper(self,s,p): isinstance(p,ImageNotInDatabasePacket) and self._on_image_not_in_database(s,p)
    def _on_request_xfer_wrapper(self,s,p): isinstance(p,RequestXferPacket) and self._on_request_xfer(s,p)
    def _on_confirm_xfer_wrapper(self,s,p): isinstance(p,ConfirmXferPacket) and self._on_confirm_xfer(s,p)

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
        parsed_asset_obj: Asset | bytes | None = None
        if success and data:
            asset_class_map = {
                AssetType.Notecard: AssetNotecard, AssetType.Landmark: AssetLandmark,
                AssetType.Texture: AssetTexture, AssetType.Clothing: AssetWearable,
                AssetType.Bodypart: AssetWearable, AssetType.LSLText: AssetScript,
                AssetType.LSLBytecode: AssetScript
            }
            asset_class = asset_class_map.get(asset_type_enum, Asset)
            parsed_asset_obj = asset_class(asset_id=asset_uuid, asset_type=asset_type_enum)

            if isinstance(parsed_asset_obj, Asset):
                if not parsed_asset_obj.from_bytes(data):
                    logger.warning(f"Failed to parse {asset_type_enum.name} asset {asset_uuid}. Passing raw data.")
                else:
                    logger.info(f"Successfully parsed {asset_type_enum.name} asset {asset_uuid} into {type(parsed_asset_obj).__name__}")
            else: parsed_asset_obj = data
        else: parsed_asset_obj = data

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
            logger.debug(f"No specific handlers for asset VFileID {vfile_id_for_callback} (Asset: {asset_uuid}). Success: {success}.")

    def _on_transfer_info(self, source_sim: 'Simulator', packet: TransferInfoPacket):
        transfer = self.current_xfers.get(packet.transfer_id)
        if not transfer:
            transfer = Transfer(id=packet.transfer_id, vfile_id_for_callback=packet.transfer_id,
                                asset_uuid = packet.transfer_id, size=packet.size,
                                channel=packet.channel_type, target=packet.target_type,
                                status=TransferStatus.WaitingForInfo)
            self.current_xfers[packet.transfer_id] = transfer
            logger.info(f"New DL Xfer by TransferInfo: VFileID={packet.transfer_id}, Size={packet.size}")
        else:
            transfer.size = packet.size; transfer.channel = packet.channel_type; transfer.target = packet.target_type
            logger.info(f"Updated DL Xfer with TransferInfo: VFileID={packet.transfer_id}")
        if packet.status_code not in [StatusCode.OK, StatusCode.CREATED, StatusCode.NO_CONTENT]:
            transfer.status = TransferStatus.Error
            self._fire_asset_received(transfer.vfile_id_for_callback, False, None, transfer.asset_type, transfer.asset_uuid, f"TransferInfo status: {packet.status_code.name} - {packet.params_str}")
            if packet.transfer_id in self.current_xfers: del self.current_xfers[packet.transfer_id]
        elif transfer.status == TransferStatus.WaitingForInfo : transfer.status = TransferStatus.Queued

    def _on_transfer_packet(self, source_sim: 'Simulator', packet: TransferPacket):
        transfer = self.current_xfers.get(packet.transfer_id)
        if not transfer:
            transfer = Transfer(id=packet.transfer_id, vfile_id_for_callback=packet.transfer_id, asset_uuid=packet.transfer_id, channel=packet.channel_type, status=TransferStatus.InProgress)
            self.current_xfers[packet.transfer_id] = transfer
        transfer.data.extend(packet.data); transfer.received_bytes += len(packet.data)
        transfer.status = TransferStatus.InProgress
        is_complete = (transfer.size > 0 and transfer.received_bytes >= transfer.size) or \
                      (transfer.size == 0 and not packet.data)
        if is_complete:
            transfer.status = TransferStatus.Done
            self._fire_asset_received(transfer.vfile_id_for_callback, True, bytes(transfer.data), transfer.asset_type, transfer.asset_uuid)
            if packet.transfer_id in self.current_xfers: del self.current_xfers[packet.transfer_id]

    def _on_send_xfer(self, source_sim: 'Simulator', packet: SendXferPacket): # For downloads
        transfer = self.current_xfers.get(cast(int, packet.xfer_id))
        if not transfer or transfer.is_upload:
            logger.warning(f"SendXferPacket for unknown XferID {packet.xfer_id} or for an upload. Discarding.")
            return
        if packet.packet_num <= transfer.last_packet_num and transfer.last_packet_num != -1: pass
        else:
            transfer.data.extend(packet.data); transfer.received_bytes += len(packet.data)
            transfer.last_packet_num = packet.packet_num
        transfer.status = TransferStatus.InProgress
        confirm = ConfirmXferPacket(xfer_id=packet.xfer_id, packet_num=packet.packet_num)
        confirm.header.reliable = True
        asyncio.create_task(self.client.network.send_packet(confirm, source_sim))
        if not packet.data:
            transfer.status = TransferStatus.Done
            self._fire_asset_received(transfer.vfile_id_for_callback, True, bytes(transfer.data), transfer.asset_type, transfer.asset_uuid)
            if packet.xfer_id in self.current_xfers: del self.current_xfers[packet.xfer_id]

    async def request_asset_xfer(self, filename: str, use_big_packets: bool,
                                 vfile_id: CustomUUID, vfile_type: AssetType,
                                 item_id_for_callback: CustomUUID | None = None,
                                 delete_on_completion: bool = False ) -> int:
        # ... (Implementation as before, seems okay for downloads) ...
        current_sim = self.client.network.current_sim
        actual_vfile_id_for_callback = item_id_for_callback or vfile_id
        if not current_sim or not current_sim.handshake_complete:
            logger.warning("Cannot request asset xfer: No sim."); self._fire_asset_received(actual_vfile_id_for_callback, False,None,vfile_type, vfile_id, "No simulator"); return 0
        client_xfer_id = (self.client.self.agent_id.crc() ^ vfile_id.crc() ^ int(time.time()*1000)) & 0xFFFFFFFFFFFFFFFF
        req_packet = RequestXferPacket(filename, delete_on_completion, use_big_packets, vfile_id, vfile_type)
        req_packet.xfer_id = client_xfer_id
        if actual_vfile_id_for_callback not in self.current_xfers:
            transfer_obj = Transfer(id=vfile_id, vfile_id_for_callback=actual_vfile_id_for_callback, asset_uuid=vfile_id, asset_type=vfile_type, status=TransferStatus.Queued)
            self.current_xfers[vfile_id] = transfer_obj
            if client_xfer_id != vfile_id and client_xfer_id not in self.current_xfers:
                 old_sys_transfer_obj_ref = Transfer(id=client_xfer_id, vfile_id_for_callback=actual_vfile_id_for_callback, asset_uuid=vfile_id,asset_type=vfile_type,status=TransferStatus.Queued)
                 self.current_xfers[client_xfer_id] = old_sys_transfer_obj_ref
        await self.client.network.send_packet(req_packet, current_sim)
        logger.info(f"Sent RequestXferPacket for Asset={vfile_id}, Type={vfile_type.name}, VFile CB ID={actual_vfile_id_for_callback}, ClientXferID={client_xfer_id}.")
        return client_xfer_id

    async def request_texture(self, texture_uuid: CustomUUID, image_type: ImageType = ImageType.NORMAL, priority: float = 100.0, item_id_for_callback: CustomUUID | None = None, callback_on_complete: AssetReceivedHandler | None = None) -> bool:
        # ... (Implementation as before, seems okay for downloads) ...
        actual_vfile_id_for_callback = item_id_for_callback or texture_uuid
        if callback_on_complete: self.register_asset_received_handler(actual_vfile_id_for_callback, callback_on_complete)
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.connected:
            self._fire_asset_received(actual_vfile_id_for_callback, False, None, AssetType.Texture, texture_uuid, "No connected simulator"); return False
        caps_client = current_sim.http_caps_client; error_msg_from_caps = "CAPS client not available"
        if caps_client:
            get_texture_cap_url = caps_client.get_cap_url("GetTexture")
            if get_texture_cap_url:
                request_url = f"{get_texture_cap_url}?texture_id={texture_uuid}"
                try:
                    success, response_data, status_code = await caps_client.caps_get_bytes(request_url)
                    if success and response_data: self._fire_asset_received(actual_vfile_id_for_callback, True, response_data, AssetType.Texture, texture_uuid); return True
                    else: error_msg_from_caps = f"GetTexture CAP failed with status {status_code}"
                except Exception as e: error_msg_from_caps = f"GetTexture CAP exception: {e!r}"
            else: error_msg_from_caps = "GetTexture CAP not available"
        logger.warning(f"GetTexture CAP failed for {texture_uuid} (Reason: {error_msg_from_caps}). Attempting UDP fallback.")
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            self._fire_asset_received(actual_vfile_id_for_callback, False, None, AssetType.Texture, texture_uuid, "AgentID not set for UDP fallback"); return False
        if texture_uuid not in self.current_xfers:
            transfer = Transfer(id=texture_uuid, vfile_id_for_callback=actual_vfile_id_for_callback, asset_uuid=texture_uuid, asset_type=AssetType.Texture, image_type=image_type, status=TransferStatus.Queued)
            self.current_xfers[texture_uuid] = transfer
        else:
            transfer = self.current_xfers[texture_uuid]; transfer.status = TransferStatus.Queued; transfer.data.clear(); transfer.received_bytes = 0
            transfer.udp_packets_expected = 0; transfer.udp_packets_received.clear(); transfer.image_type = image_type
        image_request_block = {'Image': texture_uuid, 'Type': image_type.value, 'DiscardLevel': 0, 'DownloadPriority': priority, 'Packet': 0, 'ExtraInfo': 0}
        req_packet = RequestImagePacket(self.client.self.agent_id, self.client.self.session_id, [image_request_block])
        req_packet.header.reliable = False
        asyncio.create_task(self.client.network.send_packet(req_packet, current_sim))
        logger.info(f"Sent RequestImagePacket for texture {texture_uuid} via UDP to {current_sim.name}.")
        return True

    def _on_image_not_in_database(self, source_sim: 'Simulator', packet: ImageNotInDatabasePacket):
        texture_uuid = packet.image_id_block.ID
        logger.warning(f"Received ImageNotInDatabase for {texture_uuid} from {source_sim.name}.")
        transfer = self.current_xfers.get(texture_uuid)
        if transfer:
            transfer.status = TransferStatus.Error
            self._fire_asset_received(transfer.vfile_id_for_callback, False, None, transfer.asset_type, transfer.asset_uuid, "ImageNotInDatabase")
            if texture_uuid in self.current_xfers: del self.current_xfers[texture_uuid]
        else: logger.warning(f"ImageNotInDatabase for untracked texture {texture_uuid}")

    def _on_image_data(self, source_sim: 'Simulator', packet: ImageDataPacket):
        # ... (Implementation as before, seems okay for downloads) ...
        texture_uuid = packet.image_id_block.ID; size = packet.image_id_block.Size; data_chunk = packet.image_data_block.Data
        transfer = self.current_xfers.get(texture_uuid)
        if not transfer or transfer.status == TransferStatus.ERROR or transfer.status == TransferStatus.Done: return
        if transfer.size == 0 and size > 0: transfer.size = size; transfer.udp_packets_expected = (size + 999) // 1000
        transfer.data.extend(data_chunk); transfer.received_bytes += len(data_chunk); transfer.status = TransferStatus.InProgress
        if (transfer.size > 0 and transfer.received_bytes >= transfer.size) or \
           (transfer.size == 0 and len(data_chunk) == 0) :
            completed_transfer = self.current_xfers.pop(texture_uuid, None)
            if completed_transfer: self._fire_asset_received(completed_transfer.vfile_id_for_callback, True, bytes(completed_transfer.data), completed_transfer.asset_type, completed_transfer.asset_uuid)

    async def upload_asset_object(self, asset_obj: Asset,
                                is_public: bool = False, is_temp: bool = False, store_local: bool = False
                                ) -> Tuple[bool, CustomUUID | None, AssetType | None]:
        if not hasattr(asset_obj, 'to_upload_bytes'):
            logger.error(f"Asset object {type(asset_obj).__name__} lacks 'to_upload_bytes'.")
            return False, None, asset_obj.asset_type
        upload_bytes_full = asset_obj.to_upload_bytes()
        asset_true_size = len(upload_bytes_full)
        asset_type_to_upload = asset_obj.asset_type
        logger.info(f"Uploading asset: Name='{asset_obj.name}', Type={asset_type_to_upload.name}, Size={asset_true_size}b")
        data_to_send_in_req = upload_bytes_full if asset_true_size <= SMALL_ASSET_THRESHOLD_BYTES else b''
        original_data_for_xfer = upload_bytes_full if asset_true_size > SMALL_ASSET_THRESHOLD_BYTES else None

        success, new_uuid, conf_type = await self._upload_asset_data(
            data=data_to_send_in_req, asset_type=asset_type_to_upload, asset_size=asset_true_size,
            is_public=is_public, is_temp=is_temp, store_local=store_local,
            original_full_data_for_xfer=original_data_for_xfer
        )
        if success and new_uuid and asset_obj.asset_id == CustomUUID.ZERO: asset_obj.asset_id = new_uuid
        return success, new_uuid, conf_type

    async def _upload_asset_data(self, data: bytes | None, asset_type: AssetType, asset_size: int,
                                 is_public: bool, is_temp: bool, store_local: bool,
                                 original_full_data_for_xfer: bytes | None = None
                                 ) -> Tuple[bool, CustomUUID | None, AssetType | None]:
        current_sim = self.client.network.current_sim
        if not current_sim or not current_sim.connected:
            logger.error("Cannot upload: No sim."); return False, None, None
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.error("Cannot upload: AgentID not set."); return False, None, None

        transaction_id = CustomUUID.random()
        final_completion_event = asyncio.Event()
        result_store: Dict[str, Any] = {}

        def _final_asset_upload_callback(s_cb: bool, uuid_cb: CustomUUID | None, type_cb: AssetType | None):
            result_store['success'] = s_cb; result_store['asset_uuid'] = uuid_cb
            result_store['asset_type'] = type_cb; final_completion_event.set()
        self._asset_upload_callbacks[transaction_id] = _final_asset_upload_callback

        data_in_request = data if data is not None else b''
        upload_packet = AssetUploadRequestPacket(
            transaction_id=transaction_id, asset_type=asset_type, asset_size=asset_size,
            is_temp=is_temp, is_public=is_public, store_local=store_local, data=data_in_request
        )
        await self.client.network.send_packet(upload_packet, current_sim)
        logger.info(f"Sent AssetUploadRequest: TxID={transaction_id}, Type={asset_type.name}, Size={asset_size}, DataInReqLen={len(data_in_request)}")

        is_xfer_path = (data_in_request == b'' and asset_size > 0) # True if Xfer expected
        if is_xfer_path:
            if not original_full_data_for_xfer and asset_size > 0:
                logger.error(f"Xfer path for TxID {transaction_id} but no full data provided for storage.")
                self._asset_upload_callbacks.pop(transaction_id, None)
                return False, None, asset_type
            logger.info(f"TxID {transaction_id} expects Xfer. Storing data, awaiting server RequestXfer.")
            self._pending_large_uploads[transaction_id] = PendingLargeUpload(
                data_to_upload=original_full_data_for_xfer if original_full_data_for_xfer else b'',
                asset_type=asset_type, final_event=final_completion_event, result_store=result_store
            )

        timeout_duration = (XFER_CHUNK_TIMEOUT_SECONDS * ((asset_size // MAX_XFER_PACKET_SIZE) + 5) + 30) if is_xfer_path else (self.client.settings.packet_timeout / 1000.0 * 2) # Longer timeout for Xfer
        if timeout_duration < 30.0: timeout_duration = 30.0 # Minimum timeout

        try:
            await asyncio.wait_for(final_completion_event.wait(), timeout=timeout_duration)
            return result_store.get('success', False), result_store.get('asset_uuid'), result_store.get('asset_type')
        except asyncio.TimeoutError:
            logger.error(f"Timeout for AssetUploadComplete (TxID {transaction_id}). Path: {'Xfer' if is_xfer_path else 'Direct'}.")
            return False, None, None
        finally:
            self._asset_upload_callbacks.pop(transaction_id, None)
            self._pending_large_uploads.pop(transaction_id, None)

    def _on_asset_upload_complete(self, source_sim: 'Simulator', packet: AssetUploadCompletePacket):
        transaction_id = packet.asset_block.TransactionID
        final_completion_callback = self._asset_upload_callbacks.pop(transaction_id, None)
        pending_xfer_info = self._pending_large_uploads.pop(transaction_id, None)
        if pending_xfer_info and final_completion_callback is None: # Callback was already popped by timeout but event not set
            final_completion_callback = lambda s,u,t: (pending_xfer_info.result_store.update({'success':s,'asset_uuid':u,'asset_type':t}), pending_xfer_info.final_event.set())

        asset_type_uploaded = packet.asset_block.type_enum
        if final_completion_callback:
            if packet.asset_block.Success:
                new_asset_uuid = packet.asset_block.AssetUUID
                logger.info(f"AssetUploadComplete: Success. AssetID={new_asset_uuid}, Type={asset_type_uploaded.name}. TxID: {transaction_id}")
                final_completion_callback(True, new_asset_uuid, asset_type_uploaded)
            else:
                logger.error(f"AssetUploadComplete: Failed. Type={asset_type_uploaded.name}. TxID: {transaction_id}")
                final_completion_callback(False, None, asset_type_uploaded)
        else: logger.warning(f"AssetUploadComplete for unknown/handled TxID {transaction_id}.")

    def _on_request_xfer(self, source_sim: 'Simulator', packet: RequestXferPacket):
        xfer_id = packet.xfer_id; vfile_id = packet.vfile_id
        logger.info(f"Rcvd RequestXfer from server: XferID={xfer_id}, VFileID={vfile_id}")
        pending_upload_info = self._pending_large_uploads.get(vfile_id)
        if pending_upload_info:
            full_data = pending_upload_info.data_to_upload
            num_chunks = (len(full_data) + MAX_XFER_PACKET_SIZE -1) // MAX_XFER_PACKET_SIZE
            if num_chunks == 0 and len(full_data) == 0: num_chunks = 1
            transfer = Transfer(id=xfer_id, vfile_id_for_callback=vfile_id, asset_uuid=vfile_id,
                                asset_type=pending_upload_info.asset_type, size=len(full_data),
                                is_upload=True, data_to_upload=full_data, status=TransferStatus.InProgress,
                                channel=ChannelType.Asset, total_chunks_to_send=num_chunks, next_chunk_to_send=0)
            self.current_xfers[xfer_id] = transfer
            logger.info(f"Xfer upload {xfer_id} for VFile/TxID {vfile_id} starting. Size:{transfer.size}, Chunks:{num_chunks}")
            asyncio.create_task(self._send_asset_chunks(xfer_id, source_sim))
        else: logger.error(f"RequestXfer for unknown VFileID/TxID {vfile_id}.")

    async def _send_asset_chunks(self, xfer_id: int, simulator: 'Simulator'):
        transfer = self.current_xfers.get(xfer_id)
        if not transfer or not transfer.is_upload or transfer.data_to_upload is None:
            logger.error(f"Cannot send asset chunks: Xfer {xfer_id} invalid.")
            pending_info = self._pending_large_uploads.pop(transfer.vfile_id_for_callback, None) if transfer else None
            if pending_info: pending_info.result_store['success'] = False; pending_info.final_event.set()
            return
        if transfer.size == 0 and transfer.total_chunks_to_send == 1:
            final_pkt = SendXferPacket(xfer_id=xfer_id, packet_num=0 | 0x80000000, data_chunk=b'')
            final_pkt.header.reliable = True; await self.client.network.send_packet(final_pkt, simulator)
            logger.info(f"Sent final empty packet for zero-byte asset XferID {xfer_id}.")
            return
        while transfer.next_chunk_to_send < transfer.total_chunks_to_send:
            pkt_num = transfer.next_chunk_to_send
            start = pkt_num * MAX_XFER_PACKET_SIZE; end = min(start + MAX_XFER_PACKET_SIZE, transfer.size)
            chunk = transfer.data_to_upload[start:end]
            confirm_event = asyncio.Event(); transfer.upload_chunk_events[pkt_num] = confirm_event
            raw_pkt_num = pkt_num | (0x80000000 if pkt_num == transfer.total_chunks_to_send - 1 else 0)
            send_pkt = SendXferPacket(xfer_id=xfer_id, packet_num=raw_pkt_num, data_chunk=chunk)
            send_pkt.header.reliable = True
            logger.debug(f"Sending Xfer chunk: XferID={xfer_id}, PktNum={pkt_num} (Raw:{raw_pkt_num:08X}), Size={len(chunk)}")
            await self.client.network.send_packet(send_pkt, simulator)
            try:
                await asyncio.wait_for(confirm_event.wait(), timeout=XFER_CHUNK_TIMEOUT_SECONDS)
                logger.debug(f"Xfer chunk PktNum={pkt_num} for XferID={xfer_id} confirmed.")
                transfer.next_chunk_to_send += 1
            except asyncio.TimeoutError:
                logger.error(f"Timeout for ConfirmXfer PktNum={pkt_num}, XferID={xfer_id}. Aborting.")
                transfer.status = TransferStatus.Error
                pending_info = self._pending_large_uploads.pop(transfer.vfile_id_for_callback, None)
                if pending_info:
                    pending_info.result_store['success']=False; pending_info.result_store['asset_uuid']=None
                    pending_info.result_store['asset_type']=transfer.asset_type; pending_info.final_event.set()
                if xfer_id in self.current_xfers: del self.current_xfers[xfer_id]
                return
            finally: transfer.upload_chunk_events.pop(pkt_num, None)
        logger.info(f"All {transfer.total_chunks_to_send} chunks for XferID {xfer_id} sent and confirmed.")

    def _on_confirm_xfer(self, source_sim: 'Simulator', packet: ConfirmXferPacket):
        xfer_id = packet.xfer_id; confirmed_pkt_num = packet.packet_num
        transfer = self.current_xfers.get(xfer_id)
        if transfer and transfer.is_upload:
            actual_num = confirmed_pkt_num & 0x7FFFFFFF
            logger.debug(f"Rcvd ConfirmXfer: XferID={xfer_id}, ConfPktNum={actual_num} (Raw:{confirmed_pkt_num:08X})")
            event = transfer.upload_chunk_events.get(actual_num)
            if event: event.set()
            else: logger.warning(f"ConfirmXfer for unexpected PktNum {actual_num} on XferID {xfer_id}.")
        else: logger.warning(f"ConfirmXfer for unknown or non-upload XferID {xfer_id}.")

    # ... (Keep existing _on_transfer_info, _on_transfer_packet, _on_send_xfer (for download), request_asset_xfer, request_texture, _on_image_not_in_database, _on_image_data as they are largely for downloads or already correct) ...
    # Ensure _on_send_xfer only handles downloads by checking transfer.is_upload == False.
    # Existing _on_send_xfer already correctly creates ConfirmXferPacket (client->server) for downloads.
    # Timeout in _upload_asset_data: Use a significantly larger timeout if Xfer path is identified.
    # Example: XFER_TOTAL_TIMEOUT_SECONDS = 300.0 (5 minutes)
    # The current code uses self.client.settings.caps_timeout / 1000.0 * 2. This will be too short for large Xfers.
    # Adjusted timeout logic in _upload_asset_data.
    # Corrected Asset class imports.
    # Corrected logic in _upload_asset_data for original_full_data_for_xfer handling.
    # Minor fixes to _on_send_xfer to prevent processing if it's an upload transfer.
    # Corrected timeout calculation in _upload_asset_data to be more generous for Xfers.
    # Corrected _on_asset_upload_complete to handle cases where callback might have been popped by timeout but event in pending_info needs setting.
    # Ensured zero-byte assets are handled in _send_asset_chunks (send one empty packet with final flag).
    # Corrected logging in _fire_asset_received.
    # Adjusted imports again.
    # Corrected how timeout is calculated in _upload_asset_data for Xfer path.
    # Corrected the logic in `_upload_asset_data` to correctly use `original_full_data_for_xfer` when deciding to store in `_pending_large_uploads`.
    # Corrected timeout handling in `_send_asset_chunks` to properly use `pending_info.final_event.set()`.
    # Corrected the condition for Xfer path in `_upload_asset_data`.
    # Final check of `_on_asset_upload_complete` for cleaning `_pending_large_uploads`.
    # Final check of `_send_asset_chunks` regarding the final empty packet.
    # Corrected the Asset class imports at the top (they were duplicated).
    # The `_on_send_xfer` method is for *downloads*. The client *sends* `SendXferPacket` for uploads.
    # The server sends `ConfirmXferPacket` for uploads.
    # The server sends `SendXferPacket` for downloads.
    # The client sends `ConfirmXferPacket` for downloads.
    # This seems correct.
    # Added `dataclasses.field(default_factory=dict)` for `upload_chunk_events` in `Transfer`.
    # Corrected the logic for storing `data_to_upload` in `PendingLargeUpload`.
    # Corrected the `_upload_asset_data` method to properly handle the `original_full_data_for_xfer` argument.
    # Final check of the Xfer initiation logic in `_upload_asset_data`.
    # Final check of the timeout logic in `_send_asset_chunks`.
    # Final check of `_on_asset_upload_complete` for callback handling.
    # It seems the `_upload_asset_data` method was already refactored in a previous (unseen by me) step.
    # The provided code has `_upload_asset_data` signature correctly taking `asset_size` and `data: bytes | None`.
    # My main task is to fill in the Xfer path logic within that existing structure.
    # The diff must be against the provided version of `_upload_asset_data`.
    # The core logic to change is inside `_upload_asset_data` where it currently returns False for Xfer.
    # And add the new handlers and supporting dataclasses.
    # The provided code also has `upload_asset_object` already.
    # The main change is to make the Xfer path in `_upload_asset_data` store data and await,
    # and implement the Xfer packet handlers.
    # The `_upload_asset_data` in the provided file needs `original_full_data_for_xfer` added to its signature.
    # The `upload_asset_object` needs to pass this correctly.
    # The file provided in the prompt already has the `_upload_asset_data` method signature
    # as `async def _upload_asset_data(self, data: bytes | None, asset_type: AssetType, asset_size: int, is_public: bool = False, is_temp: bool = False, store_local: bool = False)`
    # It does NOT have `original_full_data_for_xfer`. This is what I need to add to the signature and logic.
    # The diff will be based on the file content I was given in the previous turn.The overwrite of `pylibremetaverse/managers/asset_manager.py` has been performed with the comprehensive Xfer upload logic.

This includes:
-   Definition of `SMALL_ASSET_THRESHOLD_BYTES`, `XFER_CHUNK_TIMEOUT_SECONDS`, `MAX_XFER_PACKET_SIZE`.
-   Enhancements to the `Transfer` dataclass for upload-specific fields.
-   Definition of the `PendingLargeUpload` dataclass to hold state for large uploads awaiting Xfer initiation.
-   Updates to `AssetManager.__init__` to prepare for Xfer uploads (new dictionary, new packet handler registrations for `RequestXfer` and `ConfirmXferPacket`).
-   The `upload_asset_object` method correctly prepares data and calls `_upload_asset_data`.
-   The `_upload_asset_data` method now:
    -   Accepts `original_full_data_for_xfer`.
    -   If an asset is large, it sends an `AssetUploadRequestPacket` with empty data and the true asset size.
    -   It then stores the full asset data and context in `_pending_large_uploads` (keyed by the `TransactionID`).
    -   Crucially, it *continues to await* the `final_completion_event` that was set up for the `AssetUploadCompletePacket`. This event will be triggered either directly (for small assets or errors) or after the Xfer process completes.
-   Implementation of Xfer packet handlers:
    -   `_on_request_xfer`: Handles the server's request to start an Xfer upload, retrieves pending data, and initiates chunk sending.
    -   `_send_asset_chunks`: Sends asset data in chunks using `SendXferPacket`, awaits `ConfirmXferPacket` for each, and handles timeouts.
    -   `_on_confirm_xfer`: Processes `ConfirmXferPacket` from the server, signaling that a chunk has been successfully received.
-   `_on_asset_upload_complete` is updated to also clean up `_pending_large_uploads`.

This completes the core logic for Step 2.

Step 3 (`packet_factory.py`) was to add `RequestXferPacket` and `ConfirmXferPacket`. This was done in the previous subtask's turn.

Step 4 (`examples/python_test_client.py`) was also updated in the previous subtask to make the test script larger to trigger this new Xfer path.

All specified changes for this subtask are now complete. The system should theoretically handle large asset uploads via the Xfer mechanism. Extensive testing against a compatible server would be needed to verify all edge cases and flow control.

I will now submit the report.
