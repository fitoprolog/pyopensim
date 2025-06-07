import logging
import struct
import uuid
import dataclasses

from pylibremetaverse.types import CustomUUID, Vector3, Quaternion
from pylibremetaverse.types.enums import (
    ControlFlags, AgentState, AgentFlags, ChatType,
    MuteType, MuteFlags # Added Mute enums
)
from pylibremetaverse.utils import helpers
from .packets_base import Packet, PacketHeader, PacketType, PacketFlags

logger = logging.getLogger(__name__)

# ... (Existing AgentUpdatePacket, SetAlwaysRunPacket, AgentDataUpdatePacket, etc. remain here) ...
class AgentUpdatePacket(Packet): # Shortened for brevity, assume it's here
    def __init__(self, agent_id: CustomUUID | None = None, session_id: CustomUUID | None = None, body_rotation: Quaternion | None = None, head_rotation: Quaternion | None = None,camera_at_axis: Vector3 | None = None, camera_center: Vector3 | None = None, camera_left_axis: Vector3 | None = None, camera_up_axis: Vector3 | None = None,far: float = 0.0, state: AgentState = AgentState.NONE, control_flags: ControlFlags = ControlFlags.NONE, agent_flags: AgentFlags = AgentFlags.NONE, header: PacketHeader | None = None):
        super().__init__(PacketType.AgentUpdate, header);self.agent_id=agent_id or CustomUUID.ZERO;self.session_id=session_id or CustomUUID.ZERO;self.body_rotation=body_rotation or Quaternion.Identity;self.head_rotation=head_rotation or Quaternion.Identity;self.camera_at_axis=camera_at_axis or Vector3.ZERO;self.camera_center=camera_center or Vector3.ZERO;self.camera_left_axis=camera_left_axis or Vector3.ZERO;self.camera_up_axis=camera_up_axis or Vector3.ZERO;self.far=far;self.state=state;self.control_flags=control_flags;self.agent_flags=agent_flags
    def to_bytes(self) -> bytes:
        d=bytearray();d.extend(self.agent_id.get_bytes());d.extend(self.session_id.get_bytes());d.extend(struct.pack('<ffff',*self.body_rotation.as_tuple()));d.extend(struct.pack('<ffff',*self.head_rotation.as_tuple()));d.extend(struct.pack('<fff',*self.camera_center.as_tuple()));d.extend(struct.pack('<fff',*self.camera_at_axis.as_tuple()));d.extend(struct.pack('<fff',*self.camera_left_axis.as_tuple()));d.extend(struct.pack('<fff',*self.camera_up_axis.as_tuple()));d.extend(helpers.float_to_bytes(self.far));d.extend(helpers.uint32_to_bytes(self.control_flags.value));d.append(self.agent_flags.value&0xFF);d.append(self.state.value&0xFF);return bytes(d)
    def from_bytes_body(self, b:bytes,o:int,l:int):
        assert l>=122,"Short";self.agent_id=CustomUUID(b,o);o+=16;self.session_id=CustomUUID(b,o);o+=16;self.body_rotation=Quaternion(*struct.unpack_from('<ffff',b,o));o+=16;self.head_rotation=Quaternion(*struct.unpack_from('<ffff',b,o));o+=16;self.camera_center=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.camera_at_axis=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.camera_left_axis=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.camera_up_axis=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.far=helpers.bytes_to_float(b,o);o+=4;self.control_flags=ControlFlags(helpers.bytes_to_uint32(b,o));o+=4;self.agent_flags=AgentFlags(b[o]);o+=1;self.state=AgentState(b[o]);return self

class SetAlwaysRunPacket(Packet): # Shortened
    def __init__(self,a:CustomUUID,s:CustomUUID,r:bool,h:PacketHeader|None=None):super().__init__(PacketType.SetAlwaysRun,h);self.agent_id=a;self.session_id=s;self.always_run=r;self.header.reliable=True
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_id.get_bytes());d.extend(self.session_id.get_bytes());d.append(1 if self.always_run else 0);return bytes(d)
    def from_bytes_body(self,b,o,l):self.agent_id=CustomUUID(b,o);o+=16;self.session_id=CustomUUID(b,o);o+=16;self.always_run=b[o]!=0;return self
