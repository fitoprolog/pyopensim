import math
import dataclasses

@dataclasses.dataclass(slots=True)
class Quaternion:
    """A quaternion class for representing rotations."""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    W: float = 1.0  # Default to identity

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}, {self.Z}, {self.W}>"

    def __repr__(self) -> str:
        return f"Quaternion(X={self.X}, Y={self.Y}, Z={self.Z}, W={self.W})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y and self.Z == other.Z and self.W == other.W

    def __add__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            return NotImplemented
        return Quaternion(self.X + other.X, self.Y + other.Y, self.Z + other.Z, self.W + other.W)

    def __sub__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            return NotImplemented
        return Quaternion(self.X - other.X, self.Y - other.Y, self.Z - other.Z, self.W - other.W)

    def __mul__(self, other):
        if isinstance(other, (int, float)): # Scalar multiplication
            return Quaternion(self.X * other, self.Y * other, self.Z * other, self.W * other)
        elif isinstance(other, Quaternion): # Quaternion multiplication
            # q1 * q2 = (w1w2 - x1x2 - y1y2 - z1z2) +
            #           (w1x2 + x1w2 + y1z2 - z1y2)i +
            #           (w1y2 - x1z2 + y1w2 + z1x2)j +
            #           (w1z2 + x1y2 - y1x2 + z1w2)k
            w = self.W * other.W - self.X * other.X - self.Y * other.Y - self.Z * other.Z
            x = self.W * other.X + self.X * other.W + self.Y * other.Z - self.Z * other.Y
            y = self.W * other.Y - self.X * other.Z + self.Y * other.W + self.Z * other.X
            z = self.W * other.Z + self.X * other.Y - self.Y * other.X + self.Z * other.W
            return Quaternion(x, y, z, w)
        else:
            return NotImplemented

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the quaternion."""
        return self.X**2 + self.Y**2 + self.Z**2 + self.W**2

    def magnitude(self) -> float:
        """Returns the magnitude of the quaternion."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Quaternion":
        """Returns a new normalized quaternion."""
        mag = self.magnitude()
        if mag == 0.0:
            # Should this raise an error or return identity/zero?
            # C# behavior often returns identity for zero-length quaternion normalization.
            return Quaternion.Identity
        return Quaternion(self.X / mag, self.Y / mag, self.Z / mag, self.W / mag)

    def conjugate(self) -> "Quaternion":
        """Returns the conjugate of the quaternion."""
        return Quaternion(-self.X, -self.Y, -self.Z, self.W)

    # Conversion methods (to/from Euler, rotation matrix) can be added later
    # based on specific requirements or C# equivalent features.

Quaternion.Identity = Quaternion(0.0, 0.0, 0.0, 1.0)
Quaternion.ZERO = Quaternion(0.0, 0.0, 0.0, 0.0) # Often useful
