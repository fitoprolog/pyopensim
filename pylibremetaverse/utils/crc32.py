# Ported from C# LibreMetaverse CRC32.cs

class CRC32:
    """
    Computes CRC32 checksums. This is a standard CRC32 implementation.
    """
    DefaultPolynomial = 0xEDB88320 # Standard CRC32 polynomial (reversed)
    DefaultSeed = 0xFFFFFFFF       # Standard CRC32 seed
    _table = None
    _last_polynomial_used = None

    @staticmethod
    def _initialize_table(polynomial):
        """
        Initializes the CRC32 lookup table.
        This is done once for a given polynomial.
        """
        # Only re-initialize if the table hasn't been created or if the polynomial changes
        if CRC32._table is not None and CRC32._last_polynomial_used == polynomial:
            return

        CRC32._table = [0] * 256
        for i in range(256):
            entry = i
            for _ in range(8):
                if (entry & 1) == 1:
                    entry = (entry >> 1) ^ polynomial
                else:
                    entry = entry >> 1
            CRC32._table[i] = entry
        CRC32._last_polynomial_used = polynomial

    @staticmethod
    def calculate(data, offset=0, length=None, seed=None, polynomial=None):
        """
        Computes the CRC32 checksum for a portion of a byte array.

        Args:
            data (bytes or bytearray): The input data.
            offset (int): The starting offset in the data. Defaults to 0.
            length (int, optional): The number of bytes to process.
                                   If None, processes from offset to the end of data.
            seed (int, optional): The initial CRC value (pre-inverted).
                                  Defaults to DefaultSeed (0xFFFFFFFF).
            polynomial (int, optional): The CRC polynomial.
                                        Defaults to DefaultPolynomial (0xEDB88320).

        Returns:
            int: The computed CRC32 checksum (as an unsigned 32-bit integer).
        """
        current_polynomial = polynomial if polynomial is not None else CRC32.DefaultPolynomial
        current_seed = seed if seed is not None else CRC32.DefaultSeed

        CRC32._initialize_table(current_polynomial)

        if length is None:
            length = len(data) - offset

        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Input data must be bytes or bytearray.")
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError(f"Invalid offset ({offset}) or length ({length}) for data of size {len(data)}.")

        crc = current_seed

        for i in range(length):
            byte_val = data[offset + i]
            table_idx = (crc & 0xFF) ^ byte_val
            crc = (crc >> 8) ^ CRC32._table[table_idx]

        return crc ^ 0xFFFFFFFF # Final XOR

    @staticmethod
    def compute_checksum_bytes(buffer, seed=None, polynomial=None):
        """
        Computes the CRC32 checksum for the given byte array and returns it as bytes (little-endian).
        """
        checksum = CRC32.calculate(buffer, seed=seed, polynomial=polynomial)
        return checksum.to_bytes(4, byteorder='little')

if __name__ == '__main__':
    print("Running CRC32 tests...")

    # Test case 1: Empty data
    empty_data = b''
    crc_empty = CRC32.calculate(empty_data)
    print(f"CRC for empty data: {crc_empty:08x}")
    # zlib.crc32(b'') is 0. Our calculate returns (DefaultSeed ^ 0xFFFFFFFF) if no data.
    # If DefaultSeed is 0xFFFFFFFF, then 0xFFFFFFFF ^ 0xFFFFFFFF = 0.
    assert crc_empty == 0

    # Test case 2: Simple known string "123456789"
    # CRC32("123456789") = 0xCBF43926 (standard result with default seed and polynomial)
    data_123 = b"123456789"
    crc_123 = CRC32.calculate(data_123)
    print(f"CRC for '123456789': {crc_123:08x}")
    assert crc_123 == 0xCBF43926

    # Test case 3: All zeros
    data_zeros = b'\x00' * 32
    crc_zeros = CRC32.calculate(data_zeros)
    print(f"CRC for 32 zeros: {crc_zeros:08x}") # Expected: 0x190A55AD
    assert crc_zeros == 0x190A55AD

    # Test case 4: All ones (0xFF)
    data_ones = b'\xff' * 32
    crc_ones = CRC32.calculate(data_ones)
    print(f"CRC for 32 ones (0xFF): {crc_ones:08x}") # Expected: 0xFF6CAB0B
    assert crc_ones == 0xFF6CAB0B

    # Test case 5: Incremental bytes
    data_inc = bytes(range(32))
    crc_inc = CRC32.calculate(data_inc)
    print(f"CRC for incremental bytes 0-31: {crc_inc:08x}") # Expected: 0x91267E8A
    assert crc_inc == 0x91267E8A

    # Test case 6: Offset and Length
    full_data = b"Hello, CRC32 World!"
    # CRC32 of "CRC32" part
    # "CRC32" is at offset 7, length 5
    # Expected CRC32("CRC32") = 0xF4DBDF21
    crc_partial = CRC32.calculate(full_data, offset=7, length=5)
    print(f"CRC for 'CRC32' (partial): {crc_partial:08x}")
    assert crc_partial == 0xF4DBDF21

    # Test case 7: Different Seed (initial value for CRC calculation)
    # Using seed=0 effectively means the initial CRC value is 0 before processing data.
    # The final XOR is still applied.
    # For "123456789", initial value 0, final XOR FFFFFFFF -> result should be 0x37655271
    crc_diff_seed = CRC32.calculate(data_123, seed=0x00000000)
    print(f"CRC for '123456789' with seed 0: {crc_diff_seed:08x}")
    assert crc_diff_seed == 0x37655271

    # Test case 8: compute_checksum_bytes
    bytes_output = CRC32.compute_checksum_bytes(data_123)
    expected_bytes_val = 0xCBF43926
    expected_bytes = expected_bytes_val.to_bytes(4, byteorder='little')
    print(f"CRC bytes for '123456789': {bytes_output.hex()}")
    assert bytes_output == expected_bytes

    # Test case 9: Ensure table is re-initialized if polynomial changes, and not if it's the same
    CRC32.calculate(b"test", polynomial=0x04C11DB7) # Different polynomial
    assert CRC32._last_polynomial_used == 0x04C11DB7
    table_ref_1 = CRC32._table
    CRC32.calculate(b"test2", polynomial=0x04C11DB7) # Same different polynomial
    assert CRC32._table is table_ref_1 # Should be the same table instance

    CRC32.calculate(b"test3") # Back to default polynomial
    assert CRC32._last_polynomial_used == CRC32.DefaultPolynomial
    assert CRC32._table is not table_ref_1 # Should be a new table instance

    print("CRC32 tests passed.")
