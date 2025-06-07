"""
Client runtime settings and constants.
"""
from pylibremetaverse.types import Color4
from pylibremetaverse.types.enums import LogLevel

class Settings:
    """
    Manages client settings, including connection parameters, timeouts,
    and feature flags. Many of these settings mirror those found in
    LibreMetaverse's Settings.cs.
    """

    # --- Class Variables (Constants and Static Defaults) ---
    AGNI_LOGIN_SERVER: str = "https://login.agni.lindenlab.com/cgi-bin/login.cgi"
    """Primary grid login URI."""

    ADITI_LOGIN_SERVER: str = "https://login.aditi.lindenlab.com/cgi-bin/login.cgi"
    """Beta grid login URI."""

    USER_AGENT: str = "PyLibreMetaverse/0.1"
    """HTTP User-Agent header passed by the client."""

    RESOURCE_DIR: str = "pylibremetaverse_data"
    """Default directory for storing resource files (logs, cache)."""

    BIND_ADDR: str = "0.0.0.0"
    """Represents binding to all available network interfaces (System.Net.IPAddress.Any)."""

    MAX_HTTP_CONNECTIONS: int = 32
    """Maximum number of concurrent HTTP connections for operations like CAPS."""

    ENABLE_INVENTORY_STORE: bool = True
    """Whether to enable use of the AIS inventory store."""

    ENABLE_LIBRARY_STORE: bool = True
    """Whether to enable use of the AIS library store."""

    PING_INTERVAL: int = 2200  # milliseconds
    """Interval for sending PING_CHECK packets to maintain connection."""

    NETWORK_TICK_INTERVAL: int = 500  # milliseconds
    """Interval for the main network loop that processes packets and events."""

    MAX_PACKET_SIZE: int = 1200 # bytes
    """Maximum size of a UDP packet before it needs to be fragmented or handled as an error."""

    MAX_SEQUENCE: int = 0xFFFFFF
    """Maximum sequence number for UDP packets before wrapping around."""

    PACKET_ARCHIVE_SIZE: int = 1000
    """Number of packets to store in the archive for resend handling."""

    SIMULATOR_POOL_TIMEOUT: int = 2 * 60 * 1000  # milliseconds (2 minutes)
    """Timeout for disconnecting from an inactive simulator in the pool."""

    PIPELINE_REFRESH_INTERVAL: float = 500.0 # milliseconds
    """Interval for refreshing the texture pipeline."""

    LOG_LEVEL: LogLevel = LogLevel.DEBUG
    """Default logging level for the library."""

    SORT_INVENTORY: bool = False
    """Whether to sort inventory items by name."""

    # --- Instance Variables (Configurable per GridClient instance) ---
    def __init__(self, client_ref):
        """
        Initializes the Settings for a GridClient instance.

        Args:
            client_ref: A reference to the GridClient instance this Settings object belongs to.
        """
        self.client_ref = client_ref

        self.login_server: str = self.AGNI_LOGIN_SERVER
        """Login server URI to connect to."""

        self.use_llsd_login: bool = False # In C# this is dynamically set if login URI contains "login.cgi"
        """Whether to use LLSD (XML-RPC) or the older binary protocol for login."""

        self.mfa_enabled: bool = False
        """Whether Multi-Factor Authentication is enabled for the account (detected during login)."""

        self.transfer_timeout: int = 90 * 1000  # ms
        """Timeout for asset transfers (textures, objects, etc.)."""

        self.teleport_timeout: int = 40 * 1000  # ms
        """Timeout for teleport operations."""

        self.logout_timeout: int = 5 * 1000  # ms
        """Timeout for logout requests."""

        self.caps_timeout: int = 60 * 1000  # ms
        """Timeout for individual CAPS HTTP requests."""

        self.login_timeout: int = 60 * 1000 #ms
        """Timeout for the entire login process."""

        self.resend_timeout: int = 4000  # ms
        """Initial timeout for resending unacknowledged packets."""

        self.simulator_timeout: int = 30 * 1000  # ms
        """Timeout for initial connection to a simulator."""

        self.map_request_timeout: int = 5 * 1000 # ms
        """Timeout for map block requests."""

        self.default_agent_update_interval: int = 500  # ms
        """Default interval for sending agent updates (position, etc.). Can be overridden by server."""

        self.interpolation_interval: int = 250 # ms
        """Interval for client-side object interpolation ticks."""

        self.max_pending_acks: int = 10
        """Maximum number of packet acknowledgements to queue before sending."""

        self.stats_queue_size: int = 5
        """Size of the queue for UtilizationStatistics Tracker"""

        self.cache_primitives: bool = False # Not implemented in LibreMetaverse, kept for compatibility
        """Whether to cache primitive data locally."""

        self.pool_parcel_data: bool = False # Not implemented in LibreMetaverse
        """Whether to pool parcel data across simulators."""

        self.store_land_patches: bool = False
        """Whether to store received land patches (terrain heightmaps)."""

        self.send_agent_updates: bool = True
        """Master switch for sending any agent updates."""

        self.send_agent_updates_regularly: bool = True
        """Whether to send agent updates at regular intervals."""

        self.send_agent_appearance: bool = True
        """Whether to send agent appearance information (wearables)."""

        self.send_agent_throttle: bool = True
        """Whether to send agent throttle settings to simulators."""

        self.send_pings: bool = True
        """Whether to send periodic pings to maintain connection."""

        self.multiple_sims: bool = False # Default to False, set to True after successful connection to multiple sims.
        """Whether the client is connected to multiple simulators."""

        self.always_decode_objects: bool = True
        """Whether to always decode object data, even for uninteresting objects."""

        self.always_request_objects: bool = True
        """Whether to always request object data upon seeing an object."""

        self.enable_simstats: bool = True
        """Whether to request and process SimStats from the simulator."""

        self.log_all_caps_errors: bool = False
        """Whether to log all CAPS errors, even if handled."""

        self.disable_agent_update_duplicate_check: bool = True
        """Disable optimization that prevents sending agent updates if data hasn't changed."""

        self.avatar_tracking: bool = True
        """Enable tracking of avatar positions and properties."""

        self.object_tracking: bool = True
        """Enable tracking of object positions and properties."""

        self.use_interpolation_timer: bool = True
        """Use a dedicated timer for object interpolation (smoother movement)."""

        self.track_utilization: bool = False # If True, UtilizationStatistics will be more active
        """Enable tracking of network and resource utilization."""

        self.parcel_tracking: bool = True
        """Enable tracking of parcel information."""

        self.always_request_parcel_acl: bool = True
        """Always request parcel ACL (Access Control List) information."""

        self.always_request_parcel_dwell: bool = True
        """Always request parcel dwell information."""

        self.use_asset_cache: bool = True
        """Enable local caching of downloaded assets."""

        self.asset_cache_dir: str = self.RESOURCE_DIR + "/cache"
        """Directory for the asset cache."""

        self.asset_cache_max_size: int = 1024 * 1024 * 1024 # 1 GiB
        """Maximum size of the asset cache in bytes."""

        # Default color for visual effects like beacons, corrected for Color4 float constructor
        self.default_effect_color: Color4 = Color4(R=1.0, G=0.0, B=0.0, A=1.0) # Red

        self.upload_cost: int = 0 # L$
        """Current cost to upload an asset (dynamically updated)."""

        self.max_resend_count: int = 3
        """Maximum number of times to resend a reliable packet before failing."""

        self.throttle_outgoing_packets: bool = True
        """Enable throttling of outgoing packet rates."""

        self.use_texture_pipeline: bool = True
        """Enable the texture pipeline for downloading and caching textures."""

        self.use_http_textures: bool = True
        """Prefer HTTP for texture downloads if available via capabilities."""

        self.max_concurrent_texture_downloads: int = 4
        """Maximum number of concurrent texture downloads via HTTP."""

        self.pipeline_request_timeout: int = 45 * 1000 # ms
        """Timeout for requests made through the texture pipeline."""

        self.log_names: bool = True
        """Log names of avatars and objects when available."""

        self.log_resends: bool = True
        """Log packet resend events."""

        self.log_diskcache: bool = True
        """Log asset disk cache operations."""

        # From Step 15, ObjectManager settings
        self.ALWAYS_REQUEST_OBJECTS: bool = True
        """If true, the client will send a RequestMultipleObjects for any object
           detailed in an ObjectUpdateCached packet, regardless of local cache state.
           If false, it might only request if object is not found or CRC mismatch (not yet impl)."""


    def _update_upload_cost(self, new_cost: int):
        """
        Callback for NetworkManager to update the current asset upload cost.
        Typically called when EconomyData is received.
        """
        self.upload_cost = new_cost

    # Add other methods or properties as needed, for example,
    # to load/save settings from/to a file, or to dynamically
    # change settings based on grid information.
