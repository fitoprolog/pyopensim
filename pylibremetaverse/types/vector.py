import math
import dataclasses

@dataclasses.dataclass(slots=True)
class Vector2:
    """A 2D vector with X and Y components."""
    X: float = 0.0
    Y: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}>"

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
        return Vector2(self.X * scalar, self.Y * scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
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
        """Returns a new normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            raise ValueError("Cannot normalize a zero vector.")
        return Vector2(self.X / mag, self.Y / mag)

Vector2.ZERO = Vector2(0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector3:
    """A 3D vector with X, Y, and Z components."""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}, {self.Z}>"

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

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.X * scalar, self.Y * scalar, self.Z * scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
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
        """Returns a new normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            # Changed to return a zero vector as per common practice,
            # rather than raising an error, to match potential C# behavior.
            return Vector3.ZERO
        return Vector3(self.X / mag, self.Y / mag, self.Z / mag)

Vector3.ZERO = Vector3(0.0, 0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector3d:
    """
    A 3D vector with double precision X, Y, and Z components.
    In Python, floats are typically double precision, so this is similar to Vector3
    but can be used for explicit type distinction or future enhancements.
    """
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}, {self.Z}>d"

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

    def __mul__(self, scalar: float) -> "Vector3d":
        return Vector3d(self.X * scalar, self.Y * scalar, self.Z * scalar)

    def __truediv__(self, scalar: float) -> "Vector3d":
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
        """Returns a new normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3d.ZERO # Return zero vector if magnitude is zero
        return Vector3d(self.X / mag, self.Y / mag, self.Z / mag)

Vector3d.ZERO = Vector3d(0.0, 0.0, 0.0)


@dataclasses.dataclass(slots=True)
class Vector4:
    """A 4D vector with X, Y, Z, and W components."""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    W: float = 0.0

    def __str__(self) -> str:
        return f"<{self.X}, {self.Y}, {self.Z}, {self.W}>"

    def __repr__(self) -> str:
        return f"Vector4(X={self.X}, Y={self.Y}, Z={self.Z}, W={self.W})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector4):
            return NotImplemented
        return self.X == other.X and self.Y == other.Y and self.Z == other.Z and self.W == other.W

    def __add__(self, other: "Vector4") -> "Vector4":
        if not isinstance(other, Vector4):
            return NotImplemented
        return Vector4(self.X + other.X, self.Y + other.Y, self.Z + other.Z, self.W + other.W)

    def __sub__(self, other: "Vector4") -> "Vector4":
        if not isinstance(other, Vector4):
            return NotImplemented
        return Vector4(self.X - other.X, self.Y - other.Y, self.Z - other.Z, self.W - other.W)

    def __mul__(self, scalar: float) -> "Vector4":
        return Vector4(self.X * scalar, self.Y * scalar, self.Z * scalar, self.W * scalar)

    def __truediv__(self, scalar: float) -> "Vector4":
        if scalar == 0:
            raise ValueError("Cannot divide by zero.")
        return Vector4(self.X / scalar, self.Y / scalar, self.Z / scalar, self.W / scalar)

    def magnitude_squared(self) -> float:
        """Returns the squared magnitude of the vector."""
        return self.X**2 + self.Y**2 + self.Z**2 + self.W**2

    def magnitude(self) -> float:
        """Returns the magnitude (length) of the vector."""
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Vector4":
        """Returns a new normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            # Consider returning Vector4.ZERO or raising error based on C# behavior
            return Vector4.ZERO
        return self / mag


Vector4.ZERO = Vector4(0.0, 0.0, 0.0, 0.0)
