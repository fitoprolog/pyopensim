import struct
import dataclasses # Use dataclasses directly
import math

@dataclasses.dataclass(slots=True)
class Color4:
    """
    Represents an RGBA color with float components ranging from 0.0 to 1.0.
    """
    R: float = 0.0
    G: float = 0.0
    B: float = 0.0
    A: float = 0.0 # Alpha component

    def __post_init__(self):
        # Clamp values to [0, 1] range during initialization and ensure they are floats
        self.R = max(0.0, min(1.0, float(self.R)))
        self.G = max(0.0, min(1.0, float(self.G)))
        self.B = max(0.0, min(1.0, float(self.B)))
        self.A = max(0.0, min(1.0, float(self.A)))

    def __str__(self) -> str:
        # Using format specifiers for consistency
        return f"<R={self.R:.3f}, G={self.G:.3f}, B={self.B:.3f}, A={self.A:.3f}>"

    def __repr__(self) -> str:
        return f"Color4(R={self.R}, G={self.G}, B={self.B}, A={self.A})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Color4):
            return NotImplemented
        # Using math.isclose for float comparisons
        return (math.isclose(self.R, other.R) and
                math.isclose(self.G, other.G) and
                math.isclose(self.B, other.B) and
                math.isclose(self.A, other.A))

    def get_bytes_rgba(self) -> bytes:
        """
        Returns the color as a 4-byte sequence (R, G, B, A).
        Each component is clamped to [0, 255] and converted to a byte.
        Floats are assumed to be in [0,1] due to __post_init__ clamping.
        """
        return bytes([
            int(self.R * 255),
            int(self.G * 255),
            int(self.B * 255),
            int(self.A * 255)
        ])

    @classmethod
    def from_bytes_rgba(cls, data: bytes, offset: int = 0) -> "Color4":
        """
        Creates a Color4 from a 4-byte sequence (R, G, B, A) starting at offset.
        Each byte component is converted to a float in [0.0, 1.0].
        """
        if len(data) - offset < 4:
            raise ValueError("Data must contain at least 4 bytes from offset.")
        # Using struct.unpack_from for consistency if offset is used.
        r_byte, g_byte, b_byte, a_byte = struct.unpack_from('BBBB', data, offset)
        return cls(r_byte / 255.0, g_byte / 255.0, b_byte / 255.0, a_byte / 255.0)

    @classmethod
    def from_bytes_rgb(cls, data: bytes, offset: int = 0) -> "Color4":
        """
        Creates a Color4 from a 3-byte sequence (R, G, B) starting at offset. Alpha is set to 1.0.
        Each byte component is converted to a float in [0.0, 1.0].
        """
        if len(data) - offset < 3:
            raise ValueError("Data must contain at least 3 bytes from offset.")
        r_byte, g_byte, b_byte = struct.unpack_from('BBB', data, offset)
        return cls(r_byte / 255.0, g_byte / 255.0, b_byte / 255.0, 1.0)


    def to_floats(self) -> tuple[float, float, float, float]:
        """Returns the color as a tuple of four floats (R, G, B, A)."""
        return (self.R, self.G, self.B, self.A)

    @staticmethod
    def from_floats(r: float, g: float, b: float, a: float = 1.0) -> "Color4":
        """Creates a Color4 from float components. Values will be clamped."""
        return Color4(r, g, b, a)

    # Predefined colors as static methods for flexibility (e.g., modifying alpha)
    @staticmethod
    def transparent(alpha: float = 0.0) -> "Color4": return Color4(0.0, 0.0, 0.0, alpha) # Default alpha 0
    @staticmethod
    def black(alpha: float = 1.0) -> "Color4": return Color4(0.0, 0.0, 0.0, alpha)
    @staticmethod
    def white(alpha: float = 1.0) -> "Color4": return Color4(1.0, 1.0, 1.0, alpha)
    @staticmethod
    def red(alpha: float = 1.0) -> "Color4": return Color4(1.0, 0.0, 0.0, alpha)
    @staticmethod
    def green(alpha: float = 1.0) -> "Color4": return Color4(0.0, 1.0, 0.0, alpha)
    @staticmethod
    def blue(alpha: float = 1.0) -> "Color4": return Color4(0.0, 0.0, 1.0, alpha)
    @staticmethod
    def yellow(alpha: float = 1.0) -> "Color4": return Color4(1.0, 1.0, 0.0, alpha)
    @staticmethod
    def magenta(alpha: float = 1.0) -> "Color4": return Color4(1.0, 0.0, 1.0, alpha)
    @staticmethod
    def cyan(alpha: float = 1.0) -> "Color4": return Color4(0.0, 1.0, 1.0, alpha)

if __name__ == '__main__':
    print("Color4 tests...")
    c1 = Color4(0.5, 0.25, 0.75, 1.0)
    print(f"c1: {c1}")

    c_black = Color4.black()
    print(f"Black: {c_black}")
    assert c_black == Color4(0,0,0,1)
    assert Color4.black(alpha=0.5) == Color4(0,0,0,0.5)


    c_white_bytes = Color4.white().get_bytes_rgba()
    print(f"White as bytes: {c_white_bytes.hex()}")
    assert c_white_bytes == b'\xff\xff\xff\xff'

    c_from_bytes_rgba = Color4.from_bytes_rgba(b'\x80\x40\xC0\xFF')
    print(f"From RGBA bytes: {c_from_bytes_rgba}")
    assert math.isclose(c_from_bytes_rgba.R, 128/255.0)
    assert math.isclose(c_from_bytes_rgba.G, 64/255.0)
    assert math.isclose(c_from_bytes_rgba.B, 192/255.0)
    assert math.isclose(c_from_bytes_rgba.A, 1.0)

    c_from_bytes_rgb = Color4.from_bytes_rgb(b'\x80\x40\xC0')
    print(f"From RGB bytes: {c_from_bytes_rgb}")
    assert math.isclose(c_from_bytes_rgb.R, 128/255.0)
    assert math.isclose(c_from_bytes_rgb.A, 1.0)

    c_overflow = Color4(1.5, -0.5, 0.5, 255.0) # 255.0 will be clamped to 1.0 by __post_init__
    print(f"Overflow test raw input R=1.5, G=-0.5, B=0.5, A=255.0 -> Clamped: {c_overflow}")
    assert c_overflow == Color4(1.0, 0.0, 0.5, 1.0)

    c_eq1 = Color4(0.1, 0.2, 0.3, 0.4)
    c_eq2 = Color4(0.10000000001, 0.20000000001, 0.30000000001, 0.40000000001) # within math.isclose default tolerance
    assert c_eq1 == c_eq2

    c_neq_bigger = Color4(0.1, 0.2, 0.31, 0.4)
    assert not (c_eq1 == c_neq_bigger)

    floats_tuple = c1.to_floats()
    assert floats_tuple == (0.5, 0.25, 0.75, 1.0)
    c_from_f = Color4.from_floats(*floats_tuple)
    assert c_from_f == c1

    print("Color4 tests passed.")
