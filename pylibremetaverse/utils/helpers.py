import struct
import binascii
import datetime
import hashlib
import math
import socket
import ipaddress

# Constants
PI = math.pi
TWO_PI = 2.0 * math.pi
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi
HALF_PI = math.pi / 2.0
EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

# --- Byte/Numeric Conversion Functions (Little Endian default) ---

def bytes_to_int16(data: bytes, offset: int = 0) -> int:
    """Converts 2 bytes (little endian) to a signed 16-bit integer."""
    return struct.unpack_from('<h', data, offset)[0]

def bytes_to_uint16(data: bytes, offset: int = 0) -> int:
    """Converts 2 bytes (little endian) to an unsigned 16-bit integer."""
    return struct.unpack_from('<H', data, offset)[0]

def bytes_to_int32(data: bytes, offset: int = 0) -> int:
    """Converts 4 bytes (little endian) to a signed 32-bit integer."""
    return struct.unpack_from('<i', data, offset)[0]

def bytes_to_uint32(data: bytes, offset: int = 0) -> int:
    """Converts 4 bytes (little endian) to an unsigned 32-bit integer."""
    return struct.unpack_from('<I', data, offset)[0]

def bytes_to_int64(data: bytes, offset: int = 0) -> int:
    """Converts 8 bytes (little endian) to a signed 64-bit integer."""
    return struct.unpack_from('<q', data, offset)[0]

def bytes_to_uint64(data: bytes, offset: int = 0) -> int:
    """Converts 8 bytes (little endian) to an unsigned 64-bit integer."""
    return struct.unpack_from('<Q', data, offset)[0]

def bytes_to_float(data: bytes, offset: int = 0) -> float:
    """Converts 4 bytes (little endian) to a single-precision float."""
    return struct.unpack_from('<f', data, offset)[0]

def bytes_to_double(data: bytes, offset: int = 0) -> float:
    """Converts 8 bytes (little endian) to a double-precision float."""
    return struct.unpack_from('<d', data, offset)[0]

def int16_to_bytes(value: int) -> bytes:
    """Converts a signed 16-bit integer to 2 bytes (little endian)."""
    return struct.pack('<h', value)

def uint16_to_bytes(value: int) -> bytes:
    """Converts an unsigned 16-bit integer to 2 bytes (little endian)."""
    return struct.pack('<H', value)

def int32_to_bytes(value: int) -> bytes:
    """Converts a signed 32-bit integer to 4 bytes (little endian)."""
    return struct.pack('<i', value)

def uint32_to_bytes(value: int) -> bytes:
    """Converts an unsigned 32-bit integer to 4 bytes (little endian)."""
    return struct.pack('<I', value)

def int64_to_bytes(value: int) -> bytes:
    """Converts a signed 64-bit integer to 8 bytes (little endian)."""
    return struct.pack('<q', value)

def uint64_to_bytes(value: int) -> bytes:
    """Converts an unsigned 64-bit integer to 8 bytes (little endian)."""
    return struct.pack('<Q', value)

def float_to_bytes(value: float) -> bytes:
    """Converts a single-precision float to 4 bytes (little endian)."""
    return struct.pack('<f', value)

def double_to_bytes(value: float) -> bytes:
    """Converts a double-precision float to 8 bytes (little endian)."""
    return struct.pack('<d', value)

