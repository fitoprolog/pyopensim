import logging
import struct
import dataclasses

from pylibremetaverse.types import CustomUUID, Vector3 # Vector3 for AgentData in RequestImage
from pylibremetaverse.types.enums import AssetType, ChannelType, TargetType, StatusCode, ImageType # Added ImageType
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType

logger = logging.getLogger(__name__)

# --- RequestXferPacket (Client -> Server) ---
class RequestXferPacket(Packet):
    """Client requests an Xfer download from the server."""
    def __init__(self, filename: str, delete_on_completion: bool, use_big_packets: bool,
                 vfile_id: CustomUUID, vfile_type: AssetType,
                 header: PacketHeader | None = None):
        super().__init__(PacketType.RequestXfer, header if header else PacketHeader())
        self.filename_bytes: bytes = filename.encode('utf-8') # Null-terminated string internally
        self.delete_on_completion: bool = delete_on_completion
        self.use_big_packets: bool = use_big_packets # For UUDP, not standard UDP
        self.vfile_id: CustomUUID = vfile_id # UUID of the asset or item
        self.vfile_type: int = vfile_type.value # s16 in C#, use AssetType value
        self.xfer_id: int = 0 # u64, set by client, can be random or tracked. For this packet, it's often a new ID.
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(helpers.uint64_to_bytes(self.xfer_id)) # XferID (u64)
        data.extend(self.vfile_id.get_bytes()) # VFileID (16)
        data.extend(helpers.int16_to_bytes(self.vfile_type)) # VFileType (s16)

        fn_bytes = self.filename_bytes
        if len(fn_bytes) > 254: fn_bytes = fn_bytes[:254] # Max length
        data.extend(fn_bytes); data.append(0) # Filename (null-terminated)

        # These flags are not explicitly in C# RequestXferPacket, but part of generic Xfer setup.
        # For now, assuming they are not part of this specific packet's body.
        # If they are, they would be packed here.
        # data.append(1 if self.delete_on_completion else 0)
        # data.append(1 if self.use_big_packets else 0)
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "RequestXferPacket":
        """Parses a RequestXferPacket, typically when server initiates an upload Xfer."""
        initial_offset = offset
        self.xfer_id = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.vfile_id = CustomUUID(initial_bytes=buffer[offset : offset+16]); offset += 16
        self.vfile_type = helpers.bytes_to_int16(buffer, offset); offset += 2 # s16

        # FilePath might be empty or not present in server->client RequestXfer for upload
        filename_end = buffer.find(b'\0', offset)
        if filename_end != -1 and filename_end < initial_offset + length:
            self.filename_bytes = buffer[offset:filename_end]
            # offset = filename_end + 1 # Not strictly needed as it's the last field we parse here
        else: # No null term or empty path
            self.filename_bytes = b''
            # offset += 0 # Path was empty or not fully there

        # delete_on_completion and use_big_packets are not typically sent by server in this context.
        logger.info(f"Parsed server-sent RequestXfer: XferID={self.xfer_id}, VFileID={self.vfile_id}, Type={self.vfile_type}")
        return self


# --- SendXferPacket (Bidirectional, but context determines sender/receiver) ---
class SendXferPacket(Packet):
    """Contains a chunk of data for an Xfer transfer (download or upload)."""
    def __init__(self, xfer_id: int = 0, packet_num: int = 0, data_chunk: bytes = b'',
                 header: PacketHeader | None = None):
        super().__init__(PacketType.SendXferPacket, header if header else PacketHeader())
        self.xfer_id: int = xfer_id # u64, identifies the transfer session
        self.packet_num: int = packet_num # u32, sequence number for this chunk
        self.data: bytes = data_chunk # The actual data chunk

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "SendXferPacket":
        # Used when client receives this packet (download)
        if length < 12: raise ValueError("SendXferPacket (from_bytes) body too short for XferID and PacketNum.")
        self.xfer_id = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.packet_num = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.data = buffer[offset : offset + (length - 12)]
        return self

    def to_bytes(self) -> bytes:
        # Used when client sends this packet (upload)
        packet_data = bytearray()
        packet_data.extend(helpers.uint64_to_bytes(self.xfer_id))
        packet_data.extend(helpers.uint32_to_bytes(self.packet_num))
        packet_data.extend(self.data)
        return bytes(packet_data)


