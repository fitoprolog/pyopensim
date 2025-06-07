import math
import struct
from dataclasses import dataclass
# Ensure Vector3 is available for type hinting and use.
# It should be in the same directory.
from .vector import Vector3


@dataclass(slots=True)
class Quaternion:
    """
    A quaternion representation (X, Y, Z, W).
    W is the scalar component.
    """
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    W: float = 1.0 # Identity quaternion by default

    def __str__(self) -> str:
        return f"<{self.X:.3f}, {self.Y:.3f}, {self.Z:.3f}, {self.W:.3f}>" # Added formatting

    def __repr__(self) -> str:
        return f"Quaternion(X={self.X}, Y={self.Y}, Z={self.Z}, W={self.W})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        # Add tolerance for float comparisons? For now, exact.
        return self.X == other.X and self.Y == other.Y and \
               self.Z == other.Z and self.W == other.W

    @staticmethod
    def identity():
        return Quaternion(0.0, 0.0, 0.0, 1.0)

    def is_identity(self, tolerance: float = 1e-6) -> bool:
        """Checks if the quaternion is close to the identity quaternion."""
        return abs(self.X) < tolerance and \
               abs(self.Y) < tolerance and \
               abs(self.Z) < tolerance and \
               abs(self.W - 1.0) < tolerance

    def magnitude_squared(self) -> float:
        return self.X**2 + self.Y**2 + self.Z**2 + self.W**2

    def magnitude(self) -> float:
        return math.sqrt(self.magnitude_squared())

    def normalize(self) -> "Quaternion":
        """
        Returns a new normalized quaternion.
        Returns Quaternion.identity() if magnitude is very close to zero.
        """
        mag = self.magnitude()
        if mag < 1e-9: # Tolerance for zero magnitude
            return Quaternion.identity()
        return Quaternion(self.X / mag, self.Y / mag, self.Z / mag, self.W / mag)

    def __add__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            return NotImplemented
        return Quaternion(self.X + other.X, self.Y + other.Y, self.Z + other.Z, self.W + other.W)

    def __sub__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            return NotImplemented
        return Quaternion(self.X - other.X, self.Y - other.Y, self.Z - other.Z, self.W - other.W)

    def __mul__(self, other):
        if isinstance(other, Quaternion): # Quaternion multiplication
            # self = q1 (X,Y,Z,W), other = q2 (X,Y,Z,W)
            # Store components for clarity
            x1, y1, z1, w1 = self.X, self.Y, self.Z, self.W
            x2, y2, z2, w2 = other.X, other.Y, other.Z, other.W

            # Formula from standard quaternion multiplication
            new_W = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
            new_X = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
            new_Y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
            new_Z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
            return Quaternion(new_X, new_Y, new_Z, new_W)
        elif isinstance(other, (int, float)): # Scalar multiplication
            return Quaternion(self.X * other, self.Y * other, self.Z * other, self.W * other)
        return NotImplemented

    def __rmul__(self, scalar): # Handles scalar * Quaternion
        if isinstance(scalar, (int, float)):
            return self.__mul__(scalar)
        return NotImplemented

    def conjugate(self) -> "Quaternion":
        """Returns the conjugate of this quaternion."""
        return Quaternion(-self.X, -self.Y, -self.Z, self.W)

    def inverse(self) -> "Quaternion":
        """
        Returns the inverse of this quaternion.
        For unit quaternions, inverse is the conjugate.
        Otherwise, it's conjugate / magnitude_squared.
        """
        mag_sq = self.magnitude_squared()
        if mag_sq < 1e-9: # Tolerance for zero magnitude
            # Or raise error; C# equivalent might throw or return identity
            return Quaternion.identity()

        conj = self.conjugate()
        return Quaternion(conj.X / mag_sq, conj.Y / mag_sq, conj.Z / mag_sq, conj.W / mag_sq)

    @staticmethod
    def from_axis_angle(axis: Vector3, angle_rad: float) -> "Quaternion":
        """Creates a quaternion from an axis and an angle in radians."""
        # Ensure axis is a Vector3 instance
        if not isinstance(axis, Vector3):
            raise TypeError("Axis must be a Vector3 instance.")

        norm_axis = axis.normalize()
        half_angle = angle_rad / 2.0
        s = math.sin(half_angle)
        return Quaternion(
            norm_axis.X * s,
            norm_axis.Y * s,
            norm_axis.Z * s,
            math.cos(half_angle)
        )

    def to_axis_angle(self) -> tuple[Vector3, float]:
        """
        Converts this quaternion to an axis-angle representation.
        Returns (Vector3, float_radians).
        """
        q = self
        # It's safer to normalize the quaternion before conversion
        # if it's not guaranteed to be a unit quaternion.
        if abs(q.magnitude_squared() - 1.0) > 1e-6: # Tolerance for non-unit
             q = q.normalize()

        # Prevent domain errors for acos if W is slightly out of [-1, 1] due to precision
        w_clamped = max(-1.0, min(1.0, q.W))
        angle_rad = 2.0 * math.acos(w_clamped)

        s_squared = 1.0 - w_clamped * w_clamped

        if s_squared < 1e-9: # If s is close to zero, W is 1 or -1 (angle is 0 or 2pi)
            # Axis is arbitrary for a zero rotation, conventionally (1,0,0) or (0,0,1)
            axis_x = 1.0
            axis_y = 0.0
            axis_z = 0.0
        else:
            s = math.sqrt(s_squared)
            axis_x = q.X / s
            axis_y = q.Y / s
            axis_z = q.Z / s

        return Vector3(axis_x, axis_y, axis_z), angle_rad

    def to_euler_angles(self) -> Vector3: # Returns Vector3(roll, pitch, yaw)
        """
        Converts this quaternion to Euler angles (roll, pitch, yaw) in radians.
        Order: ZYX (yaw, pitch, roll) - common for aerospace and Unity.
        This implementation matches many standard libraries.
        Note: Euler angle conversions can have singularities (gimbal lock).
        """
        # Ensure quaternion is normalized for stability
        q = self.normalize()
        x, y, z, w = q.X, q.Y, q.Z, q.W

        # Roll (X-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        # Pitch (Y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp) # Use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)

        # Yaw (Z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return Vector3(roll, pitch, yaw)

    @staticmethod
    def from_euler_angles(roll: float, pitch: float, yaw: float) -> "Quaternion": # roll, pitch, yaw in radians
        """
        Creates a quaternion from Euler angles (roll, pitch, yaw) in radians.
        Assumes ZYX rotation order (yaw around Z, then pitch around new Y, then roll around new X).
        """
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy

        return Quaternion(x, y, z, w)

    def to_bytes(self) -> bytes:
        """Packs the quaternion into bytes (16 bytes, 4 floats little-endian: X, Y, Z, W)."""
        return struct.pack('<ffff', self.X, self.Y, self.Z, self.W)

    @staticmethod
    def from_bytes(data: bytes, offset: int = 0) -> 'Quaternion':
        """Unpacks a quaternion from bytes (16 bytes, 4 floats little-endian: X, Y, Z, W)."""
        if len(data) - offset < 16:
            raise ValueError("Not enough bytes to unpack Quaternion. Need 16.")
        x, y, z, w = struct.unpack_from('<ffff', data, offset)
        return Quaternion(x, y, z, w)

