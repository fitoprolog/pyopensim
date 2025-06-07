import asyncio
import logging
import time

from pylibremetaverse import utils as plm_utils
from .packets_base import PacketHeader, PacketFlags, PacketType
from .packet_factory import from_bytes as packet_from_bytes
# AckPacket needs to be imported if we handle its type for logging, though factory returns base Packet
# from .packets_control import AckPacket

logger = logging.getLogger(__name__)

class IncomingPacket:
    def __init__(self, simulator_ref, packet_obj):
        self.simulator = simulator_ref
        self.packet = packet_obj
    def __repr__(self):
        return f"IncomingPacket(Sim={self.simulator.name if self.simulator else 'N/A'}, Pkt={type(self.packet).__name__})"

class PacketProtocol(asyncio.DatagramProtocol):
    def __init__(self, simulator_ref):
        self.simulator = simulator_ref # Reference to the Simulator instance
        self.transport = None
        logger.debug(f"PacketProtocol initialized for {self.simulator}")

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        logger.info(f"UDP connection established for {self.simulator} to {self.simulator.ip_addr_str}:{self.simulator.port}")
        # self.simulator.connected is already True from Simulator.connect if transport setup succeeded.
        # self.simulator._start_network_tasks() # Simulator starts its tasks once transport is confirmed.

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        if not self.simulator or not self.simulator.client.settings: # Check if sim and settings available
            logger.warning(f"Received datagram from {addr} but simulator or settings are None. Discarding.")
            return
        if not self.simulator.connected: # Check connected state of simulator
            logger.warning(f"Received datagram from {addr} for a disconnected simulator {self.simulator}. Discarding.")
            return

        if self.simulator.client.settings.track_utilization and self.simulator.client.stats:
            self.simulator.client.stats.received_bytes(len(data),1)

        try:
            header = PacketHeader.from_bytes(data, 0)
            full_payload_offset = PacketHeader.SIZE

            # Potentially zero-decoded data (full packet: header + body_with_type_markers)
            processed_data = data
            if header.flags & PacketFlags.ZEROCODED:
                max_size = self.simulator.client.settings.MAX_PACKET_SIZE
                decompressed_buffer = bytearray(max_size)
                try:
                    actual_len = plm_utils.zero_decode(data, len(data), decompressed_buffer)
                    processed_data = bytes(decompressed_buffer[:actual_len])
                    # Re-parse header from decompressed data as flags might have changed (though unlikely for decode)
                    # More importantly, payload is now different.
                    header = PacketHeader.from_bytes(processed_data, 0)
                    logger.debug(f"Zero-decoded packet from {len(data)} to {actual_len} bytes for {self.simulator} (Seq={header.sequence})")
                except Exception as e:
                    logger.error(f"Zero-decode failed for packet (Seq={header.sequence}) from {self.simulator}: {e}")
                    return

            # Payload now means data *after* the 4-byte header
            payload_with_type_markers = processed_data[full_payload_offset:]

            # Handle appended ACKs if MSG_APPENDED_ACKS (PacketFlags.ACK) is set on this data packet's header
            if header.flags & PacketFlags.ACK:
                num_acks = payload_with_type_markers[-1] # Last byte of payload is count of ACKs
                ack_data_len = num_acks * 4 + 1 # Each ACK is 4 bytes (u32 seq) + 1 byte for count

                if len(payload_with_type_markers) >= ack_data_len:
                    ack_payload_start = len(payload_with_type_markers) - ack_data_len
                    current_ack_offset = ack_payload_start
                    for i in range(num_acks):
                        acked_seq = plm_utils.bytes_to_uint32(payload_with_type_markers, current_ack_offset)
                        if acked_seq in self.simulator.need_ack:
                            del self.simulator.need_ack[acked_seq]
                        logger.debug(f"[{self.simulator}] Appended ACK received for Seq={acked_seq} within packet Seq={header.sequence}.")
                        current_ack_offset += 4
                    # Trim the payload to exclude these appended ACKs before factory processing
                    payload_with_type_markers = payload_with_type_markers[:ack_payload_start]
                else:
                    logger.warning(f"[{self.simulator}] MSG_APPENDED_ACKS flag set, but payload too short for num_acks={num_acks}. Seq={header.sequence}")

            if not payload_with_type_markers and not (header.flags & PacketFlags.ACK): # If only header and no actual payload (e.g. pure header ACK)
                # This case might occur if a packet is ONLY ACKs in its header (no body, no appended acks)
                # Or if after stripping appended ACKs, the data payload is empty.
                # For pure header ACKs, just update ack_inbox based on header.sequence
                if header.flags & PacketFlags.ACK: # If the header itself is an ACK for its sequence number
                     logger.debug(f"Pure Header ACK received for Seq={header.sequence} from {self.simulator}")
                     if header.sequence in self.simulator.need_ack: del self.simulator.need_ack[header.sequence]
                else:
                     logger.debug(f"Empty payload for non-ACK packet Seq={header.sequence} from {self.simulator}. Discarding.")
                return

            # If reliable, queue an ACK for this packet's sequence number
            if header.reliable:
                self.simulator.queue_ack(header.sequence)

            # Deserialize using PacketFactory
            deserialized_packet = packet_from_bytes(payload_with_type_markers, header)

            if deserialized_packet:
                # If it's an AckPacket (PacketType.PacketAck, 0xFFFFFFF4), process its list of sequences
                if deserialized_packet.type == PacketType.PacketAck:
                    logger.debug(f"[{self.simulator}] Received AckPacket (Seq={header.sequence}) with {len(deserialized_packet.sequences)} ACKs: {deserialized_packet.sequences[:10]}")
                    for acked_seq in deserialized_packet.sequences:
                        if acked_seq in self.simulator.need_ack:
                            del self.simulator.need_ack[acked_seq]
                            # logger.debug(f"[{self.simulator}] Cleared reliable packet Seq={acked_seq} due to AckPacket.")
                    return # AckPacket processed, no further handling needed by general inbox

                # For other deserialized packets, put them into the NetworkManager's inbox
                logger.debug(f"Deserialized {deserialized_packet.type.name} (Seq={header.sequence}) for {self.simulator}, enqueuing.")
                incoming_wrapper = IncomingPacket(simulator=self.simulator, packet=deserialized_packet)
                asyncio.create_task(self.simulator.network_manager.packet_inbox.put(incoming_wrapper))
            else:
                logger.debug(f"PacketFactory could not deserialize. Seq={header.sequence}, Flags={header.flags!r}. "
                               f"Payload (after type markers, if any, were stripped by factory): {payload_with_type_markers[:12].hex()} from {self.simulator}")

        except Exception as e:
            logger.exception(f"Critical error in datagram_received for {self.simulator}: {e}. Raw Data: {data.hex()[:100]}")

    def error_received(self, exc: Exception):
        logger.error(f"UDP error for {self.simulator}: {exc}")
        if self.simulator:
            # This error might mean the simulator is unreachable.
            # Consider triggering a disconnect or checking connection status.
            # For now, just log. PacketProtocol.connection_lost will handle actual disconnect.
            pass

    def connection_lost(self, exc: Exception | None):
        logger.info(f"UDP connection lost for {self.simulator}. Exception: {exc if exc else 'Clean close'}")
        sim = self.simulator
        if sim:
            sim.connected = False; sim.handshake_complete = False
            sim.transport = None; sim.protocol = None
            asyncio.create_task(sim._stop_network_tasks()) # Ensure tasks are stopped

            nm = sim.network_manager
            if nm:
                asyncio.create_task(nm._on_sim_disconnected(sim, requested_logout=False))

        if exc: logger.error(f"Connection lost for {sim} due to error: {exc}")
