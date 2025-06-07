import logging
import asyncio
import dataclasses
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Callable, Optional

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.types.parcel_defs import (
    ParcelInfo, ParcelFlags, ParcelCategory, ParcelStatus, ParcelDwell, ParcelPrimOwnerData,
    ParcelAccessEntry, ParcelACLFlags # Added ACL types
)
from pylibremetaverse.types.enums import PacketType
from pylibremetaverse.network.packets_parcel import (
    ParcelPropertiesRequestPacket, ParcelPropertiesPacket,
    ParcelAccessListRequestPacket, ParcelAccessListReplyPacket # Added ACL packets
)
from pylibremetaverse.utils import helpers

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator
    from pylibremetaverse.network.packets_base import Packet

logger = logging.getLogger(__name__)

@dataclasses.dataclass(slots=True)
class ParcelPropertiesEventArgs:
    parcel: ParcelInfo
    simulator: 'Simulator'

@dataclasses.dataclass(slots=True)
class ParcelAccessListEventArgs:
    parcel_local_id: int
    sequence_id: int
    flags: int # Raw flags from the packet
    access_entries: List[ParcelAccessEntry]
    simulator: 'Simulator'

ParcelPropertiesUpdatedHandler = Callable[[ParcelPropertiesEventArgs], None]
ParcelAccessListUpdatedHandler = Callable[[ParcelAccessListEventArgs], None] # Updated signature
ParcelDwellUpdatedHandler = Callable[[CustomUUID, int, float], None] # Placeholder

