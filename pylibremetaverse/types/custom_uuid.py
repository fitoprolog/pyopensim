import uuid
import struct

class CustomUUID:
    """
    A custom UUID class that mimics the behavior of UUID.cs,
    including specific byte ordering and CRC calculation.
    """
    ZERO = None  # Will be initialized after class definition

    def __init__(self, value, offset: int = None):
        """
        Initializes a CustomUUID instance.

        Can be initialized from:
        - A string UUID representation (e.g., "11f8aa9c-b071-4242-836b-13b7abe0d489").
        - A standard Python uuid.UUID object.
        - A byte array and an offset (if value is bytes and offset is not None).
        """
        if isinstance(value, bytes) and offset is not None:
            self.from_bytes(value, offset)
        elif isinstance(value, uuid.UUID):
            self._uuid = value
        elif isinstance(value, str):
            self._uuid = uuid.UUID(value)
        elif isinstance(value, CustomUUID):
            self._uuid = value._uuid
        else:
            raise TypeError(
                "Invalid type for value. Must be bytes, uuid.UUID, CustomUUID, or str."
            )

    def to_bytes(self, dest_array: bytearray, offset: int):
        """
        Converts the internal UUID to bytes and places them into dest_array at offset.
        This method replicates the specific byte ordering from UUID.cs's ToBytes method.
        """
        if len(dest_array) < offset + 16:
            raise ValueError("Destination bytearray is too small.")

        # uuid.bytes_le is almost what we need, but UUID.cs does a specific shuffle.
        # The standard .bytes attribute is big-endian.
        # UUID.cs:
        // private byte _a; (int)
        // private byte _b; (short)
        // private byte _c; (short)
        // private byte _d;
        // private byte _e;
        // private byte _f;
        // private byte _g;
        // private byte _h;
        // private byte _i;
        // private byte _j;
        // private byte _k;
        // network byte order (big-endian) for the first 3 components
        # then the rest are just bytes

        # Python's uuid.UUID fields:
        # time_low (unsigned int, 4 bytes)
        # time_mid (unsigned short, 2 bytes)
        # time_hi_version (unsigned short, 2 bytes)
        # clock_seq_hi_variant (unsigned char, 1 byte)
        # clock_seq_low (unsigned char, 1 byte)
        # node (unsigned long, 6 bytes)

        # Mapping based on how C# UUID(byte[]) constructor works, which is what ToBytes should be inverse of.
        # C# UUID(byte[] b)
        # _a = (int)b[3] << 24 | (int)b[2] << 16 | (int)b[1] << 8 | (int)b[0];
        # _b = (short)((int)b[5] << 8 | (int)b[4]);
        # _c = (short)((int)b[7] << 8 | (int)b[6]);
        # _d = b[8];
        # _e = b[9];
        # _f = b[10];
        # _g = b[11];
        # _h = b[12];
        # _i = b[13];
        # _j = b[14];
        # _k = b[15];

        # So, ToBytes should write them in this order:
        # b[0-3] = _a (int, little-endian in array)
        # b[4-5] = _b (short, little-endian in array)
        # b[6-7] = _c (short, little-endian in array)
        # b[8-15] = _d to _k (8 bytes)

        # Get the standard big-endian bytes
        std_bytes = self._uuid.bytes

        # time_low (first 4 bytes of std_bytes) corresponds to _a, needs to be little-endian
        dest_array[offset + 0] = std_bytes[3]
        dest_array[offset + 1] = std_bytes[2]
        dest_array[offset + 2] = std_bytes[1]
        dest_array[offset + 3] = std_bytes[0]

        # time_mid (next 2 bytes of std_bytes) corresponds to _b, needs to be little-endian
        dest_array[offset + 4] = std_bytes[5]
        dest_array[offset + 5] = std_bytes[4]

        # time_hi_version (next 2 bytes of std_bytes) corresponds to _c, needs to be little-endian
        dest_array[offset + 6] = std_bytes[7]
        dest_array[offset + 7] = std_bytes[6]

        # The remaining 8 bytes are copied directly
        for i in range(8):
            dest_array[offset + 8 + i] = std_bytes[8 + i]


    def get_bytes(self) -> bytes:
        """Returns a new 16-byte bytes object by calling to_bytes."""
        arr = bytearray(16)
        self.to_bytes(arr, 0)
        return bytes(arr)

    def from_bytes(self, source_array: bytes, offset: int):
        """
        Initializes the UUID from a byte array at a given offset.
        This method replicates the byte shuffling from UUID.cs's FromBytes/UUID(byte[]) constructor.
        """
        if len(source_array) < offset + 16:
            raise ValueError("Source bytearray is too small.")

        # Read the bytes in the order C# UUID(byte[] b) expects
        # _a = (int)b[3] << 24 | (int)b[2] << 16 | (int)b[1] << 8 | (int)b[0];
        # _b = (short)((int)b[5] << 8 | (int)b[4]);
        # _c = (short)((int)b[7] << 8 | (int)b[6]);
        # _d = b[8]; ... _k = b[15];

        # These are then used to form the components for uuid.UUID constructor
        # which expects bytes in big-endian order for its 'bytes' parameter.

        b = source_array[offset : offset + 16]

        # Reconstruct the big-endian byte string for uuid.UUID
        # time_low (from b[0:4] little-endian)
        # time_mid (from b[4:6] little-endian)
        # time_hi_version (from b[6:8] little-endian)
        # clock_seq_hi_res, clock_seq_low, node (from b[8:16] as is)

        reordered_bytes = bytes([
            b[3], b[2], b[1], b[0],  # time_low
            b[5], b[4],              # time_mid
            b[7], b[6],              # time_hi_version
            b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15] # rest
        ])
        self._uuid = uuid.UUID(bytes=reordered_bytes)


    def crc(self) -> int:
        """
        Calculates a simple checksum for the UUID.
        This method implements the CRC() from UUID.cs, which sums four uints.
        """
        uuid_bytes = self.get_bytes() # These are already in the C# compatible order.

        # In C#, UUID is stored as:
        # private int _a;
        # private short _b;
        # private short _c;
        # private byte _d;
        # private byte _e;
        # private byte _f;
        # private byte _g;
        # private byte _h;
        # private byte _i;
        # private byte _j;
        # private byte _k;
        #
        # ToBytes and FromBytes use this order:
        # _a (4 bytes, little-endian), _b (2 bytes, l-e), _c (2 bytes, l-e), _d, _e, _f, _g, _h, _i, _j, _k (8 bytes)
        #
        # The CRC calculation in C# is:
        # uint accum = (uint)_a;
        # accum += (uint)((ushort)_b | ((ushort)_c << 16));
        # accum += (uint)((ushort)_d | ((ushort)_e << 8) | ((ushort)_f << 16) | ((ushort)_g << 24));
        # accum += (uint)((ushort)_h | ((ushort)_i << 8) | ((ushort)_j << 16) | ((ushort)_k << 24));
        # return (int)accum;

        # We need to unpack these parts from uuid_bytes which is ordered as per FromBytes/ToBytes.
        # uuid_bytes[0:4] is _a (int, little-endian)
        # uuid_bytes[4:6] is _b (short, little-endian)
        # uuid_bytes[6:8] is _c (short, little-endian)
        # uuid_bytes[8:16] are _d to _k

        # Read _a as a little-endian unsigned int
        val_a = struct.unpack_from('<I', uuid_bytes, 0)[0]

        # Read _b as a little-endian unsigned short
        val_b = struct.unpack_from('<H', uuid_bytes, 4)[0]

        # Read _c as a little-endian unsigned short
        val_c = struct.unpack_from('<H', uuid_bytes, 6)[0]

        # Combine _b and _c as per C# (ushort)_b | ((ushort)_c << 16)
        val_bc = val_b | (val_c << 16)

        # Read _d, _e, _f, _g and combine them
        # (uint)((ushort)_d | ((ushort)_e << 8) | ((ushort)_f << 16) | ((ushort)_g << 24));
        # These are bytes 8, 9, 10, 11
        val_defg = (uuid_bytes[8]) | \
                   (uuid_bytes[9] << 8) | \
                   (uuid_bytes[10] << 16) | \
                   (uuid_bytes[11] << 24)

        # Read _h, _i, _j, _k and combine them
        # (uint)((ushort)_h | ((ushort)_i << 8) | ((ushort)_j << 16) | ((ushort)_k << 24));
        # These are bytes 12, 13, 14, 15
        val_hijk = (uuid_bytes[12]) | \
                   (uuid_bytes[13] << 8) | \
                   (uuid_bytes[14] << 16) | \
                   (uuid_bytes[15] << 24)

        accum = val_a
        accum = (accum + val_bc) & 0xFFFFFFFF  # Emulate uint addition
        accum = (accum + val_defg) & 0xFFFFFFFF
        accum = (accum + val_hijk) & 0xFFFFFFFF

        # Convert to signed int if necessary (Python handles large integers automatically, C# int is 32-bit signed)
        if accum > 0x7FFFFFFF:
            return accum - 0x100000000
        return accum

    def __str__(self) -> str:
        """Returns the hyphenated string form of the UUID."""
        return str(self._uuid)

    def __eq__(self, other) -> bool:
        """Checks equality with another CustomUUID or uuid.UUID object."""
        if isinstance(other, CustomUUID):
            return self._uuid == other._uuid
        if isinstance(other, uuid.UUID):
            return self._uuid == other
        return False

    def __hash__(self) -> int:
        """Returns the hash of the internal uuid.UUID object."""
        return hash(self._uuid)

CustomUUID.ZERO = CustomUUID("00000000-0000-0000-0000-000000000000")