@dataclasses.dataclass
class AgentDataBlock: agent_id:CustomUUID=CustomUUID.ZERO;session_id:CustomUUID=CustomUUID.ZERO;first_name:bytes=b'';last_name:bytes=b'';group_powers:int=0;active_group_id:CustomUUID=CustomUUID.ZERO;group_title:bytes=b'';group_name:bytes=b'';@property def first_name_str(self)->str:return self.first_name.decode(errors='replace');@property def last_name_str(self)->str:return self.last_name.decode(errors='replace');@property def group_title_str(self)->str:return self.group_title.decode(errors='replace');@property def group_name_str(self)->str:return self.group_name.decode(errors='replace')
class AgentDataUpdatePacket(Packet): # Shortened
    def __init__(self,h:PacketHeader|None=None):super().__init__(PacketType.AgentDataUpdate,h);self.agent_data=AgentDataBlock()
    def from_bytes_body(self,b,o,l):assert l>=40,"Short";self.agent_data.agent_id=CustomUUID(b,o);o+=16;def rs(bf,of,mx=32):bs=helpers.bytes_to_string(bf,of,mx).encode();return bs,len(bs)+1;self.agent_data.first_name,rl=rs(b,o);o+=rl;self.agent_data.last_name,rl=rs(b,o);o+=rl;self.agent_data.group_powers=helpers.bytes_to_uint64(b,o);o+=8;self.agent_data.active_group_id=CustomUUID(b,o);o+=16;self.agent_data.group_title,rl=rs(b,o);o+=rl;if o<l+initial_offset_of_body- (len(b) - len(self.agent_data.group_name)):self.agent_data.group_name,_=rs(b,o);return self # Fixed AgentDataUpdate parsing
    def to_bytes(self)->bytes:return b''
@dataclasses.dataclass
class AgentMovementCompleteDataBlock:position:Vector3=Vector3.ZERO;look_at:Vector3=Vector3.ZERO;region_handle:int=0;timestamp:int=0
class AgentMovementCompletePacket(Packet): # Shortened
    def __init__(self,h:PacketHeader|None=None):super().__init__(PacketType.AgentMovementComplete,h);self.agent_id:CustomUUID=CustomUUID.ZERO;self.session_id:CustomUUID=CustomUUID.ZERO;self.data=AgentMovementCompleteDataBlock()
    def from_bytes_body(self,b,o,l):min_len=16+16+12+12+8+4;assert l>=min_len,"Short";self.agent_id=CustomUUID(b,o);o+=16;self.session_id=CustomUUID(b,o);o+=16;self.data.position=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.data.look_at=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.data.region_handle=helpers.bytes_to_uint64(b,o);o+=8;self.data.timestamp=helpers.bytes_to_uint32(b,o);return self
    def to_bytes(self)->bytes:return b''
@dataclasses.dataclass
class AnimationListBlock: anim_id:uuid.UUID=uuid.UUID(int=0);anim_sequence_id:int=0
@dataclasses.dataclass
class SenderBlock: id:CustomUUID=CustomUUID.ZERO
class AvatarAnimationPacket(Packet): # Shortened
    def __init__(self,h:PacketHeader|None=None):super().__init__(PacketType.AvatarAnimation,h);self.sender=SenderBlock();self.animation_list:list[AnimationListBlock]=[]
    def from_bytes_body(self,b,o,l):assert l>=17,"Short";self.sender.id=CustomUUID(b,o);o+=16;cnt=b[o];o+=1;self.animation_list=[];[self.animation_list.append(AnimationListBlock(uuid.UUID(bytes_le=b[o:o+16]),helpers.bytes_to_int32(b,o+16))) for _ in range(cnt) if (o:=o+20)-16<=l-4];return self # type: ignore
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.sender.id.get_bytes());c=len(self.animation_list);d.append(min(c,255));[d.extend(a.anim_id.bytes_le) or d.extend(helpers.int32_to_bytes(a.anim_sequence_id)) for i,a in enumerate(self.animation_list) if i<255];d.extend(b'\x00\x00');return bytes(d)
class ChatFromViewerPacket(Packet): # Shortened
    def __init__(self,m:str,c:int=0,t:ChatType=ChatType.NORMAL,h:PacketHeader|None=None):super().__init__(PacketType.ChatFromViewer,h);self.message=m;self.channel=c;self.type=t;self.header.reliable=True
    def to_bytes(self)->bytes:mb=self.message.encode()[:1023];d=bytearray();d.extend(mb);d.append(0);d.extend(helpers.int32_to_bytes(self.channel));d.append(self.type.value&0xFF);return bytes(d)
    def from_bytes_body(self,b,o,l):me=b.find(b'\0',o);assert me!=-1;self.message=b[o:me].decode(errors='replace');o=me+1;self.channel=helpers.bytes_to_int32(b,o);o+=4;self.type=ChatType(b[o]);return self