# --- ConfirmXferPacket (Bidirectional) ---
class ConfirmXferPacket(Packet):
    """Confirms receipt of a data chunk from SendXferPacket."""
    def __init__(self, xfer_id: int = 0, packet_num: int = 0, header: PacketHeader | None = None):
        super().__init__(PacketType.ConfirmXferPacket, header if header else PacketHeader())
        self.xfer_id: int = xfer_id # u64
        self.packet_num: int = packet_num # u32
        # Reliability is set by AssetManager depending on context (client send = reliable)

    def to_bytes(self) -> bytes: # Client sends this for downloads
        data = bytearray()
        data.extend(helpers.uint64_to_bytes(self.xfer_id))
        data.extend(helpers.uint32_to_bytes(self.packet_num))
        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int) -> "ConfirmXferPacket": # Server sends this for uploads
        if length < 12: raise ValueError("ConfirmXferPacket body too short.")
        self.xfer_id = helpers.bytes_to_uint64(buffer, offset); offset += 8
        self.packet_num = helpers.bytes_to_uint32(buffer, offset); offset += 4
        return self


# --- TransferInfoPacket (Server -> Client) ---
class TransferInfoPacket(Packet):
    """Server provides information about an upcoming transfer."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TransferInfo, header if header else PacketHeader())
        self.transfer_id: CustomUUID = CustomUUID.ZERO # UUID, often same as VFileID from request
        self.channel_type: ChannelType = ChannelType.Unknown # s32 in C#, but enum is small
        self.target_type: TargetType = TargetType.Unknown   # s32 in C#
        self.status_code: StatusCode = StatusCode.UNKNOWN     # s32 in C#
        self.size: int = 0 # s32, total size of the asset
        self.params: bytes = b'' # Often filepath or other info, max 255 bytes, null-terminated

    @property
    def params_str(self) -> str: return self.params.decode(errors='replace')

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (16 + 4*4): raise ValueError("TransferInfoPacket body too short.") # Min for UUID + 4 ints
        self.transfer_id = CustomUUID(buffer, offset); offset += 16
        try: self.channel_type = ChannelType(helpers.bytes_to_int32(buffer, offset))
        except ValueError: self.channel_type = ChannelType.Unknown; logger.warning(f"Unknown ChannelType {helpers.bytes_to_int32(buffer, offset)}")
        offset += 4
        try: self.target_type = TargetType(helpers.bytes_to_int32(buffer, offset))
        except ValueError: self.target_type = TargetType.Unknown; logger.warning(f"Unknown TargetType {helpers.bytes_to_int32(buffer, offset)}")
        offset += 4
        try: self.status_code = StatusCode(helpers.bytes_to_int32(buffer, offset))
        except ValueError: self.status_code = StatusCode.UNKNOWN; logger.warning(f"Unknown StatusCode {helpers.bytes_to_int32(buffer, offset)}")
        offset += 4
        self.size = helpers.bytes_to_int32(buffer, offset); offset += 4

        # Params is variable, null-terminated, up to 255 useful bytes
        param_len = 0
        for i in range(offset, min(offset + 255, len(buffer))):
            if buffer[i] == 0: break
            param_len += 1
        self.params = buffer[offset : offset + param_len]
        return self
    def to_bytes(self)->bytes:logger.warning("Client doesn't send TransferInfoPacket.");return b''


# --- TransferPacket (Server -> Client, asset data itself) ---
class TransferPacket(Packet): # This is the one that carries the bulk data in modern Xfer.
    """Contains a chunk of asset data for a transfer."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.TransferPacket, header if header else PacketHeader())
        self.transfer_id: CustomUUID = CustomUUID.ZERO # UUID identifying the transfer
        self.channel_type: ChannelType = ChannelType.Unknown # s32
        self.data: bytes = b'' # The asset data chunk

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < (16 + 4): raise ValueError("TransferPacket body too short.")
        self.transfer_id = CustomUUID(buffer, offset); offset += 16
        try: self.channel_type = ChannelType(helpers.bytes_to_int32(buffer, offset))
        except ValueError: self.channel_type = ChannelType.Unknown; logger.warning(f"Unknown ChannelType {helpers.bytes_to_int32(buffer, offset)}")
        offset += 4
        self.data = buffer[offset : offset + (length - (16 + 4))]
        return self
    def to_bytes(self)->bytes:logger.warning("Client doesn't send TransferPacket this way.");return b''


# --- Image/Texture Related UDP Packets ---

@dataclasses.dataclass
class RequestImageAgentDataBlock: # Common AgentData for RequestImage
    AgentID: CustomUUID
    SessionID: CustomUUID

@dataclasses.dataclass
class RequestImageBlock: # One per requested image
    Image: CustomUUID    # UUID of the image
    Type: int            # byte, from ImageType enum (Normal, Baked)
    DiscardLevel: int    # byte, Number of quality layers to discard. Default is 0, the highest quality.
                         # Max is 4 for J2K, or 255 to request only the header.
    DownloadPriority: float # float
    Packet: int          # uint32, Starting packet number, client should set to 0
    ExtraInfo: int       # uint32, For J2K this is the image size (bytes), for other formats it's zero