Quaternion.ZERO = Quaternion(0.0, 0.0, 0.0, 0.0) # Added for completeness

# Example Usage & Basic Tests (from my draft, slightly expanded)
if __name__ == '__main__':
    q_id = Quaternion.identity()
    print(f"Identity Quaternion: {q_id}")
    assert q_id.is_identity()
    assert Quaternion.ZERO.magnitude() == 0.0

    q1_orig = Quaternion(0.1, 0.2, 0.3, 0.9)
    q1 = q1_orig.normalize() # Work with normalized for most tests

    # Test axis-angle for a known rotation
    # 90 degrees (pi/2 radians) around X-axis
    angle_rad_90x = math.pi / 2
    q2 = Quaternion.from_axis_angle(Vector3(1,0,0), angle_rad_90x)
    print(f"q2 (90deg around X): {q2}")
    expected_q2_x = math.sin(angle_rad_90x / 2)
    expected_q2_w = math.cos(angle_rad_90x / 2)
    assert abs(q2.X - expected_q2_x) < 1e-6 and abs(q2.Y) < 1e-6 and \
           abs(q2.Z) < 1e-6 and abs(q2.W - expected_q2_w) < 1e-6

    # Test multiplication
    q_mul_q = q1 * q2
    print(f"q1 * q2: {q_mul_q}")

    q_mul_scalar = q1_orig * 2.0 # Use original for scalar mult test
    print(f"q1_orig * 2.0: {q_mul_scalar}")
    assert q_mul_scalar == Quaternion(q1_orig.X*2, q1_orig.Y*2, q1_orig.Z*2, q1_orig.W*2)
    q_rmul_scalar = 2.0 * q1_orig
    assert q_rmul_scalar == q_mul_scalar

    # Test conjugate and inverse (for normalized quaternion, they should be same)
    q1_conj = q1.conjugate()
    q1_inv = q1.inverse()
    print(f"q1 conjugate: {q1_conj}")
    print(f"q1 inverse: {q1_inv}")
    assert abs((q1_conj * q1).W - 1.0) < 1e-6 # q_conj * q should be identity for normalized q
    assert abs((q1_inv * q1).W - 1.0) < 1e-6  # q_inv * q should be identity

    # Test axis-angle conversion (q2 was 90 deg around X)
    axis, angle = q2.to_axis_angle()
    print(f"q2 to_axis_angle: Axis={axis}, Angle={angle:.3f} rad ({math.degrees(angle):.1f} deg)")
    assert abs(axis.X - 1.0) < 1e-6 and abs(axis.Y) < 1e-6 and abs(axis.Z) < 1e-6
    assert abs(angle - angle_rad_90x) < 1e-6

    # Test Euler angles
    q_euler_test = Quaternion.from_euler_angles(math.radians(30), math.radians(60), math.radians(90)) # R, P, Y
    print(f"Quaternion from Euler(30,60,90 deg): {q_euler_test}")
    euler_angles_vec = q_euler_test.to_euler_angles()
    print(f"q_euler_test to Euler: Roll={math.degrees(euler_angles_vec.X):.1f}, Pitch={math.degrees(euler_angles_vec.Y):.1f}, Yaw={math.degrees(euler_angles_vec.Z):.1f}")
    assert abs(euler_angles_vec.X - math.radians(30)) < 1e-6
    assert abs(euler_angles_vec.Y - math.radians(60)) < 1e-6
    assert abs(euler_angles_vec.Z - math.radians(90)) < 1e-6

    # Test normalization of zero magnitude quaternion
    q_zero_mag = Quaternion(0,0,0,0)
    print(f"Zero magnitude quaternion: {q_zero_mag}")
    q_zero_norm = q_zero_mag.normalize()
    print(f"Normalized zero magnitude quaternion: {q_zero_norm}")
    assert q_zero_norm.is_identity()

    # Test byte packing
    q_bytes = q1.to_bytes()
    print(f"q1 as bytes: {q_bytes.hex()}")
    q_from_bytes = Quaternion.from_bytes(q_bytes)
    print(f"q1 from bytes: {q_from_bytes}")
    assert q1 == q_from_bytes

    # Test inverse of non-normalized quaternion
    q_non_norm = Quaternion(1,2,3,4)
    q_non_norm_inv = q_non_norm.inverse()
    q_identity_check = q_non_norm * q_non_norm_inv
    print(f"Non-normalized q: {q_non_norm}")
    print(f"Inverse of non-normalized q: {q_non_norm_inv}")
    print(f"q_non_norm * q_non_norm_inv: {q_identity_check}")
    assert q_identity_check.is_identity(tolerance=1e-5) # Allow slightly larger tolerance

    print("Quaternion tests completed.")
