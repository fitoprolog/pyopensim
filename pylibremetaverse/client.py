import logging
# import requests # For actual HTTP requests later

from .managers import (
    NetworkManager, Settings, ParcelManager, AgentManager, AvatarManager,
    EstateTools, FriendsManager, GridManager, ObjectManager, GroupManager,
    InventoryAISClient, AppearanceManager,
    DirectoryManager, TerrainManager, SoundManager, AgentThrottle,
    InventoryManager, AssetManager # Ensure AssetManager is imported
)
from .network import HttpCapsClient
from .stats import UtilizationStatistics
from .types import CustomUUID

logger = logging.getLogger(__name__)

class GridClient:
    def __init__(self):
        logger.info("GridClient initializing...")

        # Core Managers first
        self.settings = Settings(self)
        self.network = NetworkManager(self)
        self.throttle = AgentThrottle(self)
        self.objects = ObjectManager(self)
        self.assets = AssetManager(self) # Instantiate AssetManager
        self.inventory = InventoryManager(self) # Instantiate InventoryManager

        # Agent-related (AgentManager often initializes other agent-specific sub-managers)
        self.self = AgentManager(self) # AgentManager uses self.client.inventory, self.client.assets etc.

        # Other world-related managers
        self.avatars = AvatarManager(self) # Manages other avatars
        self.parcels = ParcelManager(self)
        self.grid = GridManager(self)
        self.estate = EstateTools(self)
        self.terrain = TerrainManager(self)

        # Social and content managers
        self.friends = FriendsManager(self)
        self.groups = GroupManager(self)

        # Inventory AIS (alternative inventory access, if needed)
        self.inventory_ais = InventoryAISClient(self)

        # Other utility managers
        self.directory = DirectoryManager(self)
        self.sound = SoundManager(self)

        # Statistics & HTTP
        self.stats = UtilizationStatistics()
        self.http_caps_client: HttpCapsClient | None = None # Setup by NetworkManager after login via _setup_http_caps_client
        self._setup_http_caps_client() # Initial setup, might be reconfigured after login

        # Register FriendsManager IM handler with AgentManager
        if self.self and self.friends:
            # Assuming AgentManager (self.self) has register_im_handler
            # and FriendsManager has _handle_im_for_friendship
            self.self.register_im_handler(self.friends._handle_im_for_friendship)
            logger.debug("Registered FriendsManager IM handler with AgentManager.")
        else:
            logger.warning("Could not register FriendsManager IM handler: AgentManager or FriendsManager not available.")

        logger.info("GridClient initialized with all managers.")

    def _setup_http_caps_client(self):
        logger.debug("Setting up HttpCapsClient...")
        handler_settings_obj = self.settings # Settings should be available
        # In a real implementation, a requests.Session would be created and configured here.
        # For now, HttpCapsClient stub just stores settings.
        self.http_caps_client = HttpCapsClient(handler_settings_obj)
        logger.debug(f"HttpCapsClient created/updated with settings from: {type(handler_settings_obj).__name__}")

    def __str__(self) -> str:
        if self.self and self.self.name and self.self.name != "Unknown Agent":
            return f"GridClient(Agent: {self.self.name})"
        return "GridClient(No Agent Name)"

    async def connect_to_grid(self, login_params_dict: dict): # Placeholder for user-friendly connect
        """
        User-friendly method to connect to a grid.
        Takes a dictionary of login parameters.
        """
        # Example: login_params_dict = {"first": "Test", "last": "Bot", "pass": "pass", ...}
        success = await self.network.login(
            first_name=login_params_dict.get("first", ""),
            last_name=login_params_dict.get("last", ""),
            password=login_params_dict.get("pass", ""),
            channel=login_params_dict.get("channel", "PyLibreMetaverse"),
            version=login_params_dict.get("version", "0.1.0"),
            start_location=login_params_dict.get("start", "last"),
            login_uri_override=login_params_dict.get("uri")
            # Add other params like token, mfa_hash if needed
        )
        return success

    async def disconnect(self):
        logger.info("GridClient disconnect requested.")
        await self.network.logout() # Logout handles sim disconnects and task cleanup.
        logger.info("GridClient disconnect completed.")

# Example usage (for testing stub structure)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    client = GridClient()
    print(client)
    if client.settings: print(f"Settings User-Agent: {client.settings.USER_AGENT}")
    # To test login:
    # params = {"first":"Test", "last":"Bot", "pass":"password"}
    # asyncio.run(client.connect_to_grid(params))
    # asyncio.run(asyncio.sleep(10)) # Keep alive for a bit
    # asyncio.run(client.disconnect())
