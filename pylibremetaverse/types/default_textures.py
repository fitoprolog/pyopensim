# default_textures.py
# Defines default texture UUIDs for avatar appearance

from .custom_uuid import CustomUUID

# Standard Second Life Default Texture UUIDs
# These are commonly used as fallbacks or initial textures.

# Skin textures
# While SL uses different baked textures for head, upper, and lower body parts,
# they often derive from a base skin. For simplicity, a single widely recognized
# default skin texture can be used as a placeholder for all if specific baked
# layer defaults aren't critical for initial appearance logic.
# The "Default System Skin" is a common fallback.
DEFAULT_SKIN_TEXTURE_GENERAL = CustomUUID("5748decc-f629-461c-9a36-a35a221fe21f")

# Specific default skin parts (can use the general one if specifics are not set)
DEFAULT_HEAD_SKIN_TEXTURE = DEFAULT_SKIN_TEXTURE_GENERAL
DEFAULT_UPPER_SKIN_TEXTURE = DEFAULT_SKIN_TEXTURE_GENERAL
DEFAULT_LOWER_SKIN_TEXTURE = DEFAULT_SKIN_TEXTURE_GENERAL

# Default eyes (Iris)
DEFAULT_EYES_TEXTURE = CustomUUID("48305229-0679-435a-9987-a02c0ead0899") # SL Default Eyes (brown)

# Default hair
# This can be a "bald cap" texture or a basic hair style.
# Using a common "bald" texture UUID.
DEFAULT_HAIR_TEXTURE = CustomUUID("00000000-0000-0000-5005-000000000005") # Often used as a bald cap / transparent hair layer

# Default clothing items (textures that are applied if no clothing is worn in a slot)
# These are texture assets, not wearable item assets.
# Often plain white or simple fabric textures.
DEFAULT_SHIRT_TEXTURE = CustomUUID("00000000-0000-0000-0000-000000000000") # Placeholder (e.g., a white texture)
DEFAULT_PANTS_TEXTURE = CustomUUID("00000000-0000-0000-0000-000000000000") # Placeholder (e.g., a white texture)
DEFAULT_SKIRT_TEXTURE = CustomUUID("00000000-0000-0000-0000-000000000000") # Placeholder for default skirt texture

# Other common default visual assets
AVATAR_PARTICLE_SYSTEM_DEFAULT = CustomUUID("00000000-0000-0000-0000-000000000000") # Placeholder

# For TextureEntryFace.texture_id, a CustomUUID.ZERO can mean "no texture" or "blank white"
# depending on viewer interpretation for certain faces.
BLANK_TEXTURE = CustomUUID.ZERO # Often used for untextured faces or alpha masks

# Default map for avatar appearance bakes.
# Keys should be the AVATAR_FACE_* constants from AppearanceManager.
# This provides a fallback texture for each bake layer if not overridden by wearables.
# Using placeholder values here; these should be the standard Linden Lab default
# baked texture UUIDs for each layer if known and accuracy is critical.
# For now, many will point to general skin or specific part defaults.

# These constants would ideally be imported from AppearanceManager or a shared types location
# to avoid defining them twice, but for now, assume numeric correspondence.
# AVATAR_FACE_HEAD = 0
# AVATAR_FACE_UPPER_BODY = 1
# AVATAR_FACE_LOWER_BODY = 2
# AVATAR_FACE_EYES = 3
# AVATAR_FACE_HAIR = 4
# etc. (up to MAX_AVATAR_FACES - 1)

DEFAULT_AVATAR_TEXTURES_MAP: dict[int, CustomUUID] = {
    0: DEFAULT_HEAD_SKIN_TEXTURE,    # Head
    1: DEFAULT_UPPER_SKIN_TEXTURE,   # Upper Body
    2: DEFAULT_LOWER_SKIN_TEXTURE,   # Lower Body
    3: DEFAULT_EYES_TEXTURE,         # Eyes
    4: DEFAULT_HAIR_TEXTURE,         # Hair
    5: DEFAULT_UPPER_SKIN_TEXTURE,   # Upper Arm (defaults to upper body skin)
    6: DEFAULT_UPPER_SKIN_TEXTURE,   # Lower Arm (defaults to upper body skin)
    7: DEFAULT_UPPER_SKIN_TEXTURE,   # Hands (defaults to upper body skin)
    8: DEFAULT_LOWER_SKIN_TEXTURE,   # Upper Leg (defaults to lower body skin)
    9: DEFAULT_LOWER_SKIN_TEXTURE,   # Lower Leg (defaults to lower body skin)
    10: DEFAULT_LOWER_SKIN_TEXTURE,  # Foot (defaults to lower body skin)
    11: DEFAULT_SKIRT_TEXTURE,       # Skirt (can be blank or a default skirt texture)
    # Auxiliary layers (12-21 for MAX_AVATAR_FACES=22) often default to blank/transparent
    12: BLANK_TEXTURE,
    13: BLANK_TEXTURE,
    14: BLANK_TEXTURE,
    15: BLANK_TEXTURE,
    16: BLANK_TEXTURE,
    17: BLANK_TEXTURE,
    18: BLANK_TEXTURE,
    19: BLANK_TEXTURE,
    20: BLANK_TEXTURE,
    21: BLANK_TEXTURE,
    # Add more entries if MAX_AVATAR_FACES is larger, up to MAX_AVATAR_FACES-1
}


if __name__ == '__main__':
    print("Default Textures:")
    print(f"  Skin (General): {DEFAULT_SKIN_TEXTURE_GENERAL}")
    print(f"  Eyes: {DEFAULT_EYES_TEXTURE}")
    print(f"  Hair (Bald Cap): {DEFAULT_HAIR_TEXTURE}")
    # The AppearanceManager now uses DEFAULT_SKIN_TEXTURE_GENERAL for head, upper, lower.
    # And DEFAULT_EYES_TEXTURE, DEFAULT_HAIR_TEXTURE for their respective slots.
    # This is consistent with the requirements.
    assert DEFAULT_HEAD_SKIN_TEXTURE == DEFAULT_SKIN_TEXTURE_GENERAL
    assert DEFAULT_UPPER_SKIN_TEXTURE == DEFAULT_SKIN_TEXTURE_GENERAL
    assert DEFAULT_LOWER_SKIN_TEXTURE == DEFAULT_SKIN_TEXTURE_GENERAL
    print("Default texture constants seem correctly defined for AppearanceManager usage.")
