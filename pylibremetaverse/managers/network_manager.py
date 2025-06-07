import asyncio
import logging
import hashlib
import time
from typing import Callable, List, Dict, Any # Use List, Dict, Any from typing

from pylibremetaverse.network.login_defs import (
    LoginStatus, LoginParams, LoginResponseData, LoginCredential, LastExecStatus
)
from pylibremetaverse.network.simulator import Simulator
from pylibremetaverse.types import CustomUUID
from pylibremetaverse.structured_data import (
    OSDMap, OSDString, OSDBoolean, OSDInteger, OSDArray,
    serialize_llsd_xml, python_to_osd
)
from pylibremetaverse import utils as plm_utils
from pylibremetaverse.network.packets_base import Packet, PacketType, PacketHeader, PacketFlags
from pylibremetaverse.network.packets_control import (
    UseCircuitCodePacket, RegionHandshakePacket, RegionHandshakeReplyPacket,
    CompleteAgentMovementPacket, AgentThrottlePacket, EconomyDataRequestPacket
)
from pylibremetaverse.network.packet_protocol import IncomingPacket

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# --- Type Aliases for Callbacks (Assuming Synchronous for now) ---
LoginProgressHandler = Callable[[LoginStatus, str, str], None]
SimConnectionHandler = Callable[[Simulator], None]
SimDisconnectionHandler = Callable[[Simulator, bool], None] # simulator, requested_logout
NetworkDisconnectedHandler = Callable[[str], None] # reason: str
PacketHandler = Callable[[Simulator, Packet], None]


