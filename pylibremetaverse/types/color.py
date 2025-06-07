import dataclasses
import struct

@dataclasses.dataclass(slots=True)
class Color4:
    """
    A color class with Red, Green, Blue, and Alpha components.
    Components are typically floats in the range [0.0, 1.0].
    """
    R: float = 0.0
    G: float = 0.0
    B: float = 0.0
    A: float = 0.0 # Alpha = 0.0 means fully transparent, Alpha = 1.0 means fully opaque

    def __str__(self) -> str:
        return f"R:{self.R:.3f} G:{self.G:.3f} B:{self.B:.3f} A:{self.A:.3f}"

    def __repr__(self) -> str:
        return f"Color4(R={self.R}, G={self.G}, B={self.B}, A={self.A})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Color4):
            return NotImplemented
        # Using math.isclose for float comparisons might be better for some applications
        return self.R == other.R and self.G == other.G and self.B == other.B and self.A == other.A

    def get_bytes_rgba(self) -> bytes:
        """
        Returns the color as a 4-byte sequence (R, G, B, A).
        Each component is clamped to [0, 255] and converted to a byte.
        """
        r_byte = max(0, min(255, int(self.R * 255)))
        g_byte = max(0, min(255, int(self.G * 255)))
        b_byte = max(0, min(255, int(self.B * 255)))
        a_byte = max(0, min(255, int(self.A * 255)))
        return struct.pack('BBBB', r_byte, g_byte, b_byte, a_byte)

    @classmethod
    def from_bytes_rgba(cls, data: bytes) -> "Color4":
        """
        Creates a Color4 from a 4-byte sequence (R, G, B, A).
        Each byte component is converted to a float in [0.0, 1.0].
        """
        if len(data) != 4:
            raise ValueError("Data must be 4 bytes long.")
        r, g, b, a = struct.unpack('BBBB', data)
        return cls(r / 255.0, g / 255.0, b / 255.0, a / 255.0)

    # Common color constants
    Transparent: "Color4"
    Black: "Color4"
    White: "Color4"
    Red: "Color4"
    Green: "Color4"
    Blue: "Color4"

# Define constants after class definition to use the class itself
Color4.Transparent = Color4(0.0, 0.0, 0.0, 0.0)
Color4.Black = Color4(0.0, 0.0, 0.0, 1.0)
Color4.White = Color4(1.0, 1.0, 1.0, 1.0)
Color4.Red = Color4(1.0, 0.0, 0.0, 1.0)
Color4.Green = Color4(0.0, 1.0, 0.0, 1.0)
Color4.Blue = Color4(0.0, 0.0, 1.0, 1.0)
