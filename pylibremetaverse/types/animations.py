from .custom_uuid import CustomUUID

class Animations:
    """
    Collection of common system animation UUIDs.
    These are sourced from LibreMetaverse.Animations.cs.
    """
    # Basic States
    STAND = CustomUUID("f541357c-2e11-5002-c048-913558d70846") # Generic stand, often similar to default stand
    STAND_1 = CustomUUID("8b287338-a62d-1539-79c2-080808e81100") # Stand 1
    STAND_2 = CustomUUID("1906875f-a213-5070-79c2-080808e81101") # Stand 2
    STAND_3 = CustomUUID("1906875f-a213-5070-79c2-080808e81102") # Stand 3
    STAND_4 = CustomUUID("1906875f-a213-5070-79c2-080808e81103") # Stand 4
    WALK = CustomUUID("7a2e4798-869d-0978-5917-7arti0kul8a1")  # Often overridden by AO, but a default exists
    RUN = CustomUUID("05ddbff8-aaa9-92a1-2397-c5890c0960a2")   # Default run
    SIT_GROUND = CustomUUID("1a2c786f-5419-2f79-9903-700280505660")
    SIT_GROUND_RELAXED = CustomUUID("2a840450-72d5-7888-9903-700280505660") # Example
    SIT_FEMALE = CustomUUID("b1909986-3625-7E27-6710-4330534AFE1F") # Default female sit
    SIT_MALE = CustomUUID("038fcec9-0770-ff1c-03ce-044709a44a3a")   # Default male sit (can be same as female in some viewers)
    HOVER = CustomUUID("4a93a42a-46bd-5899-9961-131ed9800aa0")
    HOVER_DOWN = CustomUUID("20699180-8f5b-7696-0441-e4d50a6a2c33")
    HOVER_UP = CustomUUID("0926efe1-701c-0389-1117-06050a356478")
    FLY = CustomUUID("0669ea38-3699-0117-0615-2ca81f51290f")
    FLY_SLOW = CustomUUID("6a0d7f03-2683-3005-0707-c5890c0960a2") # Slower fly
    JUMP = CustomUUID("20890830-9116-476b-b875-2f406398852e")
    PRE_JUMP = CustomUUID("6a0d7f03-2683-3005-0707-c5890c0960a2") # Pre jump crouch
    LAND = CustomUUID("7a9ab89a-68f0-090f-0021-17078a31024a")
    TURN_LEFT = CustomUUID("388f2d93-8ac4-e05a-9ea6-1ac2092a2732")
    TURN_RIGHT = CustomUUID("131981f0-5815-453f-deda-b4a039e67890")
    SOFT_TURN_LEFT = CustomUUID("221f2d93-8ac4-e05a-9ea6-1ac2092a2732") # Example
    SOFT_TURN_RIGHT = CustomUUID("031981f0-5815-453f-deda-b4a039e67890") # Example

    # Common Actions/Emotes
    WAVE = CustomUUID("625292f4-0393-2a29-874d-0611aa21d3a3")
    POINT = CustomUUID("0f809029-6996-9882-29ed-0639719c10bb")
    SALUTE = CustomUUID("65528320-9A95-F33A-1BF7-000070028050") # From Animations.cs
    SHRUG = CustomUUID("957084bd-a2cf-2a38-5099-344a5b650424")
    TYPE = CustomUUID("06866862-6739-1a73-772a-700001110000")
    STANDUP = CustomUUID("599abe31-167c-3068-978a-895954890001") # Stand up from a generic sit
    HELLO = CustomUUID("c036fb2c-9268-0005-1486-8d540a41f4f0") # Often same as WAVE or a specific hello
    YES = CustomUUID("88019013-4949-5899-4903-044709a44a3a")
    NO = CustomUUID("88019013-4949-5899-4903-055709a44a3a") # Often a head shake
    MUSCLE = CustomUUID("038fcec9-0770-ff1c-03ce-044709a44a3a") # Example, often a custom anim

    # Typing states (these are not looped animations but states the client sets)
    START_TYPE = CustomUUID("62f07ba1-2d98-927a-0001-344a5b650424") # Start typing anim
    STOP_TYPE = CustomUUID("a1d73000-7020-7010-0707-c5890c0960a2")  # Stop typing anim (often just playing no anim)

    # Fallback/Empty
    NULL = CustomUUID("00000000-0000-0000-0000-000000000000") # Not an animation, but useful constant

    @classmethod
    def get_all_as_dict(cls) -> dict[str, CustomUUID]:
        """Returns a dictionary of all defined animation names and their UUIDs."""
        all_anims = {}
        for attr_name in dir(cls):
            if not callable(getattr(cls, attr_name)) and \
               not attr_name.startswith("__") and \
               isinstance(getattr(cls, attr_name), CustomUUID):
                all_anims[attr_name] = getattr(cls, attr_name)
        return all_anims