class RequestImagePacket(Packet): # Client -> Server
    """Client requests one or more images/textures via UDP."""
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID,
                 image_requests: list[dict], # list of dicts matching RequestImageBlock fields
                 header: PacketHeader | None = None):
        super().__init__(PacketType.RequestImage, header if header else PacketHeader())
        self.agent_data = RequestImageAgentDataBlock(AgentID=agent_id, SessionID=session_id)
        self.request_image_blocks: list[RequestImageBlock] = []
        for req_dict in image_requests:
            self.request_image_blocks.append(RequestImageBlock(
                Image=req_dict.get('Image', CustomUUID.ZERO),
                Type=req_dict.get('Type', ImageType.NORMAL.value), # Default to Normal
                DiscardLevel=req_dict.get('DiscardLevel', 0),
                DownloadPriority=req_dict.get('DownloadPriority', 100.0), # Default high priority
                Packet=req_dict.get('Packet', 0),
                ExtraInfo=req_dict.get('ExtraInfo', 0)
            ))
        self.header.reliable = False # Typically not reliable, server resends ImageData if needed

    def to_bytes(self) -> bytes:
        data = bytearray()
        # AgentData
        data.extend(self.agent_data.AgentID.get_bytes())
        data.extend(self.agent_data.SessionID.get_bytes())

        # RequestImage Blocks
        num_requests = len(self.request_image_blocks)
        if num_requests > 255: # Max 1 Request block in C# (count byte for "NumBlocks" is 1)
                               # However, packet structure implies it can be an array.
                               # The packet format implies NumBlocks is for the *entire packet content*, not per image.
                               # C# RequestImagePacket is designed for ONE image request per packet.
                               # For multiple, client sends multiple RequestImagePackets.
            logger.warning(f"RequestImagePacket: Number of requests ({num_requests}) exceeds typical single request. Sending only the first.")
            num_requests = 1

        # The packet structure in C# has one RequestImageBlock directly, not an array.
        # If sending multiple, client sends multiple packets.
        # For now, this implementation will send only the first request if multiple are provided.
        if num_requests > 0:
            block = self.request_image_blocks[0]
            data.extend(block.Image.get_bytes())
            data.append(block.Type & 0xFF)
            data.append(block.DiscardLevel & 0xFF)
            data.extend(helpers.float_to_bytes(block.DownloadPriority))
            data.extend(helpers.uint32_to_bytes(block.Packet))
            data.extend(helpers.uint32_to_bytes(block.ExtraInfo))
        else: # No requests, send empty packet (server will likely ignore)
            pass # Or raise error if this is invalid

        return bytes(data)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive RequestImagePacket in this form.")
        return self


@dataclasses.dataclass
class ImageNotInDatabaseIDBlock: # For ImageNotInDatabasePacket
    ID: CustomUUID

class ImageNotInDatabasePacket(Packet): # Server -> Client
    """Server indicates that a requested image texture is not in its database."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ImageNotInDatabase, header if header else PacketHeader())
        self.image_id_block = ImageNotInDatabaseIDBlock(ID=CustomUUID.ZERO)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        if length < 16: raise ValueError("ImageNotInDatabasePacket body too short.")
        self.image_id_block.ID = CustomUUID(buffer, offset)
        return self

    def to_bytes(self) -> bytes:
        logger.warning("Client doesn't send ImageNotInDatabasePacket.")
        return b''


@dataclasses.dataclass
class ImageDataImageIDBlock: # For ImageDataPacket
    ID: CustomUUID
    Size: int # uint32, total size of the image data
    Codec: int # byte, e.g., 0 for J2K, 2 for Lossless, 3 for PNG

@dataclasses.dataclass
class ImageDataDataBlock: # For ImageDataPacket
    Data: bytes # Variable length

class ImageDataPacket(Packet): # Server -> Client
    """Server sends a chunk of image data."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.ImageData, header if header else PacketHeader())
        self.image_id_block = ImageDataImageIDBlock(ID=CustomUUID.ZERO, Size=0, Codec=0)
        self.image_data_block = ImageDataDataBlock(Data=b'')

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # ImageID Block (ID:16, Size:4, Codec:1 = 21 bytes)
        if length < 21: raise ValueError("ImageDataPacket body too short for ImageIDBlock.")
        self.image_id_block.ID = CustomUUID(buffer, offset); offset += 16
        self.image_id_block.Size = helpers.bytes_to_uint32(buffer, offset); offset += 4
        self.image_id_block.Codec = buffer[offset]; offset += 1

        # ImageData Block (remaining data)
        self.image_data_block.Data = buffer[offset : offset + (length - 21)]
        return self

    def to_bytes(self) -> bytes:
        logger.warning("Client doesn't send ImageDataPacket.")
        return b''


