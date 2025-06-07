import math
from pylibremetaverse.types import Vector3, Quaternion # Assuming these are defined

# Default region size for dequantization range, can be overridden
DEFAULT_REGION_SIZE_X: float = 256.0
DEFAULT_REGION_SIZE_Y: float = 256.0
DEFAULT_REGION_SIZE_Z_MAX: float = 4096.0 # Max Z for dequantization, C# often uses 1024*4
SIM_MIN_POS_Z: float = 0.0

# Constants for terse decoding based on typical C# BitPack values
# These define the number of bits used for each component of a vector/quaternion
# and the min/max float values they represent after dequantization.

# Position
AVATAR_POS_BITS: int = 16 # Typically for unattached avatars
PRIM_POS_BITS: int = 16   # Typically for unattached prims
ATTACHMENT_POS_BITS: int = 8
# ATTACHMENT_POS_SCALE = 10.0 / 128.0 # (0.078125f)
ATTACHMENT_POS_MIN: float = -128.0 * (10.0 / 128.0) # -10.0
ATTACHMENT_POS_MAX: float = 127.0 * (10.0 / 128.0)  # Approx 9.92

AVATAR_TERSE_POS_BITS: int = 8 # For terse avatar updates
AVATAR_TERSE_POS_MIN: float = -4.0 # Based on C# factor of 4.0 for AVATAR_TERSE_POS_MAX_LIMITED
AVATAR_TERSE_POS_MAX: float = 4.0
PRIM_TERSE_POS_BITS: int = 16 # For terse prim updates (often same as full)


# Velocity & Acceleration (often packed similarly)
VELOCITY_BITS: int = 8
VELOCITY_MIN: float = -64.0
VELOCITY_MAX: float = 64.0

ACCELERATION_BITS: int = 8
ACCELERATION_MIN: float = -64.0
ACCELERATION_MAX: float = 64.0

# Rotation (Quaternion components X, Y, Z)
QUATERNION_COMPONENT_BITS: int = 16 # Each of X, Y, Z sent as 16-bit signed
QUATERNION_COMPONENT_MIN: float = -1.0 # Dequantized range
QUATERNION_COMPONENT_MAX: float = 1.0

# Angular Velocity
ANGULAR_VELOCITY_BITS: int = 12
ANGULAR_VELOCITY_MIN: float = -math.pi
ANGULAR_VELOCITY_MAX: float = math.pi


def get_bits(data: bytes, bit_offset: int, num_bits: int) -> int:
    """
    Extracts num_bits from a byte array (data) starting at bit_offset.
    Bits are read from left to right (MSB to LSB within a byte).
    """
    if num_bits == 0:
        return 0
    if num_bits > 32: # Max for standard int return, Python handles larger but good practice
        raise ValueError("num_bits > 32 not supported by this simple implementation")

    start_byte = bit_offset // 8
    end_byte = (bit_offset + num_bits - 1) // 8

    if end_byte >= len(data):
        raise ValueError(f"Not enough data to read {num_bits} bits at offset {bit_offset}. Data len: {len(data)}, needs up to byte {end_byte}")

    val = 0
    for i in range(start_byte, end_byte + 1):
        val = (val << 8) | data[i]

    # Shift to align the desired bits to the right
    # Total bits read from start_byte to end_byte
    total_bits_in_window = (end_byte - start_byte + 1) * 8
    # Number of bits to discard from the right end of the window
    shift_right_amount = total_bits_in_window - (bit_offset % 8 + num_bits)

    val >>= shift_right_amount

    # Mask to get only the num_bits
    mask = (1 << num_bits) - 1
    return val & mask


def dequantize(val: int, num_bits: int, min_val: float, max_val: float) -> float:
    """
    Converts an integer val (extracted using get_bits) back to a float
    in the range [min_val, max_val].
    """
    if num_bits <= 0: return min_val # Avoid division by zero or negative shift
    max_quantized_val = (1 << num_bits) - 1
    if max_quantized_val == 0: return min_val

    return min_val + (float(val) / max_quantized_val) * (max_val - min_val)

def get_signed_bits(data: bytes, bit_offset: int, num_bits: int) -> int:
    """Reads num_bits as an unsigned integer, then converts to signed if MSB is set."""
    val_unsigned = get_bits(data, bit_offset, num_bits)
    if num_bits <= 0: return 0 # Or raise error
    msb_mask = 1 << (num_bits - 1)
    if val_unsigned & msb_mask: # Check MSB for signedness
        # Convert to negative (e.g., for 8 bits, 0xFF (-1) becomes 255; 255 - 256 = -1)
        return val_unsigned - (1 << num_bits)
    return val_unsigned