class ParcelManager:
    def __init__(self, client: 'GridClient'):
        self.client: 'GridClient' = client
        self.sim_parcels: Dict[CustomUUID, Dict[int, ParcelInfo]] = {}

        self._parcel_properties_updated_handlers: List[ParcelPropertiesUpdatedHandler] = []
        self._parcel_access_list_updated_handlers: List[ParcelAccessListUpdatedHandler] = []
        self._parcel_dwell_updated_handlers: List[ParcelDwellUpdatedHandler] = []

        if self.client.network:
            reg = self.client.network.register_packet_handler
            # is_async=False because handlers directly modify shared state (self.sim_parcels)
            # and then fire events. If it were async, care would be needed for concurrent access.
            reg(PacketType.ParcelProperties, self._on_parcel_properties_wrapper, is_async=False)
            reg(PacketType.ParcelAccessListReply, self._on_parcel_access_list_reply_wrapper, is_async=False) # Added handler
        else:
            logger.error("ParcelManager: NetworkManager not available at init for packet handlers.")

    def _on_parcel_properties_wrapper(self, simulator: 'Simulator', packet: 'Packet'):
        if isinstance(packet, ParcelPropertiesPacket):
            self._on_parcel_properties(simulator, packet)
        else:
            logger.warning(f"ParcelManager: Incorrect packet type {type(packet).__name__} for _on_parcel_properties_wrapper")

    def _on_parcel_access_list_reply_wrapper(self, simulator: 'Simulator', packet: 'Packet'): # Added
        if isinstance(packet, ParcelAccessListReplyPacket):
            self._on_parcel_access_list_reply(simulator, packet)
        else:
            logger.warning(f"ParcelManager: Incorrect packet type {type(packet).__name__} for _on_parcel_access_list_reply_wrapper")

    def register_parcel_properties_updated_handler(self, callback: ParcelPropertiesUpdatedHandler):
        if callback not in self._parcel_properties_updated_handlers:
            self._parcel_properties_updated_handlers.append(callback)

    def unregister_parcel_properties_updated_handler(self, callback: ParcelPropertiesUpdatedHandler):
        if callback in self._parcel_properties_updated_handlers:
            self._parcel_properties_updated_handlers.remove(callback)

    def get_parcel(self, simulator_uuid: CustomUUID, local_id: int) -> Optional[ParcelInfo]:
        return self.sim_parcels.get(simulator_uuid, {}).get(local_id)

    def _fire_parcel_properties_updated(self, args: ParcelPropertiesEventArgs):
        logger.debug(f"Firing parcel_properties_updated for parcel {args.parcel.local_id} ('{args.parcel.name}') in sim {args.simulator.name}")
        for handler in self._parcel_properties_updated_handlers:
            try:
                handler(args)
            except Exception as e: logger.error(f"Error in parcel_properties_updated_handler: {e}", exc_info=True)

    def _fire_parcel_access_list_updated(self, args: ParcelAccessListEventArgs): # Added
        logger.debug(f"Firing parcel_access_list_updated for parcel local_id {args.parcel_local_id} in sim {args.simulator.name}")
        for handler in self._parcel_access_list_updated_handlers:
            try:
                handler(args)
            except Exception as e: logger.error(f"Error in _parcel_access_list_updated handler: {e}", exc_info=True)

    def clear_parcels_for_sim(self, simulator_uuid: CustomUUID):
        if simulator_uuid in self.sim_parcels:
            del self.sim_parcels[simulator_uuid]
            logger.info(f"Cleared all parcel data for simulator {simulator_uuid}")

    async def request_parcel_properties(self, simulator: 'Simulator', position: Vector3,
                                        sequence_id: int = 0, get_selected: bool = False,
                                        snap_selection: bool = False) -> None:
        if not self.client.self or not self.client.self.logged_in:
            logger.warning("Cannot request parcel properties: Agent not logged in or IDs not available.")
            return
        if not simulator or not simulator.connected:
            logger.warning("Cannot request parcel properties: Simulator not available/connected.")
            return

        packet = ParcelPropertiesRequestPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            position_coord=position,
            sequence_id=sequence_id,
            get_selected=get_selected,
            snap_selection=snap_selection
        )
        # packet.header.reliable = True # Already set in packet constructor
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ParcelPropertiesRequest for position {position} in {simulator.name}")

    async def request_parcel_access_list(self, simulator: 'Simulator', parcel_local_id: int,
                                         sequence_id: int = 0, request_flags: int = 0) -> None: # Added
        if not self.client.self or not self.client.self.logged_in:
            logger.warning("Cannot request parcel access list: Agent not logged in or IDs not available.")
            return
        if not simulator or not simulator.connected:
            logger.warning("Cannot request parcel access list: Simulator not available/connected.")
            return

        packet = ParcelAccessListRequestPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            parcel_local_id=parcel_local_id,
            sequence_id=sequence_id,
            request_flags=request_flags
        )
        # packet.header.reliable = True # Already set in packet constructor
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ParcelAccessListRequest for ParcelLocalID {parcel_local_id} in {simulator.name}")

    def _on_parcel_properties(self, source_sim: 'Simulator', packet: ParcelPropertiesPacket):
        pd = packet.parcel_data # This is ParcelPropertiesParcelDataBlock

        if source_sim.uuid not in self.sim_parcels:
            self.sim_parcels[source_sim.uuid] = {}

        parcel_info = self.sim_parcels[source_sim.uuid].get(pd.LocalID)
        if not parcel_info:
            parcel_info = ParcelInfo(local_id=pd.LocalID)

        parcel_info.parcel_uuid = pd.SnapKey
        # Populate ParcelInfo from packet data (rest of the fields)
        parcel_info.owner_id = pd.OwnerID
        parcel_info.is_group_owned = pd.IsGroupOwned
        parcel_info.name = pd.name_str
        parcel_info.description = pd.description_str
        parcel_info.area = pd.ActualArea
        parcel_info.billable_area = pd.BillableArea
        try: parcel_info.flags = ParcelFlags(pd.Flags)
        except ValueError: logger.warning(f"Unknown ParcelFlags value {pd.Flags}"); parcel_info.flags = ParcelFlags(pd.Flags) # Keep raw if unknown
        try: parcel_info.status = ParcelStatus(pd.Status)
        except ValueError: logger.warning(f"Unknown ParcelStatus value {pd.Status}"); parcel_info.status = ParcelStatus.UNKNOWN
        try: parcel_info.category = ParcelCategory(pd.Category)
        except ValueError: logger.warning(f"Unknown ParcelCategory value {pd.Category}"); parcel_info.category = ParcelCategory.UNKNOWN
        parcel_info.sale_price = pd.SalePrice
        parcel_info.auction_id = pd.AuctionID
        parcel_info.snapshot_id = pd.SnapshotID
        parcel_info.landing_type = pd.LandingType
        parcel_info.media_url = pd.media_url_str
        parcel_info.media_content_type = pd.media_type_str
        parcel_info.media_width = pd.MediaWidth
        parcel_info.media_height = pd.MediaHeight
        parcel_info.media_loop = pd.MediaLoop
        parcel_info.music_url = pd.music_url_str
        parcel_info.pass_hours = pd.PassHours
        parcel_info.pass_price = pd.PassPrice
        parcel_info.auth_buyer_id = pd.AuthBuyerID
        parcel_info.global_x = pd.GlobalX
        parcel_info.global_y = pd.GlobalY
        parcel_info.global_z = pd.GlobalZ
        parcel_info.sim_name = pd.sim_name_str
        if pd.RegionUUID != CustomUUID.ZERO:
            parcel_info.region_handle = helpers.region_uuid_to_handle(pd.RegionUUID, pd.GlobalX, pd.GlobalY)
        else:
            parcel_info.region_handle = helpers.coords_to_region_handle(int(pd.GlobalX / 256.0), int(pd.GlobalY / 256.0))
        parcel_info.prim_owners = list(pd.PrimOwners)

        self.sim_parcels[source_sim.uuid][parcel_info.local_id] = parcel_info
        logger.info(f"Processed ParcelProperties for L:{parcel_info.local_id} ('{parcel_info.name}') in {source_sim.name}, UUID:{parcel_info.parcel_uuid}, PrimOwners: {len(parcel_info.prim_owners)}")
        self._fire_parcel_properties_updated(ParcelPropertiesEventArgs(parcel_info, source_sim))

    def _on_parcel_access_list_reply(self, source_sim: 'Simulator', packet: ParcelAccessListReplyPacket): # Added
        db = packet.data_block
        parcel_info = self.get_parcel(source_sim.uuid, db.ParcelLocalID)

        entries = []
        for acc_block in packet.access_data_blocks:
            try:
                acl_flags = ParcelACLFlags(acc_block.AccessFlags)
            except ValueError:
                logger.warning(f"Unknown ParcelACLFlags value {acc_block.AccessFlags} for agent {acc_block.ID} on parcel {db.ParcelLocalID}")
                acl_flags = ParcelACLFlags(acc_block.AccessFlags) # Keep raw if unknown
            entries.append(ParcelAccessEntry(agent_id=acc_block.ID, time=acc_block.Time, flags=acl_flags))

        if parcel_info:
            parcel_info.access_list = entries
            logger.info(f"Updated access list for parcel L:{db.ParcelLocalID} ('{parcel_info.name}') in {source_sim.name}, {len(entries)} entries.")
        else:
            logger.warning(f"Received ParcelAccessListReply for unknown parcel LocalID {db.ParcelLocalID} in sim {source_sim.uuid}. Storing ACL data separately for now.")
            # Potentially store separately or handle if ParcelInfo might arrive later
            # For now, we'll just fire the event with the data we have.

        self._fire_parcel_access_list_updated(
            ParcelAccessListEventArgs(
                parcel_local_id=db.ParcelLocalID,
                sequence_id=db.SequenceID,
                flags=db.Flags,
                access_entries=entries,
                simulator=source_sim
            )
        )

    def register_parcel_access_list_updated_handler(self, callback: ParcelAccessListUpdatedHandler): # Signature updated
        if callback not in self._parcel_access_list_updated_handlers:
            self._parcel_access_list_updated_handlers.append(callback)

    def unregister_parcel_access_list_updated_handler(self, callback: ParcelAccessListUpdatedHandler): # Signature updated
        if callback in self._parcel_access_list_updated_handlers:
            self._parcel_access_list_updated_handlers.remove(callback)

    def register_parcel_dwell_updated_handler(self, callback: ParcelDwellUpdatedHandler):
        if callback not in self._parcel_dwell_updated_handlers: self._parcel_dwell_updated_handlers.append(callback)
    def unregister_parcel_dwell_updated_handler(self, callback: ParcelDwellUpdatedHandler):
        if callback in self._parcel_dwell_updated_handlers: self._parcel_dwell_updated_handlers.remove(callback)

