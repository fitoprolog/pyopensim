# This file marks pylibremetaverse.utils as a Python package.

from .crc32 import CRC32
from .helpers import (
    PI,
    TWO_PI,
    DEG_TO_RAD,
    RAD_TO_DEG,
    HALF_PI,
    EPOCH,
    bytes_to_int16,
    bytes_to_uint16,
    bytes_to_int32,
    bytes_to_uint32,
    bytes_to_int64,
    bytes_to_uint64,
    bytes_to_float,
    bytes_to_double,
    int16_to_bytes,
    uint16_to_bytes,
    int32_to_bytes,
    uint32_to_bytes,
    int64_to_bytes,
    uint64_to_bytes,
    float_to_bytes,
    double_to_bytes,
    bytes_to_uint16_big_endian,
    uint16_to_bytes_big_endian,
    bytes_to_uint32_big_endian,
    uint32_to_bytes_big_endian,
    bytes_to_uint64_big_endian,
    uint64_to_bytes_big_endian,
    bytes_to_string,
    string_to_bytes,
    bytes_to_hex_string,
    hex_string_to_bytes,
    float_to_byte_packed,
    byte_to_float_packed,
    float_to_uint16_packed,
    uint16_to_float_packed,
    get_unix_time,
    unix_time_to_datetime,
    datetime_to_unix_time,
    uints_to_long,
    long_to_uints,
    md5_bytes,
    sha1_bytes,
    sha256_bytes,
    ip_address_to_bytes,
    bytes_to_ip_address,
    ip_endpoint_to_bytes,
    bytes_to_ip_endpoint,
    clamp,
    lerp,
    approximately_equal, # Renamed from લગભગ_equal for PEP8 compliance
    zero_encode, # Added
    zero_decode, # Added
)

__all__ = [
    "CRC32",
    # Constants from helpers
    "PI",
    "TWO_PI",
    "DEG_TO_RAD",
    "RAD_TO_DEG",
    "HALF_PI",
    "EPOCH",
    # Byte/Numeric Conversion
    "bytes_to_int16",
    "bytes_to_uint16",
    "bytes_to_int32",
    "bytes_to_uint32",
    "bytes_to_int64",
    "bytes_to_uint64",
    "bytes_to_float",
    "bytes_to_double",
    "int16_to_bytes",
    "uint16_to_bytes",
    "int32_to_bytes",
    "uint32_to_bytes",
    "int64_to_bytes",
    "uint64_to_bytes",
    "float_to_bytes",
    "double_to_bytes",
    "bytes_to_uint16_big_endian",
    "uint16_to_bytes_big_endian",
    "bytes_to_uint32_big_endian",
    "uint32_to_bytes_big_endian",
    "bytes_to_uint64_big_endian",
    "uint64_to_bytes_big_endian",
    # String Conversion
    "bytes_to_string",
    "string_to_bytes",
    "bytes_to_hex_string",
    "hex_string_to_bytes",
    # Packed Value
    "float_to_byte_packed",
    "byte_to_float_packed",
    "float_to_uint16_packed",
    "uint16_to_float_packed",
    # Time Conversion
    "get_unix_time",
    "unix_time_to_datetime",
    "datetime_to_unix_time",
    # Bit Packing
    "uints_to_long",
    "long_to_uints",
    # Hashing
    "md5_bytes",
    "sha1_bytes",
    "sha256_bytes",
    # IP Address Helpers
    "ip_address_to_bytes",
    "bytes_to_ip_address",
    "ip_endpoint_to_bytes",
    "bytes_to_ip_endpoint",
    # Other Utilities
    "clamp",
    "lerp",
    "approximately_equal",
    zero_encode,
    zero_decode,
)

from .bit_packing import ( # Added
    get_bits,
    dequantize,
    read_packed_vector3,
    read_packed_quaternion,
    DEFAULT_REGION_SIZE_X, # Expose defaults if useful
    DEFAULT_REGION_SIZE_Y,
    DEFAULT_REGION_SIZE_Z,
)

__all__ = [
    "CRC32",
    # Constants from helpers
    "PI", "TWO_PI", "DEG_TO_RAD", "RAD_TO_DEG", "HALF_PI", "EPOCH",
    # Byte/Numeric Conversion
    "bytes_to_int16", "bytes_to_uint16", "bytes_to_int32", "bytes_to_uint32",
    "bytes_to_int64", "bytes_to_uint64", "bytes_to_float", "bytes_to_double",
    "int16_to_bytes", "uint16_to_bytes", "int32_to_bytes", "uint32_to_bytes",
    "int64_to_bytes", "uint64_to_bytes", "float_to_bytes", "double_to_bytes",
    "bytes_to_uint16_big_endian", "uint16_to_bytes_big_endian",
    "bytes_to_uint32_big_endian", "uint32_to_bytes_big_endian",
    "bytes_to_uint64_big_endian", "uint64_to_bytes_big_endian",
    # String Conversion
    "bytes_to_string", "string_to_bytes", "bytes_to_hex_string", "hex_string_to_bytes",
    # Packed Value
    "float_to_byte_packed", "byte_to_float_packed",
    "float_to_uint16_packed", "uint16_to_float_packed",
    # Time Conversion
    "get_unix_time", "unix_time_to_datetime", "datetime_to_unix_time",
    # Bit Packing (Original)
    "uints_to_long", "long_to_uints",
    # Hashing
    "md5_bytes", "sha1_bytes", "sha256_bytes",
    # IP Address Helpers
    "ip_address_to_bytes", "bytes_to_ip_address",
    "ip_endpoint_to_bytes", "bytes_to_ip_endpoint",
    # Other Utilities
    "clamp", "lerp", "approximately_equal",
    # Zero Coding
    "zero_encode", "zero_decode",
    # Bit Packing (New)
    "get_bits", "dequantize", "read_packed_vector3", "read_packed_quaternion",
    "DEFAULT_REGION_SIZE_X", "DEFAULT_REGION_SIZE_Y", "DEFAULT_REGION_SIZE_Z",
]
