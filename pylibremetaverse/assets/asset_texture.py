import dataclasses
from .asset_base import Asset
from pylibremetaverse.types import AssetType # For setting default asset_type

# Standard JPEG 2000 magic numbers
JP2_MAGIC_NUMBER = b'\x00\x00\x00\x0C\x6A\x50\x20\x20\x0D\x0A\x87\x0A' # JP2 signature box
J2K_MAGIC_NUMBER = b'\xFF\x4F\xFF\x51' # SOC (Start of Codestream) marker

@dataclasses.dataclass
class AssetTexture(Asset):
    """Represents a texture asset, typically in JPEG 2000 format."""
    # Actual image data is stored in self.raw_data from the base Asset class.
    # width: int = 0 # Requires J2K decoding library to get these
    # height: int = 0
    # components: int = 0 # e.g., 3 for RGB, 4 for RGBA

    def __post_init__(self):
        super().__post_init__()
        if self.asset_type == AssetType.Unknown: # Default if not set by creator
            self.asset_type = AssetType.Texture

    def from_bytes(self, data: bytes) -> bool:
        """
        Populates asset fields from raw byte data.
        For textures, this currently checks for J2K magic numbers.
        Full decoding of J2K to get width/height/etc. is not implemented here.
        """
        super().from_bytes(data) # Stores raw_data
        self.loaded_successfully = False # Assume failure until check passes

        if not data:
            return False

        # Check for common J2K/JP2 magic numbers
        if data.startswith(JP2_MAGIC_NUMBER) or data.startswith(J2K_MAGIC_NUMBER):
            self.loaded_successfully = True
            # TODO: Future enhancement - use a J2K decoding library to extract width, height, components
            # For example (pseudo-code):
            # try:
            #     img_info = some_j2k_lib.decode_header(self.raw_data)
            #     self.width = img_info.width
            #     self.height = img_info.height
            #     self.components = img_info.components
            # except Exception as e:
            #     # Still loaded successfully as raw data, but header parsing failed
            #     logging.warning(f"AssetTexture {self.asset_id}: Could not parse J2K header: {e}")
            #     pass # Keep loaded_successfully = True as raw data is present
        else:
            # Could be other formats (e.g. TGA for baked textures in some contexts, though rare for general assets)
            # For now, if not J2K/JP2, consider it loaded if data is present, but log a warning.
            # Or, set loaded_successfully = False if strict J2K is expected for AssetType.Texture.
            # Let's assume AssetType.Texture should generally be J2K.
            # If other image types are supported via this class, this logic might need adjustment
            # or different AssetType (e.g. AssetType.ImageTGA if that existed).
            # For now, we'll be strict: if it's AssetType.Texture, we expect J2K.
            # However, the base class sets loaded_successfully = True.
            # Let's say, if it's not J2K, it's still "loaded" as raw bytes, but maybe less "valid".
            # For simplicity, if data is present, we'll mark it as loaded.
            # The consumer of the asset would then be responsible for actual format validation.
            self.loaded_successfully = True # Accept any non-empty bytestring as "loaded" raw texture data
            # logger.warning(f"AssetTexture {self.asset_id}: Data does not start with J2K/JP2 magic numbers. Storing as raw.")

        return self.loaded_successfully

    def __str__(self):
        # Add more info if width/height become available
        return f"{super().__str__()}"
