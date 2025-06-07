import math
from pylibremetaverse.types import Vector3, Quaternion

class AgentCamera:
    """Manages the agent's camera position, orientation, and viewing frustum."""

    def __init__(self):
        self._position: Vector3 = Vector3.ZERO # Camera position in sim
        self._at_axis: Vector3 = Vector3(0.9999, 0.0, 0.0) # Normalized vector camera is looking along (forward)
        self._left_axis: Vector3 = Vector3(0.0, 0.9999, 0.0) # Normalized vector pointing left from camera
        self._up_axis: Vector3 = Vector3(0.0, 0.0, 0.9999) # Normalized vector pointing up from camera
        self._far: float = 128.0 # Far clipping plane distance

        # Ensure initial vectors are normalized (though defaults are close enough)
        self._at_axis = self._at_axis.normalize() if self._at_axis.magnitude_squared() > 0 else Vector3(1.0,0.0,0.0)
        self._left_axis = self._left_axis.normalize() if self._left_axis.magnitude_squared() > 0 else Vector3(0.0,1.0,0.0)
        self._up_axis = self._up_axis.normalize() if self._up_axis.magnitude_squared() > 0 else Vector3(0.0,0.0,1.0)


    @property
    def position(self) -> Vector3: return self._position
    @position.setter
    def position(self, value: Vector3): self._position = value

    @property
    def at_axis(self) -> Vector3: return self._at_axis
    @at_axis.setter
    def at_axis(self, value: Vector3): self._at_axis = value.normalize() if value.magnitude_squared() > 0 else Vector3(1.0,0.0,0.0)

    @property
    def left_axis(self) -> Vector3: return self._left_axis
    @left_axis.setter
    def left_axis(self, value: Vector3): self._left_axis = value.normalize() if value.magnitude_squared() > 0 else Vector3(0.0,1.0,0.0)

    @property
    def up_axis(self) -> Vector3: return self._up_axis
    @up_axis.setter
    def up_axis(self, value: Vector3): self._up_axis = value.normalize() if value.magnitude_squared() > 0 else Vector3(0.0,0.0,1.0)

    @property
    def far(self) -> float: return self._far
    @far.setter
    def far(self, value: float): self._far = max(0.0, value)


    def look_direction(self, heading_rads: float):
        """
        Sets camera orientation based on a heading angle (radians) in the XY plane.
        Assumes camera pitch and roll are zero (level with horizon).
        """
        cos_h = math.cos(heading_rads)
        sin_h = math.sin(heading_rads)

        self._at_axis = Vector3(cos_h, sin_h, 0.0) # Forward vector in XY plane
        # Left vector is 90 degrees counter-clockwise from AtAxis in XY plane
        self._left_axis = Vector3(-sin_h, cos_h, 0.0)
        self._up_axis = Vector3(0.0, 0.0, 1.0) # Assuming camera is level

    def look_at(self, target_pos: Vector3, current_pos: Vector3 | None = None):
        """
        Orients the camera to look at a target position from a current position.
        Args:
            target_pos: The world coordinates of the point to look at.
            current_pos: The world coordinates of the camera. If None, uses self.position.
        """
        cam_pos = current_pos if current_pos is not None else self._position

        forward = target_pos - cam_pos
        if forward.magnitude_squared() < 1e-6: # Too close, can't determine direction
            # Keep current orientation or default to something sensible
            # For now, if too close, don't change AtAxis
            if self._at_axis.magnitude_squared() < 1e-6: # If AtAxis is also zero, reset
                 self._at_axis = Vector3(1.0, 0.0, 0.0)
        else:
            self._at_axis = forward.normalize()

        # Calculate Up vector (assuming world Up is <0,0,1>)
        # This is a common way to get a stable Up vector for camera.
        # If AtAxis is (nearly) parallel to world_up, Right vector calculation will be unstable.
        world_up = Vector3(0.0, 0.0, 1.0)
        dot_at_world_up = self._at_axis.dot(world_up)

        if abs(dot_at_world_up) > 0.999: # Camera looking nearly straight up or down
            # Use previous Left vector to derive new Up, or an alternative reference
            # For simplicity, if looking straight up/down, Up can be At cross previous Left
            # This ensures Up remains orthogonal to At and somewhat stable.
            # However, a more robust solution might involve keeping camera roll fixed.
            # Let's use a fallback: if looking straight up/down, use world X as a stable "right" reference.
            if dot_at_world_up > 0: # Looking up
                self._up_axis = self._at_axis.cross(Vector3(1.0,0.0,0.0)).normalize()
                if self._up_axis.magnitude_squared() < 1e-6: # If At was parallel to X
                    self._up_axis = self._at_axis.cross(Vector3(0.0,1.0,0.0)).normalize()
            else: # Looking down
                 self._up_axis = self._at_axis.cross(Vector3(-1.0,0.0,0.0)).normalize()
                 if self._up_axis.magnitude_squared() < 1e-6:
                    self._up_axis = self._at_axis.cross(Vector3(0.0,-1.0,0.0)).normalize()

        else: # Standard case
            right = self._at_axis.cross(world_up).normalize()
            self._up_axis = right.cross(self._at_axis).normalize() # Re-calculate Up to be orthogonal

        # Left is cross product of Up and At
        self._left_axis = self._up_axis.cross(self._at_axis).normalize()

        # Ensure all are normalized again due to potential float precision issues
        self._at_axis = self._at_axis.normalize()
        self._up_axis = self._up_axis.normalize()
        self._left_axis = self._left_axis.normalize()

    def __str__(self):
        return (f"AgentCamera(Pos={self.position}, At={self.at_axis}, Up={self.up_axis}, "
                f"Left={self.left_axis}, Far={self.far})")