class NetworkManager:
    def __init__(self, client_ref):
        self.client = client_ref # GridClient instance
        self.simulators: List[Simulator] = []
        self.current_sim: Simulator | None = None
        self.connected: bool = False
        self.logged_in: bool = False

        self.circuit_code: int = 0
        self.agent_id: CustomUUID = CustomUUID.ZERO
        self.session_id: CustomUUID = CustomUUID.ZERO
        self.secure_session_id: CustomUUID = CustomUUID.ZERO

        self.login_status: LoginStatus = LoginStatus.NONE
        self.login_message: str = ""
        self.login_error_key: str = ""
        self.login_seed_capability: str | None = None
        self.login_response_data: LoginResponseData | None = None

        self.packet_inbox: asyncio.Queue[IncomingPacket] = asyncio.Queue()
        self.packet_event_handlers: Dict[PacketType, List[PacketHandler]] = {}
        self.caps_event_handlers: Dict[str, List[Callable[[Any], None]]] = {}

        self._login_progress_handlers: List[LoginProgressHandler] = []
        self._logged_out_handlers: List[Callable[[], None]] = []
        self._sim_connected_handlers: List[SimConnectionHandler] = []
        self._sim_disconnected_handlers: List[SimDisconnectionHandler] = []
        self._disconnected_handlers: List[NetworkDisconnectedHandler] = []
        self._packet_processing_task: asyncio.Task | None = None

    async def login(self, first_name: str, last_name: str, password: str,
                    channel: str, version: str, start_location: str = "last",
                    login_uri_override: str | None = None,
                    token: str = "", mfa_hash: str = "") -> bool:
        if not first_name or not last_name or (not password and not token):
            self._update_login_status(LoginStatus.FAILED, "Credentials missing.")
            return False
        password_md5 = "$1$" + hashlib.md5(password.encode('utf-8')).hexdigest() if not token and password else ""
        credential = LoginCredential(first_name, last_name, password_md5, token, mfa_hash)
        login_params = LoginParams(self.client, credential, channel, version, login_uri_override, start_location, self.client.settings.login_timeout)
        self._update_login_status(LoginStatus.CONNECTING_TO_LOGIN, f"Connecting to {login_params.login_uri}...")
        if not httpx: self._update_login_status(LoginStatus.FAILED, "HTTP library missing."); return False
        self.login_response_data = LoginResponseData()
        if not self.client.settings.use_llsd_login: self._update_login_status(LoginStatus.FAILED, "XML-RPC login N/A."); return False

        try:
            login_data_dict = { "first": login_params.first_name, "last": login_params.last_name, "passwd": login_params.password_md5,
                                "start": login_params.start_location, "channel": login_params.channel, "version": login_params.version,
                                "platform": login_params.platform, "platform_version": login_params.platform_version,
                                "mac": login_params.mac, "id0": login_params.id0, "options": login_params.options, }
            if login_params.token: login_data_dict["token"] = login_params.token
            if login_params.mfa_hash: login_data_dict["mfa_token"] = login_params.mfa_hash; login_data_dict["mfa_type"] = "totp"
            llsd_payload = serialize_llsd_xml(python_to_osd(login_data_dict))
            self._update_login_status(LoginStatus.READING_RESPONSE, "Sending LLSD login...")
            async with httpx.AsyncClient(timeout=login_params.timeout_ms / 1000.0) as http_client:
                response = await http_client.post(login_params.login_uri, content=llsd_payload, headers={'Content-Type': 'application/llsd+xml', 'User-Agent': self.client.settings.USER_AGENT})
            if response.status_code != 200:
                self._update_login_status(LoginStatus.FAILED, f"Login HTTP Error: {response.status_code}", "http_error"); return False

            self.login_response_data.parse_llsd(response.content)
            if not self.login_response_data.success:
                self._update_login_status(LoginStatus.FAILED, self.login_response_data.message or "Login failed.", self.login_response_data.reason); return False

            self.agent_id = self.login_response_data.agent_id; self.session_id = self.login_response_data.session_id
            self.secure_session_id = self.login_response_data.secure_session_id; self.circuit_code = self.login_response_data.circuit_code
            self.login_seed_capability = self.login_response_data.seed_capability
            self.client.self.AgentID = self.agent_id; self.client.self.SessionID = self.session_id
            self.client.self.SecureSessionID = self.secure_session_id; self.client.self.CircuitCode = self.circuit_code
            self.client.self.SeedCapability = self.login_seed_capability
            self.client.self.name = f"{self.login_response_data.first_name} {self.login_response_data.last_name}"
            self._update_login_status(LoginStatus.CONNECTING_TO_SIM, f"Login successful: {self.login_response_data.message}. Connecting to sim...")

            sim_ip = str(self.login_response_data.sim_ip) if self.login_response_data.sim_ip else None
            if not sim_ip or not self.login_response_data.sim_port:
                self._update_login_status(LoginStatus.FAILED, "No sim address in login response."); return False

            self._start_packet_processing()
            region_handle = plm_utils.uints_to_long(self.login_response_data.region_x, self.login_response_data.region_y)

            connected_sim = await self.connect_to_sim(sim_ip, self.login_response_data.sim_port, region_handle, True,
                                                      self.login_seed_capability, self.login_response_data.region_size_x,
                                                      self.login_response_data.region_size_y)
            if connected_sim: # connect_to_sim now calls _start_network_tasks on the sim
                self._update_login_status(LoginStatus.SUCCESS, self.login_response_data.message or "Connected to grid.")
                self.logged_in = True; self.connected = True
                return True
            else:
                return False
        except httpx.RequestError as e: self._update_login_status(LoginStatus.FAILED, f"Network error: {e}", "network_error"); return False
        except Exception as e: logger.exception("LLSD login error"); self._update_login_status(LoginStatus.FAILED, f"Error: {e}", "exception"); return False


    async def connect_to_sim(self, ip_addr_str: str, port: int, handle: int, is_default: bool,
                             seed_caps_url: str | None, region_size_x: int, region_size_y: int) -> Simulator | None:
        logger.info(f"Connecting to sim: {ip_addr_str}:{port}, Default: {is_default}")
        sim = Simulator(self, ip_addr_str, port, handle, region_size_x, region_size_y)
        if not await sim.connect(is_default):
            self._update_login_status(LoginStatus.FAILED, f"UDP endpoint setup failed for {sim.name}.")
            return None

        sim._start_network_tasks() # Start ACK and Resend loops for this sim.

        self.simulators.append(sim)
        if not self._packet_processing_task or self._packet_processing_task.done():
            self._start_packet_processing()

        try:
            use_circuit = UseCircuitCodePacket(self.circuit_code, self.session_id, self.agent_id)
            use_circuit.header.reliable = True
            await sim.send_packet(use_circuit)

            rhr_packet = await self._wait_for_packet_type(PacketType.RegionHandshake, sim, timeout=15.0)
            if not rhr_packet or not isinstance(rhr_packet, RegionHandshakePacket):
                raise asyncio.TimeoutError("RegionHandshake not received or wrong type.")

            await self._handle_region_handshake(rhr_packet, sim)

            if is_default: self.current_sim = sim
            if seed_caps_url and self.client.http_caps_client and not self.client.http_caps_client.caps_url:
                self.client.http_caps_client.caps_url = seed_caps_url

            logger.info(f"Successfully handshaked with {sim.name}")
            return sim
        except asyncio.TimeoutError: msg = f"Timeout during handshake with {sim.name}."
        except Exception as e: msg = f"Error during handshake with {sim.name}: {e}"; logger.exception(msg)

        self._update_login_status(LoginStatus.FAILED, msg if 'msg' in locals() else "Sim handshake failed.")
        await sim.disconnect(send_close_circuit=False)
        if sim in self.simulators: self.simulators.remove(sim)
        return None

    async def _wait_for_packet_type(self, packet_type: PacketType, simulator: Simulator, timeout: float = 10.0) -> Packet | None:
        start_time = time.monotonic()
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout: raise asyncio.TimeoutError(f"Timeout waiting for {packet_type.name}")
            try:
                incoming: IncomingPacket = await asyncio.wait_for(self.packet_inbox.get(), timeout=timeout - elapsed)
                if incoming.simulator == simulator and incoming.packet.type == packet_type:
                    return incoming.packet
                else:
                    self.packet_inbox.put_nowait(incoming); await asyncio.sleep(0.01)
            except asyncio.TimeoutError: raise

    async def _handle_region_handshake(self, packet: RegionHandshakePacket, sim: Simulator):
        sim.name = packet.sim_name_str; sim.id = packet.region_id
        logger.info(f"Handling RegionHandshake from {sim.name} (ID: {sim.id}). SimFlags: {packet.region_flags}")

        reply = RegionHandshakeReplyPacket(self.agent_id, self.session_id, flags=0x1 | 0x2 | 0x4)
        reply.header.reliable = True; await sim.send_packet(reply)

        move = CompleteAgentMovementPacket(self.agent_id, self.session_id, self.circuit_code)
        move.header.reliable = True; await sim.send_packet(move)

        default_throttles_payload = b'\x00' * AgentThrottlePacket.THROTTLE_BUFFER_SIZE
        throttle_packet = AgentThrottlePacket(default_throttles_payload)
        throttle_packet.header.reliable = True; await sim.send_packet(throttle_packet)

        econ_packet = EconomyDataRequestPacket()
        econ_packet.header.reliable = True; await sim.send_packet(econ_packet)

        sim.handshake_complete = True
        if self.current_sim == sim: self.connected = True

        for handler in self._sim_connected_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): await handler(sim)
                else: handler(sim)
            except Exception as e: logger.error(f"Error in _sim_connected_handler: {e}")

    async def _incoming_packet_processor(self):
        logger.info("Incoming packet processor task started.")
        try:
            while True:
                if not self.connected and self.packet_inbox.empty():
                    if not self.client.settings.ENABLE_SIMSTATS: break
                    await asyncio.sleep(0.1); continue
                try:
                    incoming: IncomingPacket = await asyncio.wait_for(self.packet_inbox.get(), timeout=1.0)
                    packet = incoming.packet; source_sim = incoming.simulator
                    logger.debug(f"Processing {packet.type.name} (Seq={packet.header.sequence}) from {source_sim.name}")
                    if packet.type == PacketType.RegionHandshake and not source_sim.handshake_complete:
                        await self._handle_region_handshake(packet, source_sim); continue
                    if packet.type in self.packet_event_handlers:
                        for cb in self.packet_event_handlers[packet.type]:
                            try:
                                if asyncio.iscoroutinefunction(cb): await cb(source_sim, packet)
                                else: cb(source_sim, packet)
                            except Exception as e: logger.error(f"Error in {packet.type.name} handler: {e}")
                    else: logger.debug(f"No handler for {packet.type.name}")
                except asyncio.TimeoutError: continue
                except Exception as e: logger.exception("Packet processing loop error"); await asyncio.sleep(0.1)
        except asyncio.CancelledError: logger.info("Incoming packet processor task cancelled.")
        finally: logger.info("Incoming packet processor stopped.")

    def _start_packet_processing(self):
        if not self._packet_processing_task or self._packet_processing_task.done():
            self._packet_processing_task = asyncio.create_task(self._incoming_packet_processor())
    def _stop_packet_processing(self):
        if self._packet_processing_task and not self._packet_processing_task.done():
            self._packet_processing_task.cancel()
        self._packet_processing_task = None

    async def logout(self):
        logger.info("logout() called.")
        await self._stop_packet_processing()
        for sim in list(self.simulators): await sim.disconnect()
        self.simulators.clear()
        if self.client.http_caps_client: self.client.http_caps_client.disconnect(logout=True)
        self.logged_in = False; self.connected = False; self.current_sim = None
        self._update_login_status(LoginStatus.NONE, "Logged out.")
        for handler in self._logged_out_handlers:
            try:
                if asyncio.iscoroutinefunction(handler): await handler()
                else: handler()
            except Exception as e: logger.error(f"Error in _logged_out_handler: {e}")

    def shutdown(self, reason_type: str = "Unknown", message: str = ""):
        logger.info(f"shutdown(reason='{reason_type}') called.")
        async def _shutdown_async():
            await self._stop_packet_processing()
            for sim in list(self.simulators): await sim.disconnect(send_close_circuit=False)
            self.simulators.clear()
            if self.client.http_caps_client: self.client.http_caps_client.disconnect(logout=False)
            self.logged_in = False; self.connected = False; self.current_sim = None
            self._update_login_status(LoginStatus.NONE, f"Shutdown: {reason_type} - {message}")
            for handler in self._disconnected_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler): await handler(reason_type)
                    else: handler(reason_type)
                except Exception as e: logger.error(f"Error in _disconnected_handler: {e}")
        if asyncio.get_event_loop().is_running(): asyncio.create_task(_shutdown_async())
        else: asyncio.run(_shutdown_async())

    async def send_packet(self, packet: Packet, simulator: Simulator | None = None, set_sequence: bool = True):
        target_sim = simulator if simulator else self.current_sim
        if not target_sim or not target_sim.connected:
            logger.warning(f"NM: Cannot send {type(packet).__name__}, no/disconnected sim.")
            return
        await target_sim.send_packet(packet, set_sequence=set_sequence)

    def _update_login_status(self, status: LoginStatus, message: str, error_key: str = ""):
        self.login_status = status; self.login_message = message; self.login_error_key = error_key
        logger.info(f"Login status: {status.name} - {message} (Key: {error_key or 'N/A'})") # Use .name for enum
        for handler in self._login_progress_handlers:
            try: handler(status, message, error_key)
            except Exception as e: logger.error(f"Error in login_progress_handler: {e}")

    def register_login_progress_handler(self, cb: LoginProgressHandler): self._login_progress_handlers.append(cb)
    def unregister_login_progress_handler(self, cb: LoginProgressHandler):
        if cb in self._login_progress_handlers: self._login_progress_handlers.remove(cb)

    def register_logged_out_handler(self, cb: Callable[[], None]): self._logged_out_handlers.append(cb)
    def unregister_logged_out_handler(self, cb: Callable[[], None]):
        if cb in self._logged_out_handlers: self._logged_out_handlers.remove(cb)

    def register_sim_connected_handler(self, cb: SimConnectionHandler): self._sim_connected_handlers.append(cb)
    def unregister_sim_connected_handler(self, cb: SimConnectionHandler):
        if cb in self._sim_connected_handlers: self._sim_connected_handlers.remove(cb)

    def register_sim_disconnected_handler(self, cb: SimDisconnectionHandler): self._sim_disconnected_handlers.append(cb)
    def unregister_sim_disconnected_handler(self, cb: SimDisconnectionHandler):
        if cb in self._sim_disconnected_handlers: self._sim_disconnected_handlers.remove(cb)

    def register_disconnected_handler(self, cb: NetworkDisconnectedHandler): self._disconnected_handlers.append(cb)
    def unregister_disconnected_handler(self, cb: NetworkDisconnectedHandler):
        if cb in self._disconnected_handlers: self._disconnected_handlers.remove(cb)

    def register_packet_handler(self, packet_type: PacketType, callback: PacketHandler):
        if packet_type not in self.packet_event_handlers:
            self.packet_event_handlers[packet_type] = []
        if callback not in self.packet_event_handlers[packet_type]:
            self.packet_event_handlers[packet_type].append(callback)

    def unregister_packet_handler(self, packet_type: PacketType, callback: PacketHandler):
        if packet_type in self.packet_event_handlers and callback in self.packet_event_handlers[packet_type]:
            self.packet_event_handlers[packet_type].remove(callback)

    async def _on_sim_disconnected(self, sim: Simulator, requested_logout: bool):
        logger.info(f"NM notified of disconnect from {sim.name}, logout={requested_logout}")
        if sim in self.simulators: self.simulators.remove(sim)
        if self.current_sim == sim:
            self.current_sim = None
            if not requested_logout and self.logged_in:
                self.connected = False
                logger.warning(f"Unexpected disconnect from current sim {sim.name}")
                for handler in self._disconnected_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler): await handler("SimUnexpectedDisconnect")
                        else: handler("SimUnexpectedDisconnect")
                    except Exception as e: logger.error(f"Error in _disconnected_handler: {e}")
        for handler in self._sim_disconnected_handlers:
            try: # Pass (sim, requested_logout)
                if asyncio.iscoroutinefunction(handler): await handler(sim, requested_logout)
                else: handler(sim, requested_logout)
            except Exception as e: logger.error(f"Error in _sim_disconnected_handler: {e}")
        if not self.simulators and self.logged_in and not requested_logout:
             self.connected = False
             for handler in self._disconnected_handlers:
                 try:
                     if asyncio.iscoroutinefunction(handler): await handler("AllSimsDisconnected")
                     else: handler("AllSimsDisconnected")
                 except Exception as e: logger.error(f"Error in _disconnected_handler: {e}")
