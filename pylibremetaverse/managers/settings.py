# Stub for Settings
class Settings:
    def __init__(self, client_ref):
        self.client = client_ref
        # Dummy attributes for GridClient._setup_http_caps_client
        self.MAX_HTTP_CONNECTIONS: int = 10
        self.USER_AGENT: str = "pylibremetaverse/0.1"
        self.CAPS_TIMEOUT: int = 60000 # milliseconds
        self.MULTIPLE_SIMS: bool = True # Example, adjust as needed
        self.LOGIN_SERVER: str = "https://login.agni.lindenlab.com/cgi-bin/login.cgi" # Example
        self.LOGOUT_TIMEOUT: int = 5000 # ms
        self.DISABLE_STATISTICS: bool = False
        self.SEND_AGENT_UPDATES: bool = True
        self.STORE_LAND_PATCHES: bool = False
        self.ALWAYS_DECODE_OBJECTS: bool = False
        self.ALWAYS_REQUEST_OBJECTS: bool = False
        self.ENABLE_OBJECT_TRACKING: bool = False
        self.THROTTLE_OUTGOING_PACKETS: bool = True # Default usually true
        self.default_animation_send_rate: int = 30 # Example
        pass