# --- Asset Upload Packets ---

@dataclasses.dataclass
class AssetUploadRequestAssetBlock: # For AssetUploadRequestPacket
    TransactionID: CustomUUID # New random UUID for this upload session
    Type: int             # sbyte, from AssetType enum
    Tempfile: bool        # bool, True if asset is short-lived (e.g., for immediate use like baking)
    Public: bool          # bool, True if asset is public (not used often, permissions handle this)
    StoreLocal: bool      # bool, True if asset should be stored locally by server (viewer internal use, often false)
    Size: int = 0         # int32, True size of the asset, even if Data field is empty for Xfer
    Data: bytes | None = None # Asset data for small assets. If None or empty for large assets, server may initiate Xfer.

class AssetUploadRequestPacket(Packet): # Client -> Server
    """Client initiates an asset upload, potentially with data for small assets."""
    def __init__(self, transaction_id: CustomUUID, asset_type: AssetType,
                 asset_size: int, # True size of the asset
                 is_temp: bool, is_public: bool, store_local: bool,
                 data: bytes | None, # Actual data chunk, can be None or empty for Xfer
                 header: PacketHeader | None = None):
        super().__init__(PacketType.AssetUploadRequest, header if header else PacketHeader())
        self.asset_block = AssetUploadRequestAssetBlock(
            TransactionID=transaction_id,
            Type=asset_type.value,
            Tempfile=is_temp,
            Public=is_public,
            StoreLocal=store_local,
            Size=asset_size,
            Data=data if data is not None else b'' # Store empty bytes if None, for len()
        )
        self.header.reliable = True

    def to_bytes(self) -> bytes:
        data_bytes = bytearray()
        # AssetBlock
        data_bytes.extend(self.asset_block.TransactionID.get_bytes())
        data_bytes.append(self.asset_block.Type & 0xFF) # sbyte in C#, pack as byte
        data_bytes.append(1 if self.asset_block.Tempfile else 0)
        data_bytes.append(1 if self.asset_block.Public else 0)
        data_bytes.append(1 if self.asset_block.StoreLocal else 0)
        data_bytes.extend(helpers.int32_to_bytes(self.asset_block.Size)) # Add true asset size

        # Data is variable length, prefixed by its size (u32)
        # If self.asset_block.Data is b'', len is 0, correct for Xfer initiation.
        actual_data_to_send = self.asset_block.Data if self.asset_block.Data is not None else b''
        data_bytes.extend(helpers.uint32_to_bytes(len(actual_data_to_send)))
        data_bytes.extend(actual_data_to_send)
        return bytes(data_bytes)

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        logger.warning("Client doesn't receive AssetUploadRequestPacket.")
        return self


# AssetBlock in C# AssetUploadCompletePacket includes TransactionID
@dataclasses.dataclass
class AssetUploadCompleteAssetBlock: # For AssetUploadCompletePacket
    TransactionID: CustomUUID # UUID, should match the one from AssetUploadRequestPacket
    Success: bool       # bool, True if upload was successful
    AssetUUID: CustomUUID # UUID of the newly uploaded asset (if Success is True)
    Type: int           # sbyte, from AssetType enum (type of asset that was uploaded)

    @property
    def type_enum(self) -> AssetType:
        try: return AssetType(self.Type)
        except ValueError: return AssetType.Unknown

class AssetUploadCompletePacket(Packet): # Server -> Client
    """Server confirms asset upload completion and provides the new asset's UUID."""
    def __init__(self, header: PacketHeader | None = None):
        super().__init__(PacketType.AssetUploadComplete, header if header else PacketHeader())
        self.asset_block = AssetUploadCompleteAssetBlock( # Renamed from data_block to asset_block
            TransactionID=CustomUUID.ZERO,
            Success=False,
            AssetUUID=CustomUUID.ZERO,
            Type=AssetType.Unknown.value
        )

    def from_bytes_body(self, buffer: bytes, offset: int, length: int):
        # Min size: TransactionID (16) + Success (1) + AssetUUID (16) + Type (1) = 34 bytes
        if length < 34:
            raise ValueError(f"AssetUploadCompletePacket body too short ({length} bytes). Expected at least 34.")

        self.asset_block.TransactionID = CustomUUID(buffer, offset); offset += 16
        self.asset_block.Success = (buffer[offset] != 0); offset += 1
        self.asset_block.AssetUUID = CustomUUID(buffer, offset); offset += 16
        self.asset_block.Type = struct.unpack_from('<b', buffer, offset)[0]; offset += 1 # sbyte

        return self

    def to_bytes(self) -> bytes:
        logger.warning("Client doesn't send AssetUploadCompletePacket.")
        return b''
