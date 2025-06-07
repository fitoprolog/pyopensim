import asyncio
import socket
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Tuple, List

from pylibremetaverse.types import CustomUUID, Vector3
from .packet_protocol import PacketProtocol
from .packets_base import Packet, PacketFlags, PacketHeader


if TYPE_CHECKING:
    from pylibremetaverse.managers.network_manager import NetworkManager
    from pylibremetaverse.client import GridClient

logger = logging.getLogger(__name__)

RESEND_TIMEOUT_FACTOR = 3.0
RESEND_MAX_COUNT = 3
ACK_BATCH_DELAY = 0.05
ACK_MAX_BATCH = 10

class Simulator:
    def __init__(self, network_manager_ref: 'NetworkManager',
                 ip_addr_str: str, port: int, handle: int,
                 region_size_x: int, region_size_y: int):
        self.network_manager = network_manager_ref
        self.client: 'GridClient' = network_manager_ref.client

        self.ip_addr_str: str = ip_addr_str; self.port: int = port
        self.handle: int = handle; self.id: CustomUUID = CustomUUID.ZERO
        self.region_size_x: int = region_size_x; self.region_size_y: int = region_size_y
        self.name: str = f"Unknown ({self.handle})"
        self.sim_version: str = "" # Added, set by AgentMovementComplete

        self.connected: bool = False; self.handshake_complete: bool = False
        self.agent_movement_complete: bool = False # Added: True after AgentMovementComplete received
        self.sequence_number: int = 0

        self.ack_inbox: Dict[int, float] = {}
        self.ack_queue: asyncio.Queue[int] = asyncio.Queue()
        self.need_ack: Dict[int, Tuple[Packet, float, int]] = {}

        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: PacketProtocol | None = None

        self.ack_task: asyncio.Task | None = None
        self.resend_task: asyncio.Task | None = None

        self.stats_last_packets_in: int = 0; self.stats_last_packets_out: int = 0

    async def connect(self, is_default: bool) -> bool:
        logger.info(f"[{self}] connect(is_default={is_default}) called.")
        if self.transport and self.connected: return True
        loop = asyncio.get_running_loop()
        try:
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                lambda: PacketProtocol(self), remote_addr=(self.ip_addr_str, self.port)
            )
            self.connected = True
            # _start_network_tasks is called by NetworkManager after connect_to_sim succeeds
            logger.info(f"[{self}] UDP endpoint setup initiated for {self.ip_addr_str}:{self.port}.")
            return True
        except Exception as e:
            logger.error(f"[{self}] Failed to create UDP endpoint: {e}")
            self.connected = False; self.transport = None; self.protocol = None
            return False

    async def disconnect(self, send_close_circuit: bool = True):
        logger.info(f"[{self}] disconnect(send_close_circuit={send_close_circuit}) called.")
        await self._stop_network_tasks()
        if send_close_circuit and self.connected and self.transport:
            from .packets_control import CloseCircuitPacket
            try:
                await self.send_packet(CloseCircuitPacket(), set_sequence=False)
                logger.debug(f"[{self}] Sent CloseCircuitPacket.")
                await asyncio.sleep(0.05)
            except Exception as e: logger.error(f"[{self}] Error sending CloseCircuitPacket: {e}")

        if self.transport:
            try: self.transport.close()
            except Exception as e: logger.error(f"[{self}] Error during transport.close(): {e}")

        self.connected = False; self.handshake_complete = False
        self.agent_movement_complete = False # Reset on disconnect
        logger.info(f"[{self}] Disconnect process completed on Simulator side.")

    def queue_ack(self, sequence_number: int):
        self.ack_queue.put_nowait(sequence_number)
        logger.debug(f"[{self}] Queued ACK for sequence {sequence_number}.")

    async def _send_acks_loop(self):
        logger.debug(f"[{self}] ACK sending loop started.")
        try:
            while self.connected:
                acks_to_send: List[int] = []
                try:
                    first_ack = await asyncio.wait_for(self.ack_queue.get(), timeout=ACK_BATCH_DELAY)
                    acks_to_send.append(first_ack)
                    while len(acks_to_send) < ACK_MAX_BATCH:
                        try: acks_to_send.append(self.ack_queue.get_nowait())
                        except asyncio.QueueEmpty: break
                except asyncio.TimeoutError: pass

                if acks_to_send:
                    from .packets_control import AckPacket
                    ack_packet = AckPacket(sequences=acks_to_send)
                    await self.send_packet(ack_packet, set_sequence=True)
                    logger.debug(f"[{self}] Sent AckPacket for {len(acks_to_send)} sequences: {acks_to_send}")

                if not acks_to_send : await asyncio.sleep(ACK_BATCH_DELAY)
        except asyncio.CancelledError: logger.info(f"[{self}] ACK sending loop cancelled.")
        except Exception as e: logger.exception(f"[{self}] ACK sending loop error: {e}")
        finally: logger.debug(f"[{self}] ACK sending loop stopped.")

    async def _resend_loop(self):
        logger.debug(f"[{self}] Resend loop started.")
        try:
            resend_timeout_secs = self.client.settings.resend_timeout / 1000.0
            max_resends = self.client.settings.max_resend_count
            while self.connected:
                current_time = time.monotonic(); packets_to_resend = []
                for seq, (packet, time_sent, resend_count) in list(self.need_ack.items()):
                    if current_time - time_sent > resend_timeout_secs * (resend_count + 1) * RESEND_TIMEOUT_FACTOR:
                        if resend_count >= max_resends:
                            logger.error(f"[{self}] Max resends for packet Seq={seq}, Type={packet.type.name}. Giving up.")
                            del self.need_ack[seq]
                            # TODO: Trigger disconnect or notify critical failure
                            continue
                        logger.warning(f"[{self}] Resending packet Seq={seq}, Type={packet.type.name}, Count={resend_count + 1}")
                        packet.header.flags |= PacketFlags.RESENT
                        packets_to_resend.append(packet)
                        self.need_ack[seq] = (packet, current_time, resend_count + 1)
                for p_to_resend in packets_to_resend:
                    await self.send_packet(p_to_resend, set_sequence=False)
                await asyncio.sleep(resend_timeout_secs / 3.0)
        except asyncio.CancelledError: logger.info(f"[{self}] Resend loop cancelled.")
        except Exception as e: logger.exception(f"[{self}] Resend loop error: {e}")
        finally: logger.debug(f"[{self}] Resend loop stopped.")

    async def send_packet(self, packet: Packet, set_sequence: bool = True):
        if not self.transport or not self.connected:
            logger.warning(f"[{self}] Sim not connected, cannot send {type(packet).__name__}")
            return
        if set_sequence and not (packet.header.flags & PacketFlags.ACK):
            max_seq = self.client.settings.MAX_SEQUENCE
            self.sequence_number = (self.sequence_number + 1) & max_seq
            packet.header.sequence = self.sequence_number
        if packet.header.reliable and not (packet.header.flags & PacketFlags.ACK):
            self.need_ack[packet.header.sequence] = (packet, time.monotonic(), 0)
        try:
            max_size = self.client.settings.MAX_PACKET_SIZE
            data_to_send = packet.to_bytes_with_header(max_packet_size=max_size)
            self.transport.sendto(data_to_send)
            if self.client.settings.track_utilization and self.client.stats:
                 self.client.stats.sent_bytes(len(data_to_send),1)
            logger.debug(f"[{self}] Sent: {packet.type.name} (Seq={packet.header.sequence}, Flags={packet.header.flags!r}, Rel={packet.header.reliable}, Len={len(data_to_send)})")
        except Exception as e:
            logger.error(f"[{self}] Error sending {packet.type.name} (Seq={packet.header.sequence}): {e}")

    def _start_network_tasks(self):
        if not self.transport or not self.connected:
            logger.error(f"[{self}] Cannot start network tasks, not connected or no transport.")
            return
        logger.debug(f"[{self}] Starting network tasks (ACKs, Resends)...")
        if not self.ack_task or self.ack_task.done():
            self.ack_task = asyncio.create_task(self._send_acks_loop())
        if not self.resend_task or self.resend_task.done():
            self.resend_task = asyncio.create_task(self._resend_loop())

    async def _stop_network_tasks(self):
        logger.debug(f"[{self}] Stopping network tasks (ACKs, Resends)...")
        tasks_to_stop: List[Tuple[asyncio.Task | None, str]] = [
            (self.ack_task, "ACKLoop"), (self.resend_task, "ResendLoop"),
        ]
        for task, name in tasks_to_stop:
            if task and not task.done():
                task.cancel(); await asyncio.sleep(0) # Yield to allow task to process cancellation
                try: await asyncio.wait_for(task, timeout=1.0) # Wait briefly for clean exit
                except asyncio.CancelledError: logger.debug(f"Task {name} successfully cancelled for {self}.")
                except asyncio.TimeoutError: logger.warning(f"Task {name} did not exit cleanly after cancellation for {self}.")
                except Exception as e: logger.error(f"Error stopping task {name} for {self}: {e}")
        self.ack_task = None; self.resend_task = None
        logger.debug(f"[{self}] Network tasks stopped.")

    def __str__(self) -> str: return f"Simulator(Name='{self.name}', IP={self.ip_addr_str}:{self.port})"
    def __repr__(self) -> str:
        return (f"<Simulator Name='{self.name}' IP='{self.ip_addr_str}:{self.port}' "
                f"Connected={self.connected} Handshake={self.handshake_complete} AMC={self.agent_movement_complete}>")