def dequantize_from_bits(data: bytes, bit_offset: int, num_bits: int,
                         min_val: float, max_val: float,
                         is_signed_int: bool = False) -> tuple[float, int]:
    """Helper to combine get_bits and dequantize for a single component."""
    if is_signed_int:
        quantized_val = get_signed_bits(data, bit_offset, num_bits)
    else:
        quantized_val = get_bits(data, bit_offset, num_bits)
    bit_offset += num_bits

    # For signed dequantization where the range [min_val, max_val] is symmetric (e.g. -A to A)
    # and the integer was packed from a signed value, the C# BitPack.DequantizeSigned often uses:
    # return (float)quantized_val * (max_val / max_absolute_quantized_val_for_type)
    # e.g. for an 8-bit signed value (-128 to 127), max_abs_quantized is 127.
    # if is_signed_int and min_val == -max_val: # Symmetric signed range
    #     max_abs_q_val = (1 << (num_bits - 1)) -1
    #     if max_abs_q_val == 0: return 0.0, bit_offset
    #     return (float(quantized_val) / max_abs_q_val) * max_val, bit_offset
    # else: # Standard unsigned or asymmetric signed dequantization
    # The provided dequantize function should handle signed ranges correctly if min_val is negative.

    val_float = dequantize(quantized_val, num_bits, min_val, max_val)
    return val_float, bit_offset


def read_packed_vector3(data: bytes, bit_offset: int,
                        num_bits_list: list[int], # num_bits for X, Y, Z
                        min_val_list: list[float],  # min_val for X, Y, Z
                        max_val_list: list[float],  # max_val for X, Y, Z
                        is_signed_list: list[bool]  # is_signed for X, Y, Z
                        ) -> tuple[Vector3, int]:
    """
    Reads 3 components for a Vector3 with per-component packing parameters.
    Returns the Vector3 and the new bit_offset.
    """
    if not (len(num_bits_list) == 3 and len(min_val_list) == 3 and \
            len(max_val_list) == 3 and len(is_signed_list) == 3):
        raise ValueError("num_bits, min_val, max_val, and is_signed lists must all have 3 elements.")

    x, bit_offset = dequantize_from_bits(data, bit_offset, num_bits_list[0], min_val_list[0], max_val_list[0], is_signed_list[0])
    y, bit_offset = dequantize_from_bits(data, bit_offset, num_bits_list[1], min_val_list[1], max_val_list[1], is_signed_list[1])
    z, bit_offset = dequantize_from_bits(data, bit_offset, num_bits_list[2], min_val_list[2], max_val_list[2], is_signed_list[2])

    return Vector3(x, y, z), bit_offset


def read_packed_quaternion(data: bytes, bit_offset: int) -> tuple[Quaternion, int]:
    """
    Reads a packed quaternion. Typically, 3 components (X, Y, Z) are sent,
    each as a 16-bit signed integer. The W component is derived.
    The 16-bit values represent the range [-1.0, 1.0].
    This corresponds to `PackToShort_1s()` in C# which maps float to short `(short)(value * 32767.0f)`.
    """
    # Each component is 16 bits
    num_bits_component = 16

    # Read X, Y, Z as signed 16-bit integers (if they were packed that way)
    # get_bits returns unsigned. We need to interpret them as signed if they were packed from signed shorts.
    # C# packs them directly as `(short)(value * 32767.0f)`.
    # So, when dequantizing, we need to know the original signed range.
    # A common way is to read as unsigned, then convert to signed if MSB is set.

    def read_signed_short_as_int(d: bytes, bo: int) -> int:
        val_unsigned = get_bits(d, bo, 16)
        if val_unsigned & (1 << 15): # Check MSB for signedness
            return val_unsigned - (1 << 16) # Convert to negative if MSB is set
        return val_unsigned

    x_s = read_signed_short_as_int(data, bit_offset); bit_offset += num_bits_component
    y_s = read_signed_short_as_int(data, bit_offset); bit_offset += num_bits_component
    z_s = read_signed_short_as_int(data, bit_offset); bit_offset += num_bits_component

    # Dequantize from short range [-32767, 32767] to float [-1.0, 1.0]
    # (Actually, PackToShort_1s uses 32767.0f, so max value is 32767)
    # Inverse of (short)(value * 32767.0f) is (float)short_val / 32767.0f
    max_short_val = 32767.0
    x = float(x_s) / max_short_val
    y = float(y_s) / max_short_val
    z = float(z_s) / max_short_val

    # Derive W component
    sum_sq = x*x + y*y + z*z
    if sum_sq > 1.0: # Clamp to avoid math domain error from precision issues
        # This also implies re-normalization might be needed if sum_sq is significantly off
        # For now, just clamp for sqrt. A full normalization of (x,y,z) before deriving w might be better.
        sum_sq = 1.0
        # Normalize x,y,z if sum_sq was > 1.0 to maintain unit quaternion property as best as possible.
        # This is a simplified approach.
        len_xyz = math.sqrt(x*x + y*y + z*z) # Re-calculate original length before clamping sum_sq
        if len_xyz > 1e-6 : # Avoid division by zero
             x /= len_xyz; y /= len_xyz; z /= len_xyz

    w = math.sqrt(1.0 - sum_sq)

    return Quaternion(x, y, z, w).normalize(), bit_offset # Ensure normalized

# TODO: Add functions to *pack* (quantize and write_bits) values if client needs to send these.
# def write_bits(dest_bytearray: bytearray, bit_offset: int, num_bits: int, value: int) -> int: ...
# def quantize(f_val: float, num_bits: int, min_val: float, max_val: float) -> int: ...
# def write_packed_vector3(...): ...
# def write_packed_quaternion(...): ...
