import math
import struct
import dataclasses # Using dataclasses directly
from .vector import Vector3, Vector4
from .quaternion import Quaternion

@dataclasses.dataclass(slots=True)
class Matrix4:
    """
    A 4x4 matrix class, typically used for transformations.
    Values are stored and initialized in row-major order:
    M11, M12, M13, M14,
    M21, M22, M23, M24,
    M31, M32, M33, M34,
    M41, M42, M43, M44
    """
    M11: float = 1.0; M12: float = 0.0; M13: float = 0.0; M14: float = 0.0
    M21: float = 0.0; M22: float = 1.0; M23: float = 0.0; M24: float = 0.0
    M31: float = 0.0; M32: float = 0.0; M33: float = 1.0; M34: float = 0.0
    M41: float = 0.0; M42: float = 0.0; M43: float = 0.0; M44: float = 1.0

    def __post_init__(self):
        # Ensure all elements are floats, useful if integers were passed.
        # This is somewhat redundant with type hinting but provides runtime coercion if needed.
        self.M11, self.M12, self.M13, self.M14 = float(self.M11), float(self.M12), float(self.M13), float(self.M14)
        self.M21, self.M22, self.M23, self.M24 = float(self.M21), float(self.M22), float(self.M23), float(self.M24)
        self.M31, self.M32, self.M33, self.M34 = float(self.M31), float(self.M32), float(self.M33), float(self.M34)
        self.M41, self.M42, self.M43, self.M44 = float(self.M41), float(self.M42), float(self.M43), float(self.M44)

    def _to_list_row_major(self) -> list[float]:
        """Helper to get elements in row-major list format."""
        return [
            self.M11, self.M12, self.M13, self.M14,
            self.M21, self.M22, self.M23, self.M24,
            self.M31, self.M32, self.M33, self.M34,
            self.M41, self.M42, self.M43, self.M44,
        ]

    @classmethod
    def from_list(cls, elements: list[float]) -> "Matrix4":
        """Creates a Matrix4 from a list of 16 floats (row-major)."""
        if len(elements) != 16:
            raise ValueError("List must contain 16 elements.")
        return cls(*elements)

    def is_identity(self, tolerance: float = 1e-6) -> bool:
        identity_elements = [
            1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1
        ]
        current_elements = self._to_list_row_major()
        for i in range(16):
            if abs(current_elements[i] - identity_elements[i]) > tolerance:
                return False
        return True

    def __str__(self) -> str:
        return (f"[{self.M11:.3f}, {self.M12:.3f}, {self.M13:.3f}, {self.M14:.3f}]\n"
                f"[{self.M21:.3f}, {self.M22:.3f}, {self.M23:.3f}, {self.M24:.3f}]\n"
                f"[{self.M31:.3f}, {self.M32:.3f}, {self.M33:.3f}, {self.M34:.3f}]\n"
                f"[{self.M41:.3f}, {self.M42:.3f}, {self.M43:.3f}, {self.M44:.3f}]")

    def __repr__(self) -> str: # Kept from existing, it's good
        return (f"Matrix4(M11={self.M11}, M12={self.M12}, M13={self.M13}, M14={self.M14}, "
                f"M21={self.M21}, M22={self.M22}, M23={self.M23}, M24={self.M24}, "
                f"M31={self.M31}, M32={self.M32}, M33={self.M33}, M34={self.M34}, "
                f"M41={self.M41}, M42={self.M42}, M43={self.M43}, M44={self.M44})")

    def __eq__(self, other) -> bool: # Kept from existing
        if not isinstance(other, Matrix4):
            return NotImplemented
        # Compare using a tolerance for float precision issues
        self_list = self._to_list_row_major()
        other_list = other._to_list_row_major()
        for i in range(16):
            if abs(self_list[i] - other_list[i]) > 1e-6: # Using a small tolerance
                return False
        return True


    def __mul__(self, other):
        if isinstance(other, Matrix4):
            # Matrix multiplication (copied from existing, it's correct)
            m_res = [0.0] * 16
            m_res[0] = self.M11*other.M11 + self.M12*other.M21 + self.M13*other.M31 + self.M14*other.M41
            m_res[1] = self.M11*other.M12 + self.M12*other.M22 + self.M13*other.M32 + self.M14*other.M42
            # ... (all 16 elements as in existing file) ...
            m_res[2] = self.M11*other.M13 + self.M12*other.M23 + self.M13*other.M33 + self.M14*other.M43
            m_res[3] = self.M11*other.M14 + self.M12*other.M24 + self.M13*other.M34 + self.M14*other.M44

            m_res[4] = self.M21*other.M11 + self.M22*other.M21 + self.M23*other.M31 + self.M24*other.M41
            m_res[5] = self.M21*other.M12 + self.M22*other.M22 + self.M23*other.M32 + self.M24*other.M42
            m_res[6] = self.M21*other.M13 + self.M22*other.M23 + self.M23*other.M33 + self.M24*other.M43
            m_res[7] = self.M21*other.M14 + self.M22*other.M24 + self.M23*other.M34 + self.M24*other.M44

            m_res[8] = self.M31*other.M11 + self.M32*other.M21 + self.M33*other.M31 + self.M34*other.M41
            m_res[9] = self.M31*other.M12 + self.M32*other.M22 + self.M33*other.M32 + self.M34*other.M42
            m_res[10]= self.M31*other.M13 + self.M32*other.M23 + self.M33*other.M33 + self.M34*other.M43
            m_res[11]= self.M31*other.M14 + self.M32*other.M24 + self.M33*other.M34 + self.M34*other.M44

            m_res[12]= self.M41*other.M11 + self.M42*other.M21 + self.M43*other.M31 + self.M44*other.M41
            m_res[13]= self.M41*other.M12 + self.M42*other.M22 + self.M43*other.M32 + self.M44*other.M42
            m_res[14]= self.M41*other.M13 + self.M42*other.M23 + self.M43*other.M33 + self.M44*other.M43
            m_res[15]= self.M41*other.M14 + self.M42*other.M24 + self.M43*other.M34 + self.M44*other.M44
            return Matrix4.from_list(m_res)

        elif isinstance(other, Vector4): # Transform Vector4 (copied from existing)
            x = self.M11*other.X + self.M12*other.Y + self.M13*other.Z + self.M14*other.W
            y = self.M21*other.X + self.M22*other.Y + self.M23*other.Z + self.M24*other.W
            z = self.M31*other.X + self.M32*other.Y + self.M33*other.Z + self.M34*other.W
            w = self.M41*other.X + self.M42*other.Y + self.M43*other.Z + self.M44*other.W
            return Vector4(x,y,z,w)

        elif isinstance(other, Vector3): # Added from my draft
            # Assumes transforming a point (w=1)
            res_x = self.M11*other.X + self.M12*other.Y + self.M13*other.Z + self.M14
            res_y = self.M21*other.X + self.M22*other.Y + self.M23*other.Z + self.M24
            res_z = self.M31*other.X + self.M32*other.Y + self.M33*other.Z + self.M34
            res_w = self.M41*other.X + self.M42*other.Y + self.M43*other.Z + self.M44

            if abs(res_w - 1.0) > 1e-6 and abs(res_w) > 1e-6 : # Perspective divide if w is not 1 and not 0
                return Vector3(res_x / res_w, res_y / res_w, res_z / res_w)
            return Vector3(res_x, res_y, res_z)
        return NotImplemented

    def determinant(self) -> float: # Kept from existing file (it's correct)
        m = self._to_list_row_major()
        return (
            m[0] * (m[5]*(m[10]*m[15] - m[11]*m[14]) - m[6]*(m[9]*m[15] - m[11]*m[13]) + m[7]*(m[9]*m[14] - m[10]*m[13])) -
            m[1] * (m[4]*(m[10]*m[15] - m[11]*m[14]) - m[6]*(m[8]*m[15] - m[11]*m[12]) + m[7]*(m[8]*m[14] - m[10]*m[12])) +
            m[2] * (m[4]*(m[9]*m[15] - m[11]*m[13]) - m[5]*(m[8]*m[15] - m[11]*m[12]) + m[7]*(m[8]*m[13] - m[9]*m[12])) -
            m[3] * (m[4]*(m[9]*m[14] - m[10]*m[13]) - m[5]*(m[8]*m[14] - m[10]*m[12]) + m[6]*(m[8]*m[13] - m[9]*m[12]))
        )

    def inverse(self) -> "Matrix4": # Kept from existing file (it's correct)
        m = self._to_list_row_major()
        inv_elems = [0.0] * 16
        inv_elems[0] = m[5]*m[10]*m[15] - m[5]*m[11]*m[14] - m[9]*m[6]*m[15] + m[9]*m[7]*m[14] + m[13]*m[6]*m[11] - m[13]*m[7]*m[10]
        # ... (all 16 inv_elems calculations as in existing file) ...
        inv_elems[4] = -m[4]*m[10]*m[15] + m[4]*m[11]*m[14] + m[8]*m[6]*m[15] - m[8]*m[7]*m[14] - m[12]*m[6]*m[11] + m[12]*m[7]*m[10]
        inv_elems[8] = m[4]*m[9]*m[15] - m[4]*m[11]*m[13] - m[8]*m[5]*m[15] + m[8]*m[7]*m[13] + m[12]*m[5]*m[11] - m[12]*m[7]*m[9]
        inv_elems[12] = -m[4]*m[9]*m[14] + m[4]*m[10]*m[13] + m[8]*m[5]*m[14] - m[8]*m[6]*m[13] - m[12]*m[5]*m[10] + m[12]*m[6]*m[9]
        inv_elems[1] = -m[1]*m[10]*m[15] + m[1]*m[11]*m[14] + m[9]*m[2]*m[15] - m[9]*m[3]*m[14] - m[13]*m[2]*m[11] + m[13]*m[3]*m[10]
        inv_elems[5] = m[0]*m[10]*m[15] - m[0]*m[11]*m[14] - m[8]*m[2]*m[15] + m[8]*m[3]*m[14] + m[12]*m[2]*m[11] - m[12]*m[3]*m[10]
        inv_elems[9] = -m[0]*m[9]*m[15] + m[0]*m[11]*m[13] + m[8]*m[1]*m[15] - m[8]*m[3]*m[13] - m[12]*m[1]*m[11] + m[12]*m[3]*m[9]
        inv_elems[13] = m[0]*m[9]*m[14] - m[0]*m[10]*m[13] - m[8]*m[1]*m[14] + m[8]*m[2]*m[13] + m[12]*m[1]*m[10] - m[12]*m[2]*m[9]
        inv_elems[2] = m[1]*m[6]*m[15] - m[1]*m[7]*m[14] - m[5]*m[2]*m[15] + m[5]*m[3]*m[14] + m[13]*m[2]*m[7] - m[13]*m[3]*m[6]
        inv_elems[6] = -m[0]*m[6]*m[15] + m[0]*m[7]*m[14] + m[4]*m[2]*m[15] - m[4]*m[3]*m[14] - m[12]*m[2]*m[7] + m[12]*m[3]*m[6]
        inv_elems[10] = m[0]*m[5]*m[15] - m[0]*m[7]*m[13] - m[4]*m[1]*m[15] + m[4]*m[3]*m[13] + m[12]*m[1]*m[7] - m[12]*m[3]*m[5]
        inv_elems[14] = -m[0]*m[5]*m[14] + m[0]*m[6]*m[13] + m[4]*m[1]*m[14] - m[4]*m[2]*m[13] - m[12]*m[1]*m[6] + m[12]*m[2]*m[5]
        inv_elems[3] = -m[1]*m[6]*m[11] + m[1]*m[7]*m[10] + m[5]*m[2]*m[11] - m[5]*m[3]*m[10] - m[9]*m[2]*m[7] + m[9]*m[3]*m[6]
        inv_elems[7] = m[0]*m[6]*m[11] - m[0]*m[7]*m[10] - m[4]*m[2]*m[11] + m[4]*m[3]*m[10] + m[8]*m[2]*m[7] - m[8]*m[3]*m[6]
        inv_elems[11] = -m[0]*m[5]*m[11] + m[0]*m[7]*m[9] + m[4]*m[1]*m[11] - m[4]*m[3]*m[9] - m[8]*m[1]*m[7] + m[8]*m[3]*m[5]
        inv_elems[15] = m[0]*m[5]*m[10] - m[0]*m[6]*m[9] - m[4]*m[1]*m[10] + m[4]*m[2]*m[9] + m[8]*m[1]*m[6] - m[8]*m[2]*m[5]

        det = m[0]*inv_elems[0] + m[1]*inv_elems[4] + m[2]*inv_elems[8] + m[3]*inv_elems[12]
        if abs(det) < 1e-9: # Use tolerance for zero determinant
            raise ValueError("Matrix is singular and cannot be inverted (determinant is too close to zero).")

        det_inv = 1.0 / det
        for i in range(16):
            inv_elems[i] *= det_inv
        return Matrix4.from_list(inv_elems)

    def transpose(self) -> "Matrix4": # Kept from existing
        return Matrix4(
            self.M11, self.M21, self.M31, self.M41,
            self.M12, self.M22, self.M32, self.M42,
            self.M13, self.M23, self.M33, self.M43,
            self.M14, self.M24, self.M34, self.M44
        )

    @staticmethod
    def create_identity() -> "Matrix4": # Kept from existing
        return Matrix4()

    @staticmethod
    def create_translation(translation: Vector3) -> "Matrix4": # Changed to use Vector3
        return Matrix4(
            M14=translation.X,
            M24=translation.Y,
            M34=translation.Z
        )

    @staticmethod
    def create_scale(scale: Vector3) -> "Matrix4": # Changed to use Vector3
        return Matrix4(
            M11=scale.X,
            M22=scale.Y,
            M33=scale.Z
        )

    @staticmethod
    def create_from_quaternion(q: Quaternion) -> "Matrix4": # Kept from existing (formula is correct)
        q = q.normalize()
        xx, yy, zz = q.X*q.X, q.Y*q.Y, q.Z*q.Z
        xy, xz, yz = q.X*q.Y, q.X*q.Z, q.Y*q.Z
        wx, wy, wz = q.W*q.X, q.W*q.Y, q.W*q.Z
        return Matrix4(
            M11=1 - 2*(yy + zz), M12=2*(xy - wz),     M13=2*(xz + wy), M14=0.0,
            M21=2*(xy + wz),     M22=1 - 2*(xx + zz), M23=2*(yz - wx), M24=0.0,
            M31=2*(xz - wy),     M32=2*(yz + wx),     M33=1 - 2*(xx + yy), M34=0.0,
            M41=0.0, M42=0.0, M43=0.0, M44=1.0
        )

    @staticmethod
    def create_look_at(camera_pos: Vector3, camera_target: Vector3, camera_up: Vector3) -> "Matrix4": # Added from my draft
        z_axis = (camera_target - camera_pos).normalize()
        x_axis = camera_up.cross(z_axis).normalize() # Note: SL/LibreMetaverse might use a different up-vector convention
        y_axis = z_axis.cross(x_axis)

        return Matrix4(
            M11=x_axis.X, M12=x_axis.Y, M13=x_axis.Z, M14=-x_axis.dot(camera_pos),
            M21=y_axis.X, M22=y_axis.Y, M23=y_axis.Z, M24=-y_axis.dot(camera_pos),
            M31=z_axis.X, M32=z_axis.Y, M33=z_axis.Z, M34=-z_axis.dot(camera_pos),
            M41=0.0,      M42=0.0,      M43=0.0,      M44=1.0
        )

    @staticmethod
    def create_perspective_fov(fov_y_rad: float, aspect_ratio: float, near_plane: float, far_plane: float) -> "Matrix4": # Added from my draft
        if aspect_ratio == 0: raise ValueError("aspect_ratio cannot be zero.")
        if far_plane == near_plane: raise ValueError("far_plane and near_plane cannot be equal.")
        if near_plane <= 0: raise ValueError("near_plane must be positive.")
        if far_plane <= 0: raise ValueError("far_plane must be positive.")


        cot_fov_half = 1.0 / math.tan(fov_y_rad / 2.0)

        # Standard perspective projection matrix (OpenGL like, results in -1 to 1 NDC)
        m11 = cot_fov_half / aspect_ratio
        m22 = cot_fov_half
        m33 = (far_plane + near_plane) / (near_plane - far_plane) # Remaps Z to [-1, 1]
        m34 = (2 * far_plane * near_plane) / (near_plane - far_plane)
        m43 = -1.0 # Projects Z to -W for perspective divide (camera looks down -Z)
        m44 = 0.0

        return Matrix4(M11=m11, M22=m22, M33=m33, M34=m34, M43=m43, M44=0.0)

    def to_bytes_row_major(self) -> bytes: # Added from my draft
        """Packs matrix into 16 floats (64 bytes) in row-major order."""
        return struct.pack('<16f', *self._to_list_row_major())

    def to_bytes_column_major(self) -> bytes: # Added from my draft
        """Packs matrix into 16 floats (64 bytes) in column-major order (OpenGL default)."""
        tm_list = self.transpose()._to_list_row_major()
        return struct.pack('<16f', *tm_list)

    @staticmethod
    def from_bytes_row_major(data: bytes, offset: int = 0) -> 'Matrix4': # Added from my draft
        if len(data) - offset < 64:
            raise ValueError("Not enough bytes to unpack Matrix4 (row-major). Need 64.")
        elements = list(struct.unpack_from('<16f', data, offset))
        return Matrix4.from_list(elements)

