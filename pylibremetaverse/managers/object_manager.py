import logging
import asyncio
from typing import TYPE_CHECKING, Dict, List, Callable

from pylibremetaverse.types import CustomUUID, Vector3, Quaternion
from pylibremetaverse.types.primitive import Primitive
from pylibremetaverse.types.enums import PrimFlags, PCode, Material, ClickAction, PathCurve, ProfileCurve, SaleType
from pylibremetaverse.network.packets_object import (
    ObjectUpdatePacket, ObjectDataBlock,
    RequestMultipleObjectsPacket, ObjectUpdateCachedPacket,
    ImprovedTerseObjectUpdatePacket, ImprovedTerseObjectDataBlock,
    KillObjectPacket,
    RequestObjectPropertiesFamilyPacket,
    ObjectPropertiesFamilyPacket, ObjectPropertiesPacket, ObjectPropertiesPacketDataBlock,
    ObjectMovePacket, ObjectScalePacket, ObjectRotationPacket,
    ObjectNamePacket, ObjectDescriptionPacket, ObjectTextPacket, ObjectClickActionPacket,
    ObjectAddPacket # Added ObjectAddPacket for creation
)
from pylibremetaverse.network.packet_protocol import IncomingPacket
from pylibremetaverse.types.enums import AddFlags # Ensure AddFlags is imported
# ClickAction, PCode, Material, PathCurve, ProfileCurve are already imported from pylibremetaverse.types.enums
from pylibremetaverse.network.packets_base import Packet, PacketType
from pylibremetaverse import utils

if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient
    from pylibremetaverse.network.simulator import Simulator

logger = logging.getLogger(__name__)

ObjectUpdatedHandler = Callable[[Primitive, 'Simulator'], None]
ObjectRemovedHandler = Callable[[int, 'Simulator'], None]