if __name__ == '__main__':
    print("ParcelManager with request and properties handling defined.")
    # Conceptual test
    class MockSim: name = "TestSim"; uuid = CustomUUID.random(); connected = True; handle = 0; parcels = None
    class MockAgent: agent_id = CustomUUID.random(); session_id = CustomUUID.random(); logged_in = True
    class MockNetwork:
        _handlers = {}
        def register_packet_handler(self, pt, cb, ia=False): self._handlers[pt] = cb
        async def send_packet(self, p, sim): print(f"MockSend: {type(p).__name__} to {sim.name}")
    class MockClient: self = MockAgent(); network = MockNetwork(); parcels = None

    mock_client = MockClient()
    pm = ParcelManager(mock_client) # This will register handlers
    mock_client.parcels = pm

    def test_prop_handler(args: ParcelPropertiesEventArgs): print(f"Handler: ParcelProps '{args.parcel.name}' in {args.simulator.name}")
    pm.register_parcel_properties_updated_handler(test_prop_handler)
    def test_acl_handler(args: ParcelAccessListEventArgs): print(f"Handler: ParcelACL for L:{args.parcel_local_id}, {len(args.access_entries)} entries in {args.simulator.name}")
    pm.register_parcel_access_list_updated_handler(test_acl_handler)

    mock_sim_obj = MockSim()

    # Test ParcelProperties
    prop_packet = ParcelPropertiesPacket()
    prop_packet.parcel_data.LocalID = 100
    prop_packet.parcel_data.Name = b"My Test Parcel\0"
    # ... fill more prop_packet fields ...
    pm._on_parcel_properties(mock_sim_obj, prop_packet)
    retrieved_parcel = pm.get_parcel(mock_sim_obj.uuid, 100)
    assert retrieved_parcel is not None and retrieved_parcel.name == "My Test Parcel"
    print(f"Retrieved: {retrieved_parcel}")

    # Test ParcelAccessList
    acl_packet = ParcelAccessListReplyPacket()
    acl_packet.data_block.ParcelLocalID = 100
    acl_packet.data_block.SequenceID = 1
    acl_packet.access_data_blocks.append(ParcelAccessListReplyAccessDataBlock(ID=CustomUUID.random(), Time=0, AccessFlags=ParcelACLFlags.ALLOWED.value))
    acl_packet.access_data_blocks.append(ParcelAccessListReplyAccessDataBlock(ID=CustomUUID.random(), Time=0, AccessFlags=ParcelACLFlags.BANNED.value | ParcelACLFlags.GROUP.value))
    pm._on_parcel_access_list_reply(mock_sim_obj, acl_packet)
    assert retrieved_parcel.access_list is not None and len(retrieved_parcel.access_list) == 2
    print(f"Retrieved Parcel with ACL: {retrieved_parcel}")

    async def run_requests():
        await pm.request_parcel_properties(mock_sim_obj, Vector3(128,128,20))
        await pm.request_parcel_access_list(mock_sim_obj, 100)
    asyncio.run(run_requests())

    print("ParcelManager test conceptualized.")