Matrix4.Identity = Matrix4.create_identity() # Kept from existing
Matrix4.ZERO = Matrix4(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0) # Kept from existing

if __name__ == '__main__': # Combined tests
    print("Matrix4 tests...")
    m_id = Matrix4.identity()
    print("Identity Matrix:\n", m_id)
    assert m_id.is_identity()

    v_trans = Vector3(10, 20, 30)
    m_trans = Matrix4.create_translation(v_trans)
    print("Translation Matrix (10,20,30):\n", m_trans)
    assert m_trans.M14 == 10 and m_trans.M24 == 20 and m_trans.M34 == 30

    v_scale = Vector3(2, 3, 4)
    m_scale = Matrix4.create_scale(v_scale)
    print("Scale Matrix (2,3,4):\n", m_scale)
    assert m_scale.M11 == 2 and m_scale.M22 == 3 and m_scale.M33 == 4

    q_rot = Quaternion.from_axis_angle(Vector3(0,1,0), math.pi/2)
    m_rot = Matrix4.create_from_quaternion(q_rot)
    print("Rotation Matrix (90 deg around Y):\n", m_rot)
    assert abs(m_rot.M11 - 0) < 1e-6 and abs(m_rot.M13 - 1) < 1e-6

    m_combo = m_trans * m_rot * m_scale
    print("Combined TRS Matrix (S*R*T order of application):\n", m_combo)

    v_point = Vector3(1, 1, 1)
    v_transformed = m_combo * v_point
    # S(1,1,1) -> (2,3,4)
    # R(y,pi/2) . (2,3,4) -> (4,3,-2) (approx: cos(pi/2)*x+sin(pi/2)*z, y, -sin(pi/2)*x+cos(pi/2)*z)
    # T(10,20,30) . (4,3,-2) -> (14,23,28)
    print(f"Point (1,1,1) transformed by TRS: {v_transformed}")
    assert abs(v_transformed.X - 14) < 1e-5
    assert abs(v_transformed.Y - 23) < 1e-5
    assert abs(v_transformed.Z - 28) < 1e-5

    m_orig = Matrix4.create_translation(Vector3(1.5,2.5,3.5)) * \
             Matrix4.create_from_quaternion(Quaternion.from_euler_angles(0.5,0.8,0.2)) * \
             Matrix4.create_scale(Vector3(1.0,2.0,0.5))
    m_inv = m_orig.inverse()
    m_id_check = m_orig * m_inv
    print("Original Matrix:\n", m_orig)
    # print("Inverse Matrix:\n", m_inv) # Can be verbose
    print("Original * Inverse (should be Identity):\n", m_id_check)
    assert m_id_check.is_identity(tolerance=1e-5)

    m_det_test = Matrix4.create_scale(Vector3(2,3,1)) # M44 is 1 by default
    print("Determinant of scale(2,3,1) matrix:", m_det_test.determinant())
    assert abs(m_det_test.determinant() - (2*3*1*1)) < 1e-6 # Scale only affects M11,M22,M33

    m_simple = Matrix4(M12=5.0, M21=10.0)
    m_simple_t = m_simple.transpose()
    print("Simple matrix:\n", m_simple)
    print("Transposed simple matrix:\n", m_simple_t)
    assert m_simple_t.M12 == 10.0 and m_simple_t.M21 == 5.0

    rm_bytes = m_combo.to_bytes_row_major()
    m_from_rm_bytes = Matrix4.from_bytes_row_major(rm_bytes)
    assert m_combo == m_from_rm_bytes

    # LookAt and Perspective
    cam_pos = Vector3(0,5,10)
    cam_target = Vector3(0,0,0)
    cam_up = Vector3(0,1,0)
    m_lookat = Matrix4.create_look_at(cam_pos, cam_target, cam_up)
    print("LookAt Matrix:\n", m_lookat)
    # A point at origin, transformed by lookat, should be at (0,0,-10) before perspective
    origin_in_cam_space = m_lookat * Vector3.ZERO
    assert abs(origin_in_cam_space.Z - (-10.0)) < 1e-5


    m_persp = Matrix4.create_perspective_fov(math.radians(60), 16.0/9.0, 0.1, 1000.0)
    print("Perspective Matrix:\n", m_persp)
    # Check a few key properties of perspective matrix
    assert m_persp.M43 == -1.0 and m_persp.M44 == 0.0
    assert m_persp.M11 > 0 and m_persp.M22 > 0

    print("Matrix4 tests passed.")