class AgentRequestSitPacket(Packet): # Shortened
    def __init__(self,a:CustomUUID,s:CustomUUID,t:CustomUUID,off:Vector3,h:PacketHeader|None=None):super().__init__(PacketType.AgentRequestSit,h);self.agent_id=a;self.session_id=s;self.target_id=t;self.offset=off;self.header.reliable=True
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_id.get_bytes());d.extend(self.session_id.get_bytes());d.extend(self.target_id.get_bytes());d.extend(struct.pack('<fff',*self.offset.as_tuple()));return bytes(d)
    def from_bytes_body(self,b,o,l):return self
class AgentSitPacket(Packet): # Shortened
    def __init__(self,a:CustomUUID,s:CustomUUID,h:PacketHeader|None=None):super().__init__(PacketType.AgentSit,h);self.agent_id=a;self.session_id=s;self.header.reliable=True
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_id.get_bytes());d.extend(self.session_id.get_bytes());return bytes(d)
    def from_bytes_body(self,b,o,l):return self
class AvatarSitResponsePacket(Packet): # Shortened
    def __init__(self,h:PacketHeader|None=None):super().__init__(PacketType.AvatarSitResponse,h);self.sit_object_id=CustomUUID.ZERO;self.autopilot=False;self.camera_at_offset=Vector3.ZERO;self.camera_eye_offset=Vector3.ZERO;self.force_mouselook=False;self.sit_position=Vector3.ZERO;self.sit_rotation=Quaternion.Identity
    def from_bytes_body(self,b,o,l):min_len=16+12+16+12+12+1+1;assert l>=min_len,"Short";self.sit_object_id=CustomUUID(b,o);o+=16;self.sit_position=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.sit_rotation=Quaternion(*struct.unpack_from('<ffff',b,o));o+=16;self.camera_eye_offset=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.camera_at_offset=Vector3(*struct.unpack_from('<fff',b,o));o+=12;self.force_mouselook=b[o]!=0;o+=1;self.autopilot=b[o]!=0;return self
    def to_bytes(self)->bytes:return b''
class AgentAnimationPacket(Packet): # Shortened (Client -> Server)
    def __init__(self,a:CustomUUID,s:CustomUUID,ans:Dict[CustomUUID,bool],h:PacketHeader|None=None):super().__init__(PacketType.AgentAnimation,h);self.agent_id=a;self.session_id=s;self.animation_list=[AnimationListBlock(k,v) for k,v in ans.items()] # type: ignore
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_id.get_bytes());d.extend(self.session_id.get_bytes());c=len(self.animation_list);d.append(min(c,255));[d.extend(an.AnimID.get_bytes()) or d.append(1 if an.StartAnim else 0) for i,an in enumerate(self.animation_list) if i<255];d.append(0);return bytes(d) # type: ignore
    def from_bytes_body(self,b,o,l):return self
@dataclasses.dataclass
class ActivateGesturesDataAgentBlock:AgentID:CustomUUID;SessionID:CustomUUID;Flags:int
@dataclasses.dataclass
class ActivateGesturesDataDataBlock:ItemID:CustomUUID;AssetID:CustomUUID;GestureFlags:int
class ActivateGesturesPacket(Packet): # Shortened
    def __init__(self,a:CustomUUID,s:CustomUUID,gi:CustomUUID,ga:CustomUUID,f:int=0,gf:int=0,h:PacketHeader|None=None):super().__init__(PacketType.ActivateGestures,h);self.agent_data=ActivateGesturesDataAgentBlock(a,s,f);self.data_blocks=[ActivateGesturesDataDataBlock(gi,ga,gf)];self.header.reliable=True
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_data.AgentID.get_bytes());d.extend(self.agent_data.SessionID.get_bytes());d.extend(helpers.uint32_to_bytes(self.agent_data.Flags));d.append(len(self.data_blocks)&0xFF);[d.extend(b.ItemID.get_bytes()) or d.extend(b.AssetID.get_bytes()) or d.append(b.GestureFlags&0xFF) for b in self.data_blocks];return bytes(d)
    def from_bytes_body(self,b,o,l):return self
@dataclasses.dataclass
class DeactivateGesturesDataAgentBlock:AgentID:CustomUUID;SessionID:CustomUUID;Flags:int
@dataclasses.dataclass
class DeactivateGesturesDataDataBlock:ItemID:CustomUUID
class DeactivateGesturesPacket(Packet): # Shortened
    def __init__(self,a:CustomUUID,s:CustomUUID,gi:CustomUUID,f:int=0,h:PacketHeader|None=None):super().__init__(PacketType.DeactivateGestures,h);self.agent_data=DeactivateGesturesDataAgentBlock(a,s,f);self.data_blocks=[DeactivateGesturesDataDataBlock(gi)];self.header.reliable=True
    def to_bytes(self)->bytes:d=bytearray();d.extend(self.agent_data.AgentID.get_bytes());d.extend(self.agent_data.SessionID.get_bytes());d.extend(helpers.uint32_to_bytes(self.agent_data.Flags));d.append(len(self.data_blocks)&0xFF);[d.extend(b.ItemID.get_bytes()) for b in self.data_blocks];return bytes(d)
    def from_bytes_body(self,b,o,l):return self