# Big Endian versions
def bytes_to_uint16_big_endian(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from('>H', data, offset)[0]

def uint16_to_bytes_big_endian(value: int) -> bytes:
    return struct.pack('>H', value)

def bytes_to_uint32_big_endian(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from('>I', data, offset)[0]

def uint32_to_bytes_big_endian(value: int) -> bytes:
    return struct.pack('>I', value)

def bytes_to_uint64_big_endian(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from('>Q', data, offset)[0]

def uint64_to_bytes_big_endian(value: int) -> bytes:
    return struct.pack('>Q', value)


# --- String Conversion Functions ---

def bytes_to_string(data: bytes, offset: int = 0, length: int = -1) -> str:
    """
    Decodes a byte array (UTF-8) to a string.
    If length is -1, decodes until the first null terminator or end of data.
    Otherwise, decodes a slice of the specified length.
    """
    if not data:
        return ""

    if offset >= len(data):
        return ""

    if length == -1:
        # Find null terminator or end of data
        actual_data = data[offset:]
        null_idx = actual_data.find(b'\x00')
        if null_idx != -1:
            return actual_data[:null_idx].decode('utf-8', errors='replace')
        else:
            return actual_data.decode('utf-8', errors='replace')
    else:
        end = min(offset + length, len(data))
        actual_data = data[offset:end]
        # If there's a null terminator within the specified length, only decode up to it.
        null_idx = actual_data.find(b'\x00')
        if null_idx != -1:
             return actual_data[:null_idx].decode('utf-8', errors='replace')
        return actual_data.decode('utf-8', errors='replace')


def string_to_bytes(s: str, add_null_terminator: bool = True) -> bytes:
    """Encodes a string to UTF-8 bytes, optionally adding a null terminator."""
    b = s.encode('utf-8')
    if add_null_terminator:
        b += b'\x00'
    return b

def bytes_to_hex_string(data: bytes) -> str:
    """Converts bytes to a hexadecimal string."""
    return binascii.hexlify(data).decode('ascii')

def hex_string_to_bytes(hex_str: str) -> bytes:
    """Converts a hexadecimal string to bytes."""
    return binascii.unhexlify(hex_str)


# --- Packed Value Functions ---

def float_to_byte_packed(value: float, lower: float, upper: float) -> int:
    """Packs a float into a byte (0-255) given a range [lower, upper]."""
    if lower >= upper:
        raise ValueError("Lower bound must be less than upper bound.")
    clamped_val = max(lower, min(upper, value))
    normalized_val = (clamped_val - lower) / (upper - lower)
    return int(round(normalized_val * 255.0))

def byte_to_float_packed(byte_val: int, lower: float, upper: float) -> float:
    """Unpacks a byte (0-255) into a float given a range [lower, upper]."""
    if not (0 <= byte_val <= 255):
        raise ValueError("Byte value must be between 0 and 255.")
    if lower >= upper:
        raise ValueError("Lower bound must be less than upper bound.")
    normalized_val = float(byte_val) / 255.0
    return lower + normalized_val * (upper - lower)

def float_to_uint16_packed(value: float, lower: float, upper: float) -> int:
    """Packs a float into a uint16 (0-65535) given a range [lower, upper]."""
    if lower >= upper:
        raise ValueError("Lower bound must be less than upper bound.")
    clamped_val = max(lower, min(upper, value))
    normalized_val = (clamped_val - lower) / (upper - lower)
    return int(round(normalized_val * 65535.0))

def uint16_to_float_packed(uint16_val: int, lower: float, upper: float) -> float:
    """Unpacks a uint16 (0-65535) into a float given a range [lower, upper]."""
    if not (0 <= uint16_val <= 65535):
        raise ValueError("UInt16 value must be between 0 and 65535.")
    if lower >= upper:
        raise ValueError("Lower bound must be less than upper bound.")
    normalized_val = float(uint16_val) / 65535.0
    return lower + normalized_val * (upper - lower)

def scale_float_to_sbyte(value: float, min_val: float, max_val: float) -> int:
    """
    Scales a float to an sbyte (-128 to 127).
    The input float is first clamped to [min_val, max_val],
    then normalized to the range [-1.0, 1.0],
    and finally scaled to [-128, 127].
    """
    if min_val >= max_val:
        # Or handle as error, depending on desired behavior for invalid range
        if value <= min_val: return -128
        if value >= max_val: return 127
        return 0 # Midpoint for invalid range if value is also invalid

    clamped_val = max(min_val, min(value, max_val))

    # Normalize to 0-1 first relative to the span
    normalized_zero_to_one = (clamped_val - min_val) / (max_val - min_val)

    # Scale to -1 to 1
    normalized_neg_one_to_one = (normalized_zero_to_one * 2.0) - 1.0

    # Scale to sbyte range
    # Using 127.0 as multiplier to ensure it maps correctly; result is rounded and clamped.
    scaled = round(normalized_neg_one_to_one * 127.0)

    return int(max(-128, min(127, scaled)))


# --- Time Conversion ---

def get_unix_time() -> int:
    """Returns the current UTC time as a Unix timestamp (seconds since epoch)."""
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())

def unix_time_to_datetime(timestamp: int) -> datetime.datetime:
    """Converts a Unix timestamp to a UTC datetime object."""
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

def datetime_to_unix_time(dt: datetime.datetime) -> int:
    """Converts a datetime object to a Unix timestamp."""
    return int(dt.timestamp())


# --- Bit Packing ---

def uints_to_long(high_uint: int, low_uint: int) -> int:
    """Combines two 32-bit unsigned integers into a 64-bit integer."""
    # Ensure inputs are within uint32 range for conceptual clarity, though Python handles large ints
    # high_uint &= 0xFFFFFFFF
    # low_uint &= 0xFFFFFFFF
    return (high_uint << 32) | low_uint

def long_to_uints(val: int) -> tuple[int, int]:
    """Splits a 64-bit integer into two 32-bit unsigned integers (high, low)."""
    high_uint = (val >> 32) & 0xFFFFFFFF
    low_uint = val & 0xFFFFFFFF
    return high_uint, low_uint


# --- Hashing ---

def md5_bytes(data: bytes) -> bytes:
    """Calculates the MD5 hash of byte data."""
    return hashlib.md5(data).digest()

def sha1_bytes(data: bytes) -> bytes:
    """Calculates the SHA1 hash of byte data."""
    return hashlib.sha1(data).digest()

def sha256_bytes(data: bytes) -> bytes:
    """Calculates the SHA256 hash of byte data."""
    return hashlib.sha256(data).digest()

# --- IP Address Helpers ---

def ip_address_to_bytes(addr: ipaddress.IPv4Address) -> bytes:
    """Converts an IPv4Address object to 4 bytes (network order)."""
    return addr.packed # Already big-endian

def bytes_to_ip_address(data: bytes, offset: int = 0) -> ipaddress.IPv4Address:
    """Converts 4 bytes (network order) to an IPv4Address object."""
    return ipaddress.IPv4Address(data[offset:offset+4])

def ip_endpoint_to_bytes(addr: ipaddress.IPv4Address, port: int) -> bytes:
    """Converts an IPv4Address and port to 6 bytes (IP big-endian, port big-endian)."""
    return addr.packed + uint16_to_bytes_big_endian(port)

def bytes_to_ip_endpoint(data: bytes, offset: int = 0) -> tuple[ipaddress.IPv4Address, int]:
    """Converts 6 bytes to an IPv4Address and port."""
    ip_addr = ipaddress.IPv4Address(data[offset:offset+4])
    port = bytes_to_uint16_big_endian(data, offset+4)
    return ip_addr, port

# --- Other Utilities from Utils.cs often used ---

def clamp(value, min_val, max_val):
    """Clamps a value to the range [min_val, max_val]."""
    return max(min_val, min(value, max_val))

def lerp(start, end, amount):
    """Linear interpolation between start and end by amount (0-1)."""
    return start + (end - start) * amount

def approximately_equal(a: float, b: float, tolerance: float = 1e-6) -> bool:
    """Checks if two floats are approximately equal within a tolerance."""
    return abs(a - b) < tolerance


# --- Zero Coding (Placeholders) ---

def zero_encode(data: bytes) -> bytes:
    """
    Performs zero-coding compression on a byte array.
    Placeholder: Returns original data. Actual implementation is complex.
    See LibreMetaverse.Utils.ZeroEncode for reference.
    """
    # TODO: Implement actual zero-coding
    return data

def zero_decode(data: bytes, data_length: int, decompressed_buffer: bytearray) -> int:
    """
    Performs zero-coding decompression on a byte array.
    Placeholder: Copies original data. Actual implementation is complex.
    Args:
        data: The zero-coded byte array.
        data_length: The length of the data to decode from the source 'data' buffer.
        decompressed_buffer: A pre-allocated bytearray to store the decompressed data.
                             This buffer should be large enough (e.g., MAX_PACKET_SIZE).
    Returns:
        The actual length of the decompressed data.
    See LibreMetaverse.Utils.ZeroDecode for reference.
    """
    # TODO: Implement actual zero-decoding
    # Basic placeholder: copy data if it fits, assuming no actual compression/expansion.
    # This is NOT a correct zero-decode implementation.
    if data_length > len(decompressed_buffer): # Ensure we don't write past the end of source 'data' either
        # This check is more about the source 'data' vs 'data_length'
        raise ValueError("data_length exceeds source data buffer size, or decompressed_buffer is too small.")

    if data_length > 0 : # Ensure there is data to copy
        decompressed_buffer[:data_length] = data[:data_length]
    return data_length


def zero_encode(src: bytes, dest: bytearray) -> int:
    """
    Performs zero-coding compression on a byte array.
    This is a port of the C# Helpers.ZeroEncode method.
    Operates on the FULL packet data (header + body).

    Args:
        src: The source byte array (full packet data).
        dest: A pre-allocated bytearray to store the compressed data.
              Should be at least len(src) + some overhead, or MAX_PACKET_SIZE.

    Returns:
        The actual length written to dest_bytearray.
    """
    srclen = len(src)
    if srclen == 0:
        return 0

    # The MSG_APPENDED_ACKS flag (0x10) is PacketFlags.ACK
    # It indicates that the last byte of the packet payload (before this encoding)
    # specifies the number of ACKs appended to this packet.
    # Each ACK is 4 bytes (a u32 sequence number).
    # This bodylen calculation is specific to how packet ACKs are appended
    # *before* zero-coding is applied to the entire packet.
    bodylen = srclen
    if (src[0] & 0x10): # PacketFlags.ACK / MSG_APPENDED_ACKS
        # Number of appended ACKs is in the last byte of the unencoded message
        num_acks = src[srclen - 1]
        if num_acks > 0:
             bodylen = srclen - (num_acks * 4) - 1
             # num_acks * 4 for the ACK data, -1 for the byte storing num_acks itself.

    destoff = 0 # Current offset in destination buffer

    # The first 6 bytes of a message are never zero-coded
    # This typically includes the 4-byte header and first 2 bytes of payload.
    # If srclen is less than 6, then the whole message is copied.
    if srclen <= 6:
        if srclen > len(dest): return 0 # Not enough space in dest
        dest[:srclen] = src[:srclen]
        return srclen

    if len(dest) < 6: return 0 # Not enough space for even the initial copy
    dest[:6] = src[:6]
    destoff = 6

    # Zero-code the rest of the message
    srciter = 6 # Start iterating from the 7th byte of source

    while srciter < srclen:
        if destoff >= len(dest): return 0 # Ran out of space in dest

        if src[srciter] == 0x00:
            # Count zeroes
            zeros = 0
            while srciter < srclen and src[srciter] == 0x00 and zeros < 255:
                zeros += 1
                srciter += 1

            if destoff + 2 > len(dest): return 0 # Not enough space for 0x00 and zero count
            dest[destoff] = 0x00
            dest[destoff+1] = zeros & 0xFF # Store count as byte
            destoff += 2
        else:
            # Copy non-zero byte
            dest[destoff] = src[srciter]
            destoff += 1
            srciter += 1

            # Check if this is the start of the appended ACKs block
            # If MSG_APPENDED_ACKS is set and we've reached the bodylen,
            # the rest of the message is copied verbatim (these are the ACKs)
            if srciter == bodylen and (src[0] & 0x10): # MSG_APPENDED_ACKS
                remaining = srclen - srciter
                if destoff + remaining > len(dest): return 0 # Not enough space
                dest[destoff : destoff + remaining] = src[srciter : srclen]
                destoff += remaining
                srciter += remaining # Should break the loop
                break

    return destoff


def zero_decode(src: bytes, dest: bytearray) -> int:
    """
    Performs zero-coding decompression on a byte array.
    This is a port of the C# Helpers.ZeroDecode method.
    Operates on the FULL packet data.

    Args:
        src: The zero-coded source byte array (full packet data).
        dest: A pre-allocated bytearray to store the decompressed data.
              Should be large enough (e.g., MAX_PACKET_SIZE).

    Returns:
        The actual length of the decompressed data.
    """
    srclen = len(src)
    destoff = 0 # Current offset in destination buffer
    srciter = 0 # Current offset in source buffer

    # The first 6 bytes of a message are never zero-coded
    if srclen <= 6:
        if srclen > len(dest): return 0
        dest[:srclen] = src[:srclen]
        return srclen

    if len(dest) < 6: return 0
    dest[:6] = src[:6]
    destoff = 6
    srciter = 6

    while srciter < srclen:
        if destoff >= len(dest): return 0 # Ran out of space in dest

        if src[srciter] == 0x00:
            srciter += 1
            if srciter >= srclen: # Should not happen with valid encoding
                # This means a 0x00 was the last byte, which is an invalid sequence.
                # Or, source was truncated.
                return 0 # Error condition

            zeros = src[srciter] & 0xFF
            if destoff + zeros > len(dest): return 0 # Not enough space for all zeroes

            for _ in range(zeros):
                dest[destoff] = 0x00
                destoff += 1
        else:
            dest[destoff] = src[srciter]
            destoff += 1

        srciter += 1

    return destoff
