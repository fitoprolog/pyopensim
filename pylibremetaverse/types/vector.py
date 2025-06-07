import math
import struct
import dataclasses

@dataclasses.dataclass(slots=True)
class Vector2:
    """A 2D vector with X and Y components."""
    X: float = 0.0
    Y: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X:.2f}, {self.Y:.2f}>" # Added formatting

    def __repr__(self) -> str:
        return f"Vector2(X={self.X}, Y={self.Y})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y

    def __add__(self, other: "Vector2") -> "Vector2":
        if not isinstance(other, Vector2):
            return NotImplemented
        return Vector2(self.X + other.X, self.Y + other.Y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        if not isinstance(other, Vector2):
            return NotImplemented
        return Vector2(self.X - other.X, self.Y - other.Y)

    def __mul__(self, scalar: float) -> "Vector2":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2(self.X * scalar, self.Y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ValueError("Cannot divide by zero.")
        return Vector2(self.X / scalar, self.Y / scalar)

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the vector."""
        return self.X * self.X + self.Y * self.Y

    def magnitude(self) -> float:
        """Returns the magnitude (length) of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Vector2":
        """Returns a new normalized vector. Returns Vector2.ZERO if magnitude is zero."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2.ZERO
        return Vector2(self.X / mag, self.Y / mag)

Vector2.ZERO = Vector2(0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector3:
    """A 3D vector with X, Y, and Z components."""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X:.2f}, {self.Y:.2f}, {self.Z:.2f}>" # Added formatting

    def __repr__(self) -> str:
        return f"Vector3(X={self.X}, Y={self.Y}, Z={self.Z})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y and self.Z == other.Z

    def __add__(self, other: "Vector3") -> "Vector3":
        if not isinstance(other, Vector3):
            return NotImplemented
        return Vector3(self.X + other.X, self.Y + other.Y, self.Z + other.Z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        if not isinstance(other, Vector3):
            return NotImplemented
        return Vector3(self.X - other.X, self.Y - other.Y, self.Z - other.Z)

    def __mul__(self, scalar: float) -> "Vector3": # Changed to only scalar multiplication
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector3(self.X * scalar, self.Y * scalar, self.Z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ValueError("Cannot divide by zero.")
        return Vector3(self.X / scalar, self.Y / scalar, self.Z / scalar)

    def dot(self, other: "Vector3") -> float:
        """Calculates the dot product with another Vector3."""
        if not isinstance(other, Vector3):
            raise TypeError("Can only calculate dot product with another Vector3.")
        return self.X * other.X + self.Y * other.Y + self.Z * other.Z

    def cross(self, other: "Vector3") -> "Vector3":
        """Calculates the cross product with another Vector3."""
        if not isinstance(other, Vector3):
            raise TypeError("Can only calculate cross product with another Vector3.")
        return Vector3(
            self.Y * other.Z - self.Z * other.Y,
            self.Z * other.X - self.X * other.Z,
            self.X * other.Y - self.Y * other.X,
        )

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the vector."""
        return self.X * self.X + self.Y * self.Y + self.Z * self.Z

    def magnitude(self) -> float:
        """Returns the magnitude (length) of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Vector3":
        """Returns a new normalized vector. Returns Vector3.ZERO if magnitude is zero."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3.ZERO
        return Vector3(self.X / mag, self.Y / mag, self.Z / mag)

    def to_bytes(self) -> bytes:
        """Packs the vector into bytes (12 bytes, 3 floats little-endian)."""
        return struct.pack('<fff', self.X, self.Y, self.Z)

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'Vector3':
        """Unpacks a vector from bytes (12 bytes, 3 floats little-endian)."""
        if len(data) - offset < 12:
            raise ValueError("Not enough bytes to unpack Vector3. Need 12.")
        x, y, z = struct.unpack_from('<fff', data, offset)
        return Vector3(x, y, z)

Vector3.ZERO = Vector3(0.0, 0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector3d:
    """
    A 3D vector with double precision X, Y, and Z components.
    In Python, floats are typically double precision (64-bit IEEE 754).
    """
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}, {self.Z}>d" # Standard formatting, d for clarity

    def __repr__(self) -> str:
        return f"Vector3d(X={self.X}, Y={self.Y}, Z={self.Z})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector3d):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y and self.Z == other.Z

    def __add__(self, other: "Vector3d") -> "Vector3d":
        if not isinstance(other, Vector3d):
            return NotImplemented
        return Vector3d(self.X + other.X, self.Y + other.Y, self.Z + other.Z)

    def __sub__(self, other: "Vector3d") -> "Vector3d":
        if not isinstance(other, Vector3d):
            return NotImplemented
        return Vector3d(self.X - other.X, self.Y - other.Y, self.Z - other.Z)

    def __mul__(self, scalar: float) -> "Vector3d": # Changed to only scalar multiplication
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector3d(self.X * scalar, self.Y * scalar, self.Z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3d":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector3d":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ValueError("Cannot divide by zero.")
        return Vector3d(self.X / scalar, self.Y / scalar, self.Z / scalar)

    def dot(self, other: "Vector3d") -> float:
        """Calculates the dot product with another Vector3d."""
        if not isinstance(other, Vector3d):
            raise TypeError("Can only calculate dot product with another Vector3d.")
        return self.X * other.X + self.Y * other.Y + self.Z * other.Z

    def cross(self, other: "Vector3d") -> "Vector3d":
        """Calculates the cross product with another Vector3d."""
        if not isinstance(other, Vector3d):
            raise TypeError("Can only calculate cross product with another Vector3d.")
        return Vector3d(
            self.Y * other.Z - self.Z * other.Y,
            self.Z * other.X - self.X * other.Z,
            self.X * other.Y - self.Y * other.X,
        )

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the vector."""
        return self.X * self.X + self.Y * self.Y + self.Z * self.Z

    def magnitude(self) -> float:
        """Returns the magnitude (length) of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Vector3d":
        """Returns a new normalized vector. Returns Vector3d.ZERO if magnitude is zero."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3d.ZERO
        return Vector3d(self.X / mag, self.Y / mag, self.Z / mag)

    def to_bytes(self) -> bytes:
        """Packs the vector into bytes (24 bytes, 3 doubles little-endian)."""
        return struct.pack('<ddd', self.X, self.Y, self.Z)

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'Vector3d':
        """Unpacks a double precision vector from bytes (24 bytes, 3 doubles little-endian)."""
        if len(data) - offset < 24:
            raise ValueError("Not enough bytes to unpack Vector3d. Need 24.")
        x, y, z = struct.unpack_from('<ddd', data, offset)
        return Vector3d(x, y, z)

Vector3d.ZERO = Vector3d(0.0, 0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector4:
    """A 4D vector with X, Y, Z, and W components."""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    W: float = 0.0 # Changed from S to W for general consistency

    def __str__(self) -> str:
        return f"<{self.X:.2f}, {self.Y:.2f}, {self.Z:.2f}, {self.W:.2f}>" # Added formatting, W

    def __repr__(self) -> str:
        return f"Vector4(X={self.X}, Y={self.Y}, Z={self.Z}, W={self.W})" # W

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector4):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y and self.Z == other.Z and self.W == other.W # W

    def __add__(self, other: "Vector4") -> "Vector4":
        if not isinstance(other, Vector4):
            return NotImplemented
        return Vector4(self.X + other.X, self.Y + other.Y, self.Z + other.Z, self.W + other.W) # W

    def __sub__(self, other: "Vector4") -> "Vector4":
        if not isinstance(other, Vector4):
            return NotImplemented
        return Vector4(self.X - other.X, self.Y - other.Y, self.Z - other.Z, self.W - other.W) # W

    def __mul__(self, scalar: float) -> "Vector4":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector4(self.X * scalar, self.Y * scalar, self.Z * scalar, self.W * scalar) # W

    def __rmul__(self, scalar: float) -> "Vector4":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector4":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ValueError("Cannot divide by zero.")
        return Vector4(self.X / scalar, self.Y / scalar, self.Z / scalar, self.W / scalar) # W

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the vector."""
        return self.X**2 + self.Y**2 + self.Z**2 + self.W**2 # W

    def magnitude(self) -> float:
        """Returns the magnitude (length) of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Vector4":
        """Returns a new normalized vector. Returns Vector4.ZERO if magnitude is zero."""
        mag = self.magnitude()
        if mag == 0:
            return Vector4.ZERO
        # Using __truediv__ for consistency if it's defined for scalar division
        return Vector4(self.X / mag, self.Y / mag, self.Z / mag, self.W / mag) # W

    def to_bytes(self) -> bytes:
        """Packs the vector into bytes (16 bytes, 4 floats little-endian)."""
        return struct.pack('<ffff', self.X, self.Y, self.Z, self.W) # W

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'Vector4':
        """Unpacks a vector from bytes (16 bytes, 4 floats little-endian)."""
        if len(data) - offset < 16:
            raise ValueError("Not enough bytes to unpack Vector4. Need 16.")
        x, y, z, w = struct.unpack_from('<ffff', data, offset) # w
        return Vector4(x, y, z, w) # w

Vector4.ZERO = Vector4(0.0, 0.0, 0.0, 0.0)

if __name__ == '__main__':
    # Test cases from my draft + existing file combined
    v2a = Vector2(1, 2)
    v2b = Vector2(3, 4)
    print(f"v2a + v2b = {v2a + v2b}")
    print(f"v2a.magnitude() = {v2a.magnitude()}")
    assert (v2a + v2b) == Vector2(4,6)
    assert v2a.normalize().magnitude() == 1.0 or v2a.normalize().magnitude() == 0.0
    assert Vector2.ZERO.normalize() == Vector2.ZERO

    v3a = Vector3(1, 2, 3)
    v3b = Vector3(4, 5, 6)
    print(f"v3a + v3b = {v3a + v3b}")
    print(f"v3a * 2 = {v3a * 2}")
    print(f"v3a dot v3b = {v3a.dot(v3b)}")
    print(f"v3a x v3b = {v3a.cross(v3b)}")
    print(f"v3a.magnitude() = {v3a.magnitude()}")
    v3norm = v3a.normalize()
    print(f"v3a normalized = {v3norm}, magnitude = {v3norm.magnitude()}")
    assert v3norm.magnitude() == 1.0 or v3norm.magnitude() == 0.0
    assert Vector3.ZERO.normalize() == Vector3.ZERO

    v3_bytes = v3a.to_bytes()
    print(f"v3a as bytes: {v3_bytes.hex()}")
    v3_from_bytes = Vector3.from_bytes(v3_bytes)
    print(f"v3a from bytes: {v3_from_bytes}")
    assert v3a == v3_from_bytes

    v3d = Vector3d(1.0, 2.0, 3.0)
    print(f"v3d: {v3d}")
    v3d_bytes = v3d.to_bytes()
    print(f"v3d as bytes: {v3d_bytes.hex()}")
    v3d_from_bytes = Vector3d.from_bytes(v3d_bytes)
    print(f"v3d from bytes: {v3d_from_bytes}")
    assert v3d == v3d_from_bytes
    assert Vector3d.ZERO.normalize() == Vector3d.ZERO

    v4a = Vector4(1,2,3,4)
    print(f"v4a: {v4a}")
    v4_bytes = v4a.to_bytes()
    print(f"v4a as bytes: {v4_bytes.hex()}")
    v4_from_bytes = Vector4.from_bytes(v4_bytes)
    print(f"v4a from bytes: {v4_from_bytes}")
    assert v4a == v4_from_bytes
    v4norm = v4a.normalize()
    # Check that magnitude is close to 1.0, allowing for floating point inaccuracies
    assert abs(v4norm.magnitude() - 1.0) < 1e-9 or v4norm.magnitude() == 0.0
    assert Vector4.ZERO.normalize() == Vector4.ZERO


    # Test __rmul__
    v3c = 2 * Vector3(1,2,3)
    assert v3c == Vector3(2,4,6)
    print(f"2 * v3a = {v3c}")


    print("Combined Vector tests completed.")