class ObjectManager:
    def __init__(self, client: 'GridClient'):
        self.client = client
        self.simulators_objects: Dict['Simulator', Dict[int, Primitive]] = {}
        self.uuid_to_localid_map: Dict['Simulator', Dict[CustomUUID, int]] = {}
        self._object_updated_handlers: List[ObjectUpdatedHandler] = []
        self._object_removed_handlers: List[ObjectRemovedHandler] = []

        if self.client.network:
            reg = self.client.network.register_packet_handler
            reg(PacketType.ObjectUpdate, self._on_object_update_wrapper)
            reg(PacketType.ObjectUpdateCached, self._on_object_update_cached_wrapper)
            reg(PacketType.ImprovedTerseObjectUpdate, self._on_improved_terse_object_update_wrapper)
            reg(PacketType.KillObject, self._on_kill_object_wrapper)
            reg(PacketType.ObjectProperties, self._on_object_properties_wrapper)
            reg(PacketType.ObjectPropertiesFamily, self._on_object_properties_family_wrapper)
        else: logger.error("ObjectManager: NetworkManager not available at init.")

    def _on_object_update_wrapper(self,s,p): isinstance(p,ObjectUpdatePacket) and self._on_object_update(s,p)
    def _on_object_update_cached_wrapper(self,s,p): isinstance(p,ObjectUpdateCachedPacket) and self._on_object_update_cached(s,p)
    def _on_improved_terse_object_update_wrapper(self,s,p): isinstance(p,ImprovedTerseObjectUpdatePacket) and self._on_improved_terse_object_update(s,p)
    def _on_kill_object_wrapper(self,s,p): isinstance(p,KillObjectPacket) and self._on_kill_object(s,p)
    def _on_object_properties_wrapper(self,s,p): isinstance(p,ObjectPropertiesPacket) and self._on_object_properties(s,p)
    def _on_object_properties_family_wrapper(self,s,p): isinstance(p,ObjectPropertiesFamilyPacket) and self._on_object_properties_family(s,p)

    def register_object_updated_handler(self,cb):self._object_updated_handlers.append(cb)
    def unregister_object_updated_handler(self,cb):self._object_updated_handlers.remove(cb)
    def register_object_removed_handler(self,cb):self._object_removed_handlers.append(cb)
    def unregister_object_removed_handler(self,cb):self._object_removed_handlers.remove(cb)

    def _update_prim_from_properties_block(self, prim: Primitive, props_block: ObjectPropertiesPacketDataBlock):
        prim.creator_id=props_block.CreatorID; prim.owner_id=props_block.OwnerID; prim.group_id=props_block.GroupID
        prim.base_mask=props_block.BaseMask; prim.owner_mask=props_block.OwnerMask; prim.group_mask=props_block.GroupMask
        prim.everyone_mask=props_block.EveryoneMask; prim.next_owner_mask=props_block.NextOwnerMask
        prim.ownership_cost=props_block.OwnershipCost; prim.sale_price=props_block.SalePrice
        try: prim.sale_type = SaleType(props_block.SaleType)
        except ValueError: logger.warning(f"Unknown SaleType value {props_block.SaleType} for prim {prim.id_uuid}")
        prim.category=props_block.Category; prim.last_owner_id=props_block.LastOwnerID
        prim.name=props_block.name_str; prim.description=props_block.description_str
        prim.touch_text=props_block.touch_text_str; prim.sit_text=props_block.sit_text_str
        logger.debug(f"Updated props for prim {prim.id_uuid} (LID:{prim.local_id}): Name='{prim.name}'")

    def _on_object_properties(self, source_sim: 'Simulator', packet: ObjectPropertiesPacket):
        # (Implementation from previous step)
        if source_sim not in self.simulators_objects: self.simulators_objects[source_sim] = {}
        if source_sim not in self.uuid_to_localid_map: self.uuid_to_localid_map[source_sim] = {}
        sim_prims = self.simulators_objects[source_sim]; updated_prims_list = []
        for props_block in packet.object_data_blocks:
            local_id = self.uuid_to_localid_map[source_sim].get(props_block.ObjectID); prim = None
            if local_id is not None: prim = sim_prims.get(local_id)
            if not prim:
                for p_obj in sim_prims.values():
                    if p_obj.id_uuid == props_block.ObjectID: prim = p_obj; break
            if prim: self._update_prim_from_properties_block(prim, props_block); updated_prims_list.append(prim)
            else: logger.warning(f"ObjectProperties: unknown prim UUID {props_block.ObjectID} in {source_sim.name}")
        for p_event in updated_prims_list:
            for h in self._object_updated_handlers: try: h(p_event, source_sim)
            except Exception as e: logger.error(f"Err in object_updated_handler (properties): {e}")

    def _on_object_properties_family(self, source_sim: 'Simulator', packet: ObjectPropertiesFamilyPacket):
        # (Implementation from previous step)
        if source_sim not in self.simulators_objects: self.simulators_objects[source_sim] = {}
        if source_sim not in self.uuid_to_localid_map: self.uuid_to_localid_map[source_sim] = {}
        sim_prims = self.simulators_objects[source_sim]
        if packet.properties_blocks:
            props_block = packet.properties_blocks[0]
            if props_block.ObjectID != packet.object_id: logger.warning(f"OPFamily: Root ObjectID {packet.object_id} mismatch with props ID {props_block.ObjectID}")
            local_id = self.uuid_to_localid_map[source_sim].get(props_block.ObjectID); prim = None
            if local_id is not None: prim = sim_prims.get(local_id)
            if not prim:
                for p_obj in sim_prims.values():
                    if p_obj.id_uuid == props_block.ObjectID: prim = p_obj; break
            if prim:
                self._update_prim_from_properties_block(prim, props_block)
                for h in self._object_updated_handlers: try: h(prim, source_sim)
                except Exception as e: logger.error(f"Err in object_updated_handler (props family): {e}")
            else: logger.warning(f"OPFamily: unknown prim UUID {props_block.ObjectID} in {source_sim.name}")
        else: logger.warning(f"OPFamily: No properties blocks in packet for {packet.object_id}")

    def _on_object_update(self, source_sim: 'Simulator', packet: ObjectUpdatePacket):
        # (Implementation from previous step, ensure uuid_to_localid_map is updated)
        if source_sim not in self.simulators_objects: self.simulators_objects[source_sim]={}
        if source_sim not in self.uuid_to_localid_map: self.uuid_to_localid_map[source_sim]={}
        sim_prims=self.simulators_objects[source_sim];updated_prims=[]
        for obj_block in packet.object_data_blocks:
            prim=sim_prims.get(obj_block.id);is_new=False
            if not prim:prim=Primitive(obj_block.id,obj_block.full_id);sim_prims[obj_block.id]=prim;is_new=True;self.uuid_to_localid_map[source_sim][prim.id_uuid]=prim.local_id
            elif prim.id_uuid!=obj_block.full_id:
                if prim.id_uuid in self.uuid_to_localid_map[source_sim]:del self.uuid_to_localid_map[source_sim][prim.id_uuid]
                prim.id_uuid=obj_block.full_id;self.uuid_to_localid_map[source_sim][prim.id_uuid]=prim.local_id
            prim.state=obj_block.state;prim.crc=obj_block.crc;prim.parent_id=obj_block.parent_id;prim.pcode=PCode(obj_block.pcode);prim.material=Material(obj_block.material);prim.click_action=ClickAction(obj_block.click_action);prim.scale=obj_block.scale;prim.position=obj_block.position;prim.rotation=obj_block.rotation;prim.path_curve=PathCurve(obj_block.path_curve);prim.profile_curve=ProfileCurve(obj_block.profile_curve);prim.path_begin=obj_block.path_begin;prim.path_end=obj_block.path_end;prim.profile_begin=obj_block.profile_begin;prim.profile_hollow=obj_block.profile_hollow;prim.owner_id=obj_block.owner_id;prim.group_id=obj_block.group_id
            if obj_block.name_value_bytes:prim.name=obj_block.name;prim.description=obj_block.description;prim.text=obj_block.text
            prim.text_color=obj_block.text_color;prim.media_url=obj_block.media_url.decode(errors='replace') if hasattr(obj_block,'media_url')and obj_block.media_url else"";prim.texture_entry_bytes=obj_block.texture_entry_bytes;updated_prims.append(prim)
        for p_event in updated_prims:
            for h in self._object_updated_handlers:try:h(p_event,source_sim)
            except Exception as e:logger.error(f"Err in object_updated_handler:{e}")

    async def request_object_properties(self, simulator: 'Simulator', object_uuid: CustomUUID):
        # (Implementation from previous step)
        if not simulator or not simulator.connected or not simulator.handshake_complete: logger.warning(f"Sim {simulator.name if simulator else 'N/A'} not ready."); return
        packet = RequestObjectPropertiesFamilyPacket(self.client.self.agent_id,self.client.self.session_id,object_uuid)
        packet.header.reliable = True; await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ROPFamily for UUID {object_uuid} to {simulator.name}.")

    def _on_improved_terse_object_update(self, source_sim: 'Simulator', packet: ImprovedTerseObjectUpdatePacket): # Refined
        if source_sim not in self.simulators_objects: self.simulators_objects[source_sim] = {}
        sim_prims = self.simulators_objects[source_sim]; updated_prims: List[Primitive] = []

        for block in packet.object_data_blocks:
            prim = sim_prims.get(block.local_id)
            if not prim: prim = Primitive(local_id=block.local_id); sim_prims[block.local_id] = prim

            obj_data_payload = block.data
            bit_offset = 0
            if not obj_data_payload: logger.warning(f"TerseUpdate for {prim.local_id}: Empty data block."); continue

            data_update_type = obj_data_payload[0]; bit_offset += 8

            try:
                terse_update_flags = 0
                if data_update_type == 0 or data_update_type == 1: # Avatar Full or Prim Full
                    if len(obj_data_payload) * 8 <= bit_offset: logger.warning(f"Terse {prim.local_id}: Not enough data for flags1."); continue
                    terse_update_flags = obj_data_payload[bit_offset // 8]; bit_offset += 8

                TUF_HAS_PARENT_ID=0x10;TUF_HAS_POSITION=0x01;TUF_HAS_VELOCITY=0x02;TUF_HAS_ACCELERATION=0x04
                TUF_HAS_ROTATION=0x08;TUF_HAS_ANGULAR_VELOCITY=0x20;TUF_IS_ATTACHMENT=0x40

                if data_update_type == 0 or data_update_type == 1: # Full updates using terse_update_flags
                    if terse_update_flags & TUF_HAS_PARENT_ID:
                        if len(obj_data_payload)*8 >= bit_offset+32 and bit_offset%8==0: prim.parent_id=utils.helpers.bytes_to_uint32_little_endian(obj_data_payload,bit_offset//8);bit_offset+=32
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough/misaligned for ParentID.")
                    if terse_update_flags & TUF_HAS_POSITION:
                        is_att=bool(terse_update_flags & TUF_IS_ATTACHMENT)
                        n_bits_list = [utils.ATTACHMENT_POS_BITS if is_att else utils.PRIM_POS_BITS] * 3
                        mins_list = [utils.ATTACHMENT_POS_MIN if is_att else 0.0] * 3
                        maxs_list = [utils.ATTACHMENT_POS_MAX if is_att else source_sim.region_size_x,
                                     utils.ATTACHMENT_POS_MAX if is_att else source_sim.region_size_y,
                                     utils.ATTACHMENT_POS_MAX if is_att else utils.DEFAULT_REGION_SIZE_Z_MAX]
                        is_signed_list = [is_att] * 3
                        if len(obj_data_payload)*8>=bit_offset+sum(n_bits_list):
                            prim.position,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,n_bits_list,mins_list,maxs_list,is_signed_list)
                            logger.debug(f"Terse Full {prim.local_id}: Pos={prim.position}")
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough data for Position.")
                    if terse_update_flags & TUF_HAS_VELOCITY:
                        if len(obj_data_payload)*8>=bit_offset+(3*utils.VELOCITY_BITS): prim.velocity,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,[utils.VELOCITY_BITS]*3,[utils.VELOCITY_MIN]*3,[utils.VELOCITY_MAX]*3,[True]*3); logger.debug(f"Terse Full {prim.local_id}: Vel={prim.velocity}")
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough data for Velocity.")
                    if terse_update_flags & TUF_HAS_ACCELERATION:
                        if len(obj_data_payload)*8>=bit_offset+(3*utils.ACCELERATION_BITS): prim.acceleration,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,[utils.ACCELERATION_BITS]*3,[utils.ACCELERATION_MIN]*3,[utils.ACCELERATION_MAX]*3,[True]*3); logger.debug(f"Terse Full {prim.local_id}: Accel={prim.acceleration}")
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough data for Acceleration.")
                    if terse_update_flags & TUF_HAS_ROTATION:
                        if len(obj_data_payload)*8>=bit_offset+(3*utils.QUATERNION_COMPONENT_BITS): prim.rotation,bit_offset=utils.read_packed_quaternion(obj_data_payload,bit_offset); logger.debug(f"Terse Full {prim.local_id}: Rot={prim.rotation}")
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough data for Rotation.")
                    if terse_update_flags & TUF_HAS_ANGULAR_VELOCITY:
                        if len(obj_data_payload)*8>=bit_offset+(3*utils.ANGULAR_VELOCITY_BITS): prim.angular_velocity,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,[utils.ANGULAR_VELOCITY_BITS]*3,[utils.ANGULAR_VELOCITY_MIN]*3,[utils.ANGULAR_VELOCITY_MAX]*3,[True]*3); logger.debug(f"Terse Full {prim.local_id}: AngVel={prim.angular_velocity}")
                        else: logger.warning(f"Terse Full {prim.local_id}: Not enough data for AngVel.")

                elif data_update_type == 2: # Avatar Terse
                    if len(obj_data_payload)*8>=bit_offset+(3*utils.AVATAR_TERSE_POS_BITS): prim.position,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,[utils.AVATAR_TERSE_POS_BITS]*3,[utils.AVATAR_TERSE_POS_MIN]*3,[utils.AVATAR_TERSE_POS_MAX]*3,[True]*3); logger.debug(f"Terse Avatar {prim.local_id}: Pos={prim.position}")
                    else: logger.warning(f"Terse Avatar {prim.local_id}: Not enough data for Position.")
                    if len(obj_data_payload)*8>=bit_offset+(3*utils.QUATERNION_COMPONENT_BITS): prim.rotation,bit_offset=utils.read_packed_quaternion(obj_data_payload,bit_offset); logger.debug(f"Terse Avatar {prim.local_id}: Rot={prim.rotation}")
                    else: logger.warning(f"Terse Avatar {prim.local_id}: Not enough data for Rotation.")

                elif data_update_type == 3: # Prim Terse
                    if len(obj_data_payload)*8>=bit_offset+(3*utils.PRIM_POS_BITS):
                        prim.position,bit_offset=utils.read_packed_vector3(obj_data_payload,bit_offset,[utils.PRIM_POS_BITS]*3, [0.0,0.0,utils.SIM_MIN_POS_Z], [source_sim.region_size_x,source_sim.region_size_y,utils.DEFAULT_REGION_SIZE_Z_MAX], [False]*3); logger.debug(f"Terse Prim {prim.local_id}: Pos={prim.position}")
                    else: logger.warning(f"Terse Prim {prim.local_id}: Not enough data for Position.")
                    if len(obj_data_payload)*8>=bit_offset+(3*utils.QUATERNION_COMPONENT_BITS): prim.rotation,bit_offset=utils.read_packed_quaternion(obj_data_payload,bit_offset); logger.debug(f"Terse Prim {prim.local_id}: Rot={prim.rotation}")
                    else: logger.warning(f"Terse Prim {prim.local_id}: Not enough data for Rotation.")
                else: logger.debug(f"Unhandled DataUpdateType {data_update_type} for terse {prim.local_id}.")
                if block.texture_entry_bytes: prim.texture_entry_bytes = block.texture_entry_bytes
                updated_prims.append(prim)
            except ValueError as e: logger.error(f"ValueError Terse LID {block.local_id},Type {data_update_type}:{e}. Data:{obj_data_payload.hex()[:40]}")
            except Exception as e: logger.exception(f"Unexpected err Terse LID {block.local_id},Type {data_update_type}:{e}. Data:{obj_data_payload.hex()[:40]}")
        for p_event in updated_prims:
            for h in self._object_updated_handlers: try: h(p_event,source_sim)
            except Exception as e: logger.error(f"Err in object_updated_handler(terse):{e}")

    def _on_kill_object(self, source_sim: 'Simulator', packet: KillObjectPacket):
        if source_sim not in self.simulators_objects: logger.warning(f"KillObject for untracked sim {source_sim.name}"); return
        sim_prims=self.simulators_objects[source_sim]; removed_ids=[]; uuid_map=self.uuid_to_localid_map.get(source_sim,{})
        for obj_block in packet.object_data_blocks:
            local_id=obj_block.ID
            if local_id in sim_prims:
                removed_prim=sim_prims.pop(local_id);removed_ids.append(local_id)
                if removed_prim.id_uuid in uuid_map: del uuid_map[removed_prim.id_uuid]
                logger.debug(f"Killed object LocalID {local_id} in {source_sim.name}")
                for handler in self._object_removed_handlers:
                    try: handler(local_id, source_sim)
                    except Exception as e: logger.error(f"Error in object_removed_handler: {e}")
            else: logger.debug(f"KillObject: LocalID {local_id} not found in {source_sim.name} cache.")
        if removed_ids: logger.info(f"Processed KillObject in {source_sim.name}, removed {len(removed_ids)} prims.")

    def get_prim(self,s:'Simulator',lid:int)->Primitive|None: return self.simulators_objects.get(s,{}).get(lid)
    def get_prims_in_sim(self,s:'Simulator')->List[Primitive]: return list(self.simulators_objects.get(s,{}).values())
    def clear_sim_objects(self,s:'Simulator'):
        if s in self.simulators_objects:del self.simulators_objects[s];logger.info(f"Cleared objects for sim {s.name}")
        if s in self.uuid_to_localid_map:del self.uuid_to_localid_map[s]

    async def move_object(self, simulator: 'Simulator', local_id: int, new_position: Vector3):
        """Sends a packet to move an object to a new position."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot move object: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot move object: AgentID not set.")
            return

        packet = ObjectMovePacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_moves=[(local_id, new_position)]
        )
        # Reliability is set in packet's __init__
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectMovePacket for LocalID {local_id} to {new_position} in {simulator.name}.")

    async def scale_object(self, simulator: 'Simulator', local_id: int, new_scale: Vector3):
        """Sends a packet to scale an object."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot scale object: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot scale object: AgentID not set.")
            return

        packet = ObjectScalePacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_scales=[(local_id, new_scale)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectScalePacket for LocalID {local_id} to {new_scale} in {simulator.name}.")

    async def rotate_object(self, simulator: 'Simulator', local_id: int, new_rotation: Quaternion):
        """Sends a packet to rotate an object."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot rotate object: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot rotate object: AgentID not set.")
            return

        packet = ObjectRotationPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_rotations=[(local_id, new_rotation)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectRotationPacket for LocalID {local_id} to {new_rotation} in {simulator.name}.")

    async def set_object_name(self, simulator: 'Simulator', local_id: int, name: str):
        """Sends a packet to set an object's name."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot set object name: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot set object name: AgentID not set.")
            return

        packet = ObjectNamePacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_names=[(local_id, name)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectNamePacket for LocalID {local_id} to set name '{name}' in {simulator.name}.")

    async def set_object_description(self, simulator: 'Simulator', local_id: int, description: str):
        """Sends a packet to set an object's description."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot set object description: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot set object description: AgentID not set.")
            return

        packet = ObjectDescriptionPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_descriptions=[(local_id, description)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectDescriptionPacket for LocalID {local_id} in {simulator.name}.")

    async def set_object_text(self, simulator: 'Simulator', local_id: int, text: str):
        """Sends a packet to set an object's hover text."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot set object text: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot set object text: AgentID not set.")
            return

        packet = ObjectTextPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_texts=[(local_id, text)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectTextPacket for LocalID {local_id} in {simulator.name}.")

    async def set_object_click_action(self, simulator: 'Simulator', local_id: int, click_action: ClickAction):
        """Sends a packet to set an object's click action."""
        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot set object click action: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot set object click action: AgentID not set.")
            return

        packet = ObjectClickActionPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            object_click_actions=[(local_id, click_action)]
        )
        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectClickActionPacket for LocalID {local_id} to {click_action.name} in {simulator.name}.")

    async def add_prim(self, simulator: 'Simulator',
                       pcode: PCode,
                       material: Material,
                       add_flags: AddFlags,
                       path_params: dict,
                       profile_params: dict,
                       position: Vector3, # This is the target position for the raycast, or direct position if bypass_raycast
                       scale: Vector3,
                       rotation: Quaternion,
                       texture_entry_bytes: bytes,
                       group_id: CustomUUID = CustomUUID.ZERO,
                       state: int = 0, # Attachment point if AddFlags.ATTACH_TO_ROOT is set
                       bypass_raycast: bool = True,
                       ray_start_is_agent_pos: bool = True,
                       ray_end_offset: Vector3 = Vector3(2.0, 0.0, 0.0), # Offset from agent if ray_start_is_agent_pos
                       ray_target_id: CustomUUID = CustomUUID.ZERO,
                       ray_end_is_intersection: bool = False):
        """Sends a packet to add/rez a new primitive object."""

        if not simulator or not simulator.connected or not simulator.handshake_complete:
            logger.warning(f"Cannot add prim: Simulator {simulator.name if simulator else 'N/A'} not ready.")
            return
        if not self.client.self or self.client.self.agent_id == CustomUUID.ZERO:
            logger.warning("Cannot add prim: AgentID not set.")
            return
        if not self.client.self.movement: # movement manager might not be initialized if self isn't fully set
             logger.warning("Cannot add prim: Agent movement data not available for raycast calculation.")
             return

        actual_ray_start = Vector3.ZERO
        actual_ray_end = position # Default to using position as ray_end

        if bypass_raycast:
            if ray_start_is_agent_pos:
                actual_ray_start = self.client.self.movement.position
                # Calculate ray_end based on agent's rotation and offset
                # IMPORTANT: This needs the agent's *body* rotation, not camera.
                # Assuming self.client.self.movement.rotation is body rotation.
                agent_rotation = self.client.self.movement.rotation
                rotated_offset = agent_rotation.multiply_vector(ray_end_offset)
                actual_ray_end = actual_ray_start + rotated_offset
            else: # bypass_raycast but not using agent pos - use provided ray_start and ray_end (or position for ray_end)
                actual_ray_start = ray_start if ray_start is not None else self.client.self.movement.position
                actual_ray_end = ray_end if ray_end is not None else position
        else: # Not bypassing raycast, so ray_start and ray_end are critical. Position field in packet is ignored.
            actual_ray_start = ray_start if ray_start is not None else self.client.self.movement.position
            actual_ray_end = ray_end if ray_end is not None else position


        packet = ObjectAddPacket(
            agent_id=self.client.self.agent_id,
            session_id=self.client.self.session_id,
            pcode=pcode,
            material=material,
            add_flags=add_flags,
            path_params=path_params,
            profile_params=profile_params,
            position=actual_ray_end, # For ObjectAddPacket, Position field is RayEnd if BypassRaycast=1
                                     # or the world position if BypassRaycast=0 (and ray fields are used for targeting)
                                     # The C# code sets Position to RayEnd if BypassRaycast is true.
            scale=scale,
            rotation=rotation,
            texture_entry_bytes=texture_entry_bytes,
            group_id=group_id,
            state=state,
            bypass_raycast=bypass_raycast,
            ray_start=actual_ray_start,
            ray_end=actual_ray_end, # This is the actual target for the ray
            ray_target_id=ray_target_id,
            ray_end_is_intersection=ray_end_is_intersection
        )

        await self.client.network.send_packet(packet, simulator)
        logger.info(f"Sent ObjectAddPacket to {simulator.name} for PCode {pcode.name}, Scale {scale}.")
