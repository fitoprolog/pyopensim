import math
import dataclasses
from .vector import Vector3, Vector4 # Assuming vector.py is in the same directory
from .quaternion import Quaternion # Assuming quaternion.py is in the same directory

# Using a flat list for 16 elements (M11, M12, ..., M44)
# Row-major or column-major? C# XNA/MonoGame is row-major.
# Unity is column-major. Assuming row-major for now, like XNA.
# M11, M12, M13, M14 (first row)
# M21, M22, M23, M24 (second row)
# ...

@dataclasses.dataclass(slots=True)
class Matrix4:
    """
    A 4x4 matrix class, typically used for transformations.
    Values are stored in row-major order:
    M11, M12, M13, M14,
    M21, M22, M23, M24,
    M31, M32, M33, M34,
    M41, M42, M43, M44
    """
    # Initialize with identity matrix elements by default
    M11: float = 1.0; M12: float = 0.0; M13: float = 0.0; M14: float = 0.0
    M21: float = 0.0; M22: float = 1.0; M23: float = 0.0; M24: float = 0.0
    M31: float = 0.0; M32: float = 0.0; M33: float = 1.0; M34: float = 0.0
    M41: float = 0.0; M42: float = 0.0; M43: float = 0.0; M44: float = 1.0

    def __post_init__(self):
        # Ensure all elements are floats, in case integers were passed.
        self.M11, self.M12, self.M13, self.M14 = float(self.M11), float(self.M12), float(self.M13), float(self.M14)
        self.M21, self.M22, self.M23, self.M24 = float(self.M21), float(self.M22), float(self.M23), float(self.M24)
        self.M31, self.M32, self.M33, self.M34 = float(self.M31), float(self.M32), float(self.M33), float(self.M34)
        self.M41, self.M42, self.M43, self.M44 = float(self.M41), float(self.M42), float(self.M43), float(self.M44)

    @classmethod
    def from_list(cls, elements: list[float]) -> "Matrix4":
        """Creates a Matrix4 from a list of 16 floats (row-major)."""
        if len(elements) != 16:
            raise ValueError("List must contain 16 elements.")
        return cls(*elements)

    def to_list(self) -> list[float]:
        """Returns the matrix elements as a list of 16 floats (row-major)."""
        return [
            self.M11, self.M12, self.M13, self.M14,
            self.M21, self.M22, self.M23, self.M24,
            self.M31, self.M32, self.M33, self.M34,
            self.M41, self.M42, self.M43, self.M44,
        ]

    def __str__(self) -> str:
        return (f"[[{self.M11}, {self.M12}, {self.M13}, {self.M14}],\n"
                f" [{self.M21}, {self.M22}, {self.M23}, {self.M24}],\n"
                f" [{self.M31}, {self.M32}, {self.M33}, {self.M34}],\n"
                f" [{self.M41}, {self.M42}, {self.M43}, {self.M44}]]")

    def __repr__(self) -> str:
        return (f"Matrix4(M11={self.M11}, M12={self.M12}, M13={self.M13}, M14={self.M14}, "
                f"M21={self.M21}, M22={self.M22}, M23={self.M23}, M24={self.M24}, "
                f"M31={self.M31}, M32={self.M32}, M33={self.M33}, M34={self.M34}, "
                f"M41={self.M41}, M42={self.M42}, M43={self.M43}, M44={self.M44})")

    def __eq__(self, other) -> bool:
        if not isinstance(other, Matrix4):
            return NotImplemented
        return self.to_list() == other.to_list()

    def __mul__(self, other):
        if isinstance(other, Matrix4):
            # Matrix multiplication
            m = [0.0] * 16
            # Row 1
            m[0] = self.M11*other.M11 + self.M12*other.M21 + self.M13*other.M31 + self.M14*other.M41
            m[1] = self.M11*other.M12 + self.M12*other.M22 + self.M13*other.M32 + self.M14*other.M42
            m[2] = self.M11*other.M13 + self.M12*other.M23 + self.M13*other.M33 + self.M14*other.M43
            m[3] = self.M11*other.M14 + self.M12*other.M24 + self.M13*other.M34 + self.M14*other.M44
            # Row 2
            m[4] = self.M21*other.M11 + self.M22*other.M21 + self.M23*other.M31 + self.M24*other.M41
            m[5] = self.M21*other.M12 + self.M22*other.M22 + self.M23*other.M32 + self.M24*other.M42
            m[6] = self.M21*other.M13 + self.M22*other.M23 + self.M23*other.M33 + self.M24*other.M43
            m[7] = self.M21*other.M14 + self.M22*other.M24 + self.M23*other.M34 + self.M24*other.M44
            # Row 3
            m[8] = self.M31*other.M11 + self.M32*other.M21 + self.M33*other.M31 + self.M34*other.M41
            m[9] = self.M31*other.M12 + self.M32*other.M22 + self.M33*other.M32 + self.M34*other.M42
            m[10]= self.M31*other.M13 + self.M32*other.M23 + self.M33*other.M33 + self.M34*other.M43
            m[11]= self.M31*other.M14 + self.M32*other.M24 + self.M33*other.M34 + self.M34*other.M44
            # Row 4
            m[12]= self.M41*other.M11 + self.M42*other.M21 + self.M43*other.M31 + self.M44*other.M41
            m[13]= self.M41*other.M12 + self.M42*other.M22 + self.M43*other.M32 + self.M44*other.M42
            m[14]= self.M41*other.M13 + self.M42*other.M23 + self.M43*other.M33 + self.M44*other.M43
            m[15]= self.M41*other.M14 + self.M42*other.M24 + self.M43*other.M34 + self.M44*other.M44
            return Matrix4.from_list(m)
        elif isinstance(other, Vector4): # Transform Vector4
            x = self.M11*other.X + self.M12*other.Y + self.M13*other.Z + self.M14*other.W
            y = self.M21*other.X + self.M22*other.Y + self.M23*other.Z + self.M24*other.W
            z = self.M31*other.X + self.M32*other.Y + self.M33*other.Z + self.M34*other.W
            w = self.M41*other.X + self.M42*other.Y + self.M43*other.Z + self.M44*other.W
            return Vector4(x,y,z,w)
        # Add Vector3 multiplication (implicitly W=1 for position, W=0 for direction) later if needed
        return NotImplemented

    def determinant(self) -> float:
        """Calculates the determinant of the matrix."""
        # This is a complex calculation, often not needed directly if inverse is available.
        # Using the formula for determinant of a 4x4 matrix (expansion by minors)
        # For brevity, this might be simplified or rely on a library if precision is critical.
        # A direct implementation:
        t0 = self.M31 * self.M42 - self.M32 * self.M41
        t1 = self.M31 * self.M43 - self.M33 * self.M41
        t2 = self.M31 * self.M44 - self.M34 * self.M41
        t3 = self.M32 * self.M43 - self.M33 * self.M42
        t4 = self.M32 * self.M44 - self.M34 * self.M42
        t5 = self.M33 * self.M44 - self.M34 * self.M43

        d0 = self.M21 * t5 - self.M22 * t2 + self.M23 * t4 - self.M24 * t3 # Typo in original thought, should be t4, t2. Corrected.
        d1 = self.M21 * t5 - self.M22 * t1 + self.M24 * t0 # Error here, should be M21*t5 - M23*t2 + M24*t1
        # Let's use a more standard cofactor expansion.
        # For a full implementation, careful transcription of the 24 terms is needed.
        # For now, a placeholder or a reference to a library for such math is common.
        # A correct minor-based expansion:
        m = self.to_list()
        return (
            m[0] * (m[5]*(m[10]*m[15] - m[11]*m[14]) - m[6]*(m[9]*m[15] - m[11]*m[13]) + m[7]*(m[9]*m[14] - m[10]*m[13])) -
            m[1] * (m[4]*(m[10]*m[15] - m[11]*m[14]) - m[6]*(m[8]*m[15] - m[11]*m[12]) + m[7]*(m[8]*m[14] - m[10]*m[12])) +
            m[2] * (m[4]*(m[9]*m[15] - m[11]*m[13]) - m[5]*(m[8]*m[15] - m[11]*m[12]) + m[7]*(m[8]*m[13] - m[9]*m[12])) -
            m[3] * (m[4]*(m[9]*m[14] - m[10]*m[13]) - m[5]*(m[8]*m[14] - m[10]*m[12]) + m[6]*(m[8]*m[13] - m[9]*m[12]))
        )


    def inverse(self) -> "Matrix4":
        """Calculates the inverse of the matrix. Raises ValueError if not invertible."""
        # Full 4x4 matrix inversion is complex.
        # This is a placeholder for a full implementation.
        # A common approach is to use Gaussian elimination or adjugate matrix method.
        # For now, returning a copy or identity to allow structure completion.
        # A proper implementation is lengthy.
        m = self.to_list()
        inv = [0.0] * 16

        inv[0] = m[5]*m[10]*m[15] - m[5]*m[11]*m[14] - m[9]*m[6]*m[15] + m[9]*m[7]*m[14] + m[13]*m[6]*m[11] - m[13]*m[7]*m[10]
        inv[4] = -m[4]*m[10]*m[15] + m[4]*m[11]*m[14] + m[8]*m[6]*m[15] - m[8]*m[7]*m[14] - m[12]*m[6]*m[11] + m[12]*m[7]*m[10]
        inv[8] = m[4]*m[9]*m[15] - m[4]*m[11]*m[13] - m[8]*m[5]*m[15] + m[8]*m[7]*m[13] + m[12]*m[5]*m[11] - m[12]*m[7]*m[9]
        inv[12] = -m[4]*m[9]*m[14] + m[4]*m[10]*m[13] + m[8]*m[5]*m[14] - m[8]*m[6]*m[13] - m[12]*m[5]*m[10] + m[12]*m[6]*m[9]

        inv[1] = -m[1]*m[10]*m[15] + m[1]*m[11]*m[14] + m[9]*m[2]*m[15] - m[9]*m[3]*m[14] - m[13]*m[2]*m[11] + m[13]*m[3]*m[10]
        inv[5] = m[0]*m[10]*m[15] - m[0]*m[11]*m[14] - m[8]*m[2]*m[15] + m[8]*m[3]*m[14] + m[12]*m[2]*m[11] - m[12]*m[3]*m[10]
        inv[9] = -m[0]*m[9]*m[15] + m[0]*m[11]*m[13] + m[8]*m[1]*m[15] - m[8]*m[3]*m[13] - m[12]*m[1]*m[11] + m[12]*m[3]*m[9]
        inv[13] = m[0]*m[9]*m[14] - m[0]*m[10]*m[13] - m[8]*m[1]*m[14] + m[8]*m[2]*m[13] + m[12]*m[1]*m[10] - m[12]*m[2]*m[9]

        inv[2] = m[1]*m[6]*m[15] - m[1]*m[7]*m[14] - m[5]*m[2]*m[15] + m[5]*m[3]*m[14] + m[13]*m[2]*m[7] - m[13]*m[3]*m[6]
        inv[6] = -m[0]*m[6]*m[15] + m[0]*m[7]*m[14] + m[4]*m[2]*m[15] - m[4]*m[3]*m[14] - m[12]*m[2]*m[7] + m[12]*m[3]*m[6]
        inv[10] = m[0]*m[5]*m[15] - m[0]*m[7]*m[13] - m[4]*m[1]*m[15] + m[4]*m[3]*m[13] + m[12]*m[1]*m[7] - m[12]*m[3]*m[5]
        inv[14] = -m[0]*m[5]*m[14] + m[0]*m[6]*m[13] + m[4]*m[1]*m[14] - m[4]*m[2]*m[13] - m[12]*m[1]*m[6] + m[12]*m[2]*m[5]

        inv[3] = -m[1]*m[6]*m[11] + m[1]*m[7]*m[10] + m[5]*m[2]*m[11] - m[5]*m[3]*m[10] - m[9]*m[2]*m[7] + m[9]*m[3]*m[6]
        inv[7] = m[0]*m[6]*m[11] - m[0]*m[7]*m[10] - m[4]*m[2]*m[11] + m[4]*m[3]*m[10] + m[8]*m[2]*m[7] - m[8]*m[3]*m[6]
        inv[11] = -m[0]*m[5]*m[11] + m[0]*m[7]*m[9] + m[4]*m[1]*m[11] - m[4]*m[3]*m[9] - m[8]*m[1]*m[7] + m[8]*m[3]*m[5]
        inv[15] = m[0]*m[5]*m[10] - m[0]*m[6]*m[9] - m[4]*m[1]*m[10] + m[4]*m[2]*m[9] + m[8]*m[1]*m[6] - m[8]*m[2]*m[5]

        det = m[0]*inv[0] + m[1]*inv[4] + m[2]*inv[8] + m[3]*inv[12]

        if det == 0:
            raise ValueError("Matrix is singular and cannot be inverted.")

        det_inv = 1.0 / det
        for i in range(16):
            inv[i] *= det_inv

        return Matrix4.from_list(inv)

    def transpose(self) -> "Matrix4":
        """Calculates the transpose of the matrix."""
        return Matrix4(
            self.M11, self.M21, self.M31, self.M41,
            self.M12, self.M22, self.M32, self.M42,
            self.M13, self.M23, self.M33, self.M43,
            self.M14, self.M24, self.M34, self.M44
        )

    @staticmethod
    def create_identity() -> "Matrix4":
        """Creates an identity matrix."""
        return Matrix4() # Dataclass default is identity

    @staticmethod
    def create_translation(x: float, y: float, z: float) -> "Matrix4":
        """Creates a translation matrix."""
        return Matrix4(
            1, 0, 0, x,
            0, 1, 0, y,
            0, 0, 1, z,
            0, 0, 0, 1
        )

    @staticmethod
    def create_scale(x: float, y: float, z: float) -> "Matrix4":
        """Creates a scale matrix."""
        return Matrix4(
            x, 0, 0, 0,
            0, y, 0, 0,
            0, 0, z, 0,
            0, 0, 0, 1
        )

    @staticmethod
    def create_from_quaternion(quat: Quaternion) -> "Matrix4":
        """Creates a rotation matrix from a quaternion."""
        q = quat.normalize() # Ensure quaternion is normalized

        xx, yy, zz = q.X * q.X, q.Y * q.Y, q.Z * q.Z
        xy, xz, yz = q.X * q.Y, q.X * q.Z, q.Y * q.Z
        wx, wy, wz = q.W * q.X, q.W * q.Y, q.W * q.Z

        return Matrix4(
            1 - 2 * (yy + zz),     2 * (xy - wz),     2 * (xz + wy), 0,
            2 * (xy + wz), 1 - 2 * (xx + zz),     2 * (yz - wx), 0,
            2 * (xz - wy),     2 * (yz + wx), 1 - 2 * (xx + yy), 0,
            0, 0, 0, 1
        )

Matrix4.Identity = Matrix4.create_identity()
Matrix4.ZERO = Matrix4(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0) # For convenience