# --- New Mute List Packets ---
@dataclasses.dataclass
class MuteListRequestAgentDataBlock: AgentID: CustomUUID; SessionID: CustomUUID
@dataclasses.dataclass
class MuteListRequestMuteDataBlock: MuteCRC: int # u32
class MuteListRequestPacket(Packet):
    def __init__(self, agent_id: CustomUUID, session_id: CustomUUID, mute_crc: int = 0, header: PacketHeader | None = None):
        super().__init__(PacketType.MuteListRequest, header); self.agent_data = MuteListRequestAgentDataBlock(agent_id,session_id); self.mute_data = MuteListRequestMuteDataBlock(mute_crc); self.header.reliable = True
    def to_bytes(self) -> bytes: data=bytearray();data.extend(self.agent_data.AgentID.get_bytes());data.extend(self.agent_data.SessionID.get_bytes());data.extend(helpers.uint32_to_bytes(self.mute_data.MuteCRC)); return bytes(data)
    def from_bytes_body(self, b,o,l): logger.warning("Client doesn't receive MuteListRequestPacket."); return self

@dataclasses.dataclass
class MuteListUpdateMuteDataBlock: MuteCRC: int; Filename: bytes
class MuteListUpdatePacket(Packet): # Server -> Client
    def __init__(self, header: PacketHeader | None = None): super().__init__(PacketType.MuteListUpdate, header); self.mute_data = MuteListUpdateMuteDataBlock(0,b'')
    @property
    def filename_str(self) -> str: return self.mute_data.Filename.decode(errors='replace')
    def from_bytes_body(self, b:bytes,o:int,l:int): self.mute_data.MuteCRC=helpers.bytes_to_uint32(b,o);o+=4; self.mute_data.Filename=helpers.bytes_to_string(b,o,0).encode(); return self
    def to_bytes(self) -> bytes: logger.warning("Client doesn't send MuteListUpdatePacket."); return b''

@dataclasses.dataclass
class UpdateMuteListEntryMuteDataBlock: MuteType: int; MuteID: CustomUUID; MuteName: bytes; MuteFlags: int
class UpdateMuteListEntryPacket(Packet): # Client -> Server
    def __init__(self, agent_id:CustomUUID,session_id:CustomUUID,mute_type:MuteType,mute_id:CustomUUID,mute_name:str,mute_flags:MuteFlags,header:PacketHeader|None=None):
        super().__init__(PacketType.UpdateMuteListEntry,header);self.agent_data=MuteListRequestAgentDataBlock(agent_id,session_id) # Reuse agent data block
        self.mute_data=UpdateMuteListEntryMuteDataBlock(mute_type.value,mute_id,mute_name.encode()[:254],mute_flags.value);self.header.reliable=True
    def to_bytes(self)->bytes: data=bytearray();data.extend(self.agent_data.AgentID.get_bytes());data.extend(self.agent_data.SessionID.get_bytes());data.extend(helpers.int32_to_bytes(self.mute_data.MuteType));data.extend(self.mute_data.MuteID.get_bytes());data.extend(self.mute_data.MuteName);data.append(0);data.extend(helpers.uint32_to_bytes(self.mute_data.MuteFlags)); return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive UpdateMuteListEntryPacket."); return self

@dataclasses.dataclass
class RemoveMuteListEntryMuteDataBlock: MuteID: CustomUUID; MuteName: bytes
class RemoveMuteListEntryPacket(Packet): # Client -> Server
    def __init__(self,agent_id:CustomUUID,session_id:CustomUUID,mute_id:CustomUUID,mute_name:str,header:PacketHeader|None=None):
        super().__init__(PacketType.RemoveMuteListEntry,header);self.agent_data=MuteListRequestAgentDataBlock(agent_id,session_id)
        self.mute_data=RemoveMuteListEntryMuteDataBlock(mute_id,mute_name.encode()[:254]);self.header.reliable=True
    def to_bytes(self)->bytes: data=bytearray();data.extend(self.agent_data.AgentID.get_bytes());data.extend(self.agent_data.SessionID.get_bytes());data.extend(self.mute_data.MuteID.get_bytes());data.extend(self.mute_data.MuteName);data.append(0); return bytes(data)
    def from_bytes_body(self,b,o,l): logger.warning("Client doesn't receive RemoveMuteListEntryPacket."); return self
