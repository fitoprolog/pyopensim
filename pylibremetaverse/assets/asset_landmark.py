import dataclasses
import re
from .asset_base import Asset
from pylibremetaverse.types import CustomUUID, Vector3, AssetType # For default asset_type

@dataclasses.dataclass
class AssetLandmark(Asset):
    """Represents a landmark asset."""
    # Format is typically "slalm version X\nregion_handle RRRRRR\nlocal_pos X Y Z\nregion_id UUID\n..."
    # All fields are optional beyond version.

    landmark_version: str = "1.2" # Common default if not specified in data
    region_handle: int = 0       # Sim region handle (global X * 256 + global Y)
    position: Vector3 = dataclasses.field(default_factory=Vector3.ZERO) # Local position within the region
    region_id: CustomUUID = dataclasses.field(default_factory=CustomUUID.ZERO) # Optional region UUID
    # Gatekeeper and god_like fields are less common for user LMs, more for system ones.

    def __post_init__(self):
        super().__post_init__()
        if self.asset_type == AssetType.Unknown: # Default if not set by creator
            self.asset_type = AssetType.Landmark

    def from_bytes(self, data: bytes) -> bool:
        """
        Parses landmark data from its raw byte representation.
        Assumes "slalm" format.
        """
        super().from_bytes(data) # Stores raw_data
        self.loaded_successfully = False

        try:
            text_content = data.decode('utf-8')
            lines = text_content.splitlines()

            if not lines or not lines[0].lower().startswith("slalm version"):
                # Not a slalm format, or empty. Could try to treat as raw if needed.
                return False

            # Parse version from first line if present
            version_match = re.match(r"slalm version\s+([\d.]+)", lines[0], re.IGNORECASE)
            if version_match:
                self.landmark_version = version_match.group(1)

            for line in lines[1:]: # Skip the version line
                parts = line.strip().split(None, 1) # Split on first whitespace
                if len(parts) < 2:
                    continue

                key = parts[0].lower()
                value_str = parts[1]

                if key == "region_handle":
                    try: self.region_handle = int(value_str)
                    except ValueError: pass # Ignore malformed lines
                elif key == "local_pos":
                    pos_parts = value_str.split()
                    if len(pos_parts) == 3:
                        try:
                            self.position = Vector3(float(pos_parts[0]), float(pos_parts[1]), float(pos_parts[2]))
                        except ValueError: pass # Ignore malformed position
                elif key == "region_id":
                    try: self.region_id = CustomUUID(value_str)
                    except ValueError: pass # Ignore malformed UUID
                # Add more key parsing here if needed (e.g., gatekeeper, god_like)

            # A landmark is considered successfully loaded if it has at least a region_handle or position
            # (even if region_id is missing, it can still be functional if region_handle is valid)
            if self.region_handle > 0 or self.position != Vector3.ZERO or self.region_id != CustomUUID.ZERO:
                 self.loaded_successfully = True
            else: # If no useful data was parsed, mark as failed.
                 self.loaded_successfully = False


        except UnicodeDecodeError:
            # self.raw_data still holds the original bytes
            self.loaded_successfully = False
        except Exception: # Catch any other parsing errors
            self.loaded_successfully = False

        return self.loaded_successfully

    def __str__(self):
        return (f"{super().__str__()} RegionHandle={self.region_handle}, Position={self.position}, "
                f"RegionID={self.region_id if self.region_id != CustomUUID.ZERO else 'N/A'}")
