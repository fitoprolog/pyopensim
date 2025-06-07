import asyncio
import logging
import uuid
import dataclasses
import datetime
from typing import TYPE_CHECKING, List, Dict, Callable, Any

from pylibremetaverse.types import CustomUUID, Vector3, Quaternion
from pylibremetaverse.types.enums import (
    ChatType, ChatAudibleLevel, ChatSourceType,
    InstantMessageDialog, InstantMessageOnline,
    TeleportFlags, TeleportStatus, ScriptPermission,
    MuteType, MuteFlags, WearableType, AssetType, InventoryType
)
from pylibremetaverse.types.animations import Animations
from pylibremetaverse.network.login_defs import LoginResponseData, HomeInfo
from pylibremetaverse.network.simulator import Simulator
from pylibremetaverse.network.packets_base import Packet, PacketType
from pylibremetaverse.network.packet_protocol import IncomingPacket
from .agent_movement import AgentMovementManager
from .appearance_manager import AppearanceManager
from .inventory_manager import InventoryManager
from pylibremetaverse.network.packets_agent import (
    AgentDataUpdatePacket, AgentMovementCompletePacket, AvatarAnimationPacket,
    ChatFromViewerPacket, AgentRequestSitPacket, AgentSitPacket, AvatarSitResponsePacket,
    AgentAnimationPacket, ActivateGesturesPacket, DeactivateGesturesPacket,
    MuteListRequestPacket, MuteListUpdatePacket, UpdateMuteListEntryPacket, RemoveMuteListEntryPacket
)
from pylibremetaverse.network.packets_comms import (
    ChatFromSimulatorPacket, ImprovedInstantMessagePacket
)
from pylibremetaverse.network.packets_teleport import (
    TeleportLandmarkRequestPacket, TeleportLocationRequestPacket, TeleportCancelPacket,
    TeleportStartPacket, TeleportProgressPacket, TeleportFailedPacket,
    TeleportFinishPacket, TeleportLocalPacket,
    StartLurePacket, TeleportLureRequestPacket
)
from pylibremetaverse.network.packets_script import (
    ScriptDialogPacket, ScriptDialogReplyPacket, ScriptQuestionPacket, ScriptAnswerYesPacket
)
from pylibremetaverse.network.packets_appearance import AgentWearablesUpdatePacket


if TYPE_CHECKING:
    from pylibremetaverse.client import GridClient

logger = logging.getLogger(__name__)

AgentDataUpdateHandler=Callable[['AgentManager'],None];AnimationsChangedHandler=Callable[[Dict[uuid.UUID,int]],None]
ChatHandler=Callable[['ChatEventArgs'],None];IMHandler=Callable[['IMEventArgs'],None];TeleportProgressHandler=Callable[['TeleportEventArgs'],None]
AvatarSitResponseHandler=Callable[['AvatarSitResponseEventArgs'],None];TeleportLureOfferedHandler=Callable[['TeleportLureEventArgs'],None]
ScriptDialogHandler=Callable[['ScriptDialogEventArgs'],None];ScriptQuestionHandler=Callable[['ScriptQuestionEventArgs'],None]
MuteListUpdatedHandler = Callable[[Dict[str, 'MuteEntry']], None]
@dataclasses.dataclass
class ChatEventArgs:message:str;audible_level:ChatAudibleLevel;chat_type:ChatType;source_type:ChatSourceType;from_name:str;source_id:CustomUUID;owner_id:CustomUUID;position:Vector3;simulator:Simulator
@dataclasses.dataclass
class InstantMessageData:from_agent_id:CustomUUID;from_agent_name:str;to_agent_id:CustomUUID;parent_estate_id:int;region_id:CustomUUID;position:Vector3;dialog:InstantMessageDialog;group_im:bool;im_session_id:CustomUUID;timestamp:datetime.datetime;message:str;offline:InstantMessageOnline;binary_bucket:bytes
@dataclasses.dataclass
class IMEventArgs:im_data:InstantMessageData;simulator:Simulator|None
@dataclasses.dataclass
class TeleportEventArgs:message:str;status:TeleportStatus;flags:TeleportFlags
@dataclasses.dataclass
class AvatarSitResponseEventArgs:object_id:CustomUUID;autopilot:bool;camera_at_offset:Vector3;camera_eye_offset:Vector3;force_mouselook:bool;sit_position:Vector3;sit_rotation:Quaternion
@dataclasses.dataclass
class TeleportLureEventArgs:from_agent_id:CustomUUID;from_agent_name:str;message:str;lure_id:CustomUUID;simulator:Simulator
@dataclasses.dataclass
class ScriptDialogEventArgs:object_id:CustomUUID;object_name:str;first_name:str;last_name:str;message:str;image_id:CustomUUID;chat_channel:int;button_labels:list[str];simulator:Simulator
@dataclasses.dataclass
class ScriptQuestionEventArgs:task_id:CustomUUID;item_id:CustomUUID;object_name:str;object_owner_name:str;questions:ScriptPermission;simulator:Simulator
@dataclasses.dataclass
class MuteEntry: type_: MuteType; id_: CustomUUID; name: str; flags: MuteFlags


class AgentManager:
    def __init__(self, client_ref: 'GridClient'):
        self.client=client_ref; self.agent_id=CustomUUID.ZERO; self.session_id=CustomUUID.ZERO
        self.secure_session_id=CustomUUID.ZERO; self.circuit_code=0; self.seed_capability:str|None=None
        self.name="Unknown Agent"; self.home_info:HomeInfo|None=None; self.start_location_request="last"
        self.current_position=Vector3.ZERO; self.current_look_at=Vector3.ZERO
        self.movement=AgentMovementManager(self); self.appearance=AppearanceManager(client_ref)
        self.inventory=InventoryManager(client_ref)
        self.sitting_on=CustomUUID.ZERO; self.active_gestures:Dict[CustomUUID,CustomUUID]={}
        self._agent_data_update_handlers:List[AgentDataUpdateHandler]=[]; self._animations_changed_handlers:List[AnimationsChangedHandler]=[]
        self.signaled_animations:Dict[uuid.UUID,int]={}; self._chat_handlers:List[ChatHandler]=[]
        self._im_handlers:List[IMHandler]=[]; self._teleport_progress_handlers:List[TeleportProgressHandler]=[]
        self._avatar_sit_response_handlers:List[AvatarSitResponseHandler]=[]; self._teleport_lure_offered_handlers:List[TeleportLureOfferedHandler]=[]
        self._script_dialog_handlers:List[ScriptDialogHandler]=[]; self._script_question_handlers:List[ScriptQuestionHandler]=[]
        self.mute_list: Dict[str, MuteEntry] = {}; self._mute_list_updated_handlers: List[MuteListUpdatedHandler] = []
        self.teleport_status=TeleportStatus.NONE; self.teleport_message=""; self._teleport_event=asyncio.Event()
        reg=self.client.network.register_packet_handler
        reg(PacketType.AgentDataUpdate,self._on_agent_data_update_wrapper);reg(PacketType.AgentMovementComplete,self._on_movement_complete_wrapper)
        reg(PacketType.AvatarAnimation,self._on_avatar_animation_wrapper);reg(PacketType.ChatFromSimulator,self._on_chat_from_simulator_wrapper)
        reg(PacketType.ImprovedInstantMessage,self._on_improved_instant_message_wrapper)
        reg(PacketType.TeleportStart,self._on_teleport_start_wrapper);reg(PacketType.TeleportProgress,self._on_teleport_progress_wrapper)
        reg(PacketType.TeleportFailed,self._on_teleport_failed_wrapper);reg(PacketType.TeleportCancel,self._on_teleport_cancel_wrapper)
        reg(PacketType.TeleportFinish,self._on_teleport_finish_wrapper);reg(PacketType.TeleportLocal,self._on_teleport_local_wrapper)
        reg(PacketType.AvatarSitResponse,self._on_avatar_sit_response_wrapper)
        reg(PacketType.ScriptDialog,self._on_script_dialog_wrapper);reg(PacketType.ScriptQuestion,self._on_script_question_wrapper)
        reg(PacketType.MuteListUpdate, self._on_mute_list_update_wrapper)

    def _on_agent_data_update_wrapper(self,s,p): isinstance(p,AgentDataUpdatePacket) and self._on_agent_data_update(p)
    async def _on_movement_complete_wrapper(self,s,p): isinstance(p,AgentMovementCompletePacket) and await self._on_movement_complete(s,p)
    async def _on_avatar_animation_wrapper(self,s,p): isinstance(p,AvatarAnimationPacket) and await self._on_avatar_animation(s,p)
    def _on_chat_from_simulator_wrapper(self,s,p): isinstance(p,ChatFromSimulatorPacket) and self._on_chat_from_simulator(s,p)
    def _on_improved_instant_message_wrapper(self,s,p): isinstance(p,ImprovedInstantMessagePacket) and self._on_improved_instant_message(s,p)
    def _on_teleport_start_wrapper(self,s,p): isinstance(p,TeleportStartPacket) and self._on_teleport_start(s,p)
    def _on_teleport_progress_wrapper(self,s,p): isinstance(p,TeleportProgressPacket) and self._on_teleport_progress(s,p)
    def _on_teleport_failed_wrapper(self,s,p): isinstance(p,TeleportFailedPacket) and self._on_teleport_failed(s,p)
    def _on_teleport_cancel_wrapper(self,s,p): isinstance(p,TeleportCancelPacket) and self._on_teleport_cancel(s,p)
    async def _on_teleport_finish_wrapper(self,s,p): isinstance(p,TeleportFinishPacket) and await self._on_teleport_finish(s,p)
    def _on_teleport_local_wrapper(self,s,p): isinstance(p,TeleportLocalPacket) and self._on_teleport_local(s,p)
    def _on_avatar_sit_response_wrapper(self,s,p): isinstance(p,AvatarSitResponsePacket) and self._on_avatar_sit_response(s,p)
    def _on_script_dialog_wrapper(self,s,p): isinstance(p,ScriptDialogPacket) and self._on_script_dialog(s,p)
    def _on_script_question_wrapper(self,s,p): isinstance(p,ScriptQuestionPacket) and self._on_script_question(s,p)
    def _on_mute_list_update_wrapper(self,s,p): isinstance(p,MuteListUpdatePacket) and self._on_mute_list_update(s,p)

    def _handle_login_response(self,d:LoginResponseData):
        self.agent_id=d.agent_id;self.session_id=d.session_id;self.secure_session_id=d.secure_session_id;self.circuit_code=d.circuit_code;self.seed_capability=d.seed_capability;self.name=f"{d.first_name} {d.last_name}";self.start_location_request=d.start_location or "last";self.home_info=d.home;il=d.look_at if d.look_at.magnitude_squared()>1e-5 else Vector3(1,0,0);self.movement.camera.look_at(self.current_position+il,self.current_position)
        self.client.inventory.inventory_root_uuid=d.inventory_root;self.client.inventory.library_root_uuid=d.library_root;self.client.inventory.library_owner_id=d.library_owner_id
        if d.inventory_skeleton:self.client.inventory._parse_initial_skeleton(d.inventory_skeleton,d.library_skeleton,d.library_owner_id)
        logger.info(f"AgentManager init for {self.name} ({self.agent_id}). Home:{self.home_info}. InvRoot:{self.client.inventory.inventory_root_uuid}")
    def _handle_sim_connected(self,s:Simulator):
        logger.info(f"Agent: Sim {s.name} connected.");asyncio.create_task(self.movement.start_periodic_updates()) if self.client.settings.send_agent_updates_regularly and self.client.settings.send_agent_updates else self.client.settings.send_agent_updates and asyncio.create_task(self.movement.send_update(True))
        if self.client.settings.send_agent_appearance:logger.debug(f"Auto-requesting wearables for {self.agent_id} in {s.name}");asyncio.create_task(self.appearance.request_wearables())
        else:logger.debug("Auto-requesting wearables disabled.")
    async def _handle_sim_disconnected(self,s:Simulator,r:bool):logger.info(f"Agent: Sim {s.name} disconnected. Logout:{r}");(self.client.network.current_sim==s or not self.client.network.current_sim) and await self.movement.stop_periodic_updates()
    async def move_forward(self,s:bool=True,u:bool=True):await self.movement.move_forward(s,u);async def move_backward(self,s:bool=True,u:bool=True):await self.movement.move_backward(s,u);async def move_left(self,s:bool=True,u:bool=True):await self.movement.move_left(s,u);async def move_right(self,s:bool=True,u:bool=True):await self.movement.move_right(s,u);async def turn_left(self,s:bool=True,u:bool=True):await self.movement.turn_left(s,u);async def turn_right(self,s:bool=True,u:bool=True):await self.movement.turn_right(s,u);async def jump_up(self,s:bool=True,u:bool=True):await self.movement.jump_up(s,u);async def crouch_down(self,s:bool=True,u:bool=True):await self.movement.crouch_down(s,u);async def set_fly(self,a:bool,u:bool=True):await self.movement.set_fly(a,u);async def set_mouselook(self,a:bool,u:bool=True):await self.movement.set_mouselook(a,u);async def stand(self):await self.movement.stand();async def sit_on_ground(self):await self.movement.sit_on_ground();async def set_always_run(self,a:bool,u:bool=True):await self.movement.set_always_run(a,u);async def rotate_body_by(self,a:float,u:bool=True):await self.movement.rotate_body_by(a,u);async def rotate_head_pitch_by(self,a:float,u:bool=True):await self.movement.rotate_head_pitch_by(a,u)
    def _on_agent_data_update(self,p:AgentDataUpdatePacket):
        if p.agent_data.agent_id==self.agent_id:self.name=f"{p.agent_data.first_name_str} {p.agent_data.last_name_str}";logger.info(f"AgentDataUpdate for self: Name='{self.name}', GroupID='{p.agent_data.active_group_id}'");[h(self) for h in self._agent_data_update_handlers]
    async def _on_movement_complete(self,s:Simulator,p:AgentMovementCompletePacket):
        if p.agent_id==self.agent_id:self.current_position=p.data.position;self.current_look_at=p.data.look_at;self.movement.camera.position=p.data.position;self.movement.camera.look_at(p.data.position+p.data.look_at,p.data.position);s.agent_movement_complete=True;logger.info(f"AgentMovementComplete in {s.name}")
    async def _on_avatar_animation(self,s:Simulator,p:AvatarAnimationPacket):
        if p.sender.id==self.agent_id:anims={a.anim_id:a.anim_sequence_id for a in p.animation_list};self.signaled_animations!=anims and (self.signaled_animations:=anims,[h(anims) for h in self._animations_changed_handlers])
    def _on_chat_from_simulator(self,s:Simulator,p:ChatFromSimulatorPacket):args=ChatEventArgs(p.message_str,p.audible_level,p.chat_type,p.source_type,p.from_name_str,p.source_id,p.owner_id,p.position,s);[h(args) for h in self._chat_handlers]
    def _on_improved_instant_message(self,s:Simulator,p:ImprovedInstantMessagePacket):
        ts=datetime.datetime.fromtimestamp(p.message_block.timestamp,tz=datetime.timezone.utc);im_data=InstantMessageData(p.agent_data.from_agent_id,p.message_block.from_agent_name,p.message_block.to_agent_id,p.message_block.parent_estate_id,p.message_block.region_id,p.message_block.position,p.message_block.dialog,p.message_block.from_group,p.message_block.im_session_id,ts,p.message_block.message_str,p.message_block.offline,p.message_block.binary_bucket)
        if im_data.dialog==InstantMessageDialog.RequestTeleport:lure_args=TeleportLureEventArgs(im_data.from_agent_id,im_data.from_agent_name,im_data.message,im_data.im_session_id,s);logger.info(f"Lure from {lure_args.from_agent_name}");[h(lure_args) for h in self._teleport_lure_offered_handlers];return
        [h(IMEventArgs(im_data,s)) for h in self._im_handlers]
    def _fire_teleport_event(self,m,st,f):self.teleport_message=m;self.teleport_status=st;logger.info(f"TP:{st.name}-{m}");args=TeleportEventArgs(m,st,f);[h(args) for h in self._teleport_progress_handlers];st in[TeleportStatus.FAILED,TeleportStatus.FINISHED,TeleportStatus.CANCELLED] and not self._teleport_event.is_set() and self._teleport_event.set()
    def _on_teleport_start(self,s,p:TeleportStartPacket):self._fire_teleport_event("Started",TeleportStatus.START,p.teleport_flags)
    def _on_teleport_progress(self,s,p:TeleportProgressPacket):self._fire_teleport_event(p.message_str,TeleportStatus.PROGRESS,p.teleport_flags)
    def _on_teleport_failed(self,s,p:TeleportFailedPacket):self._fire_teleport_event(p.reason_str,TeleportStatus.FAILED,TeleportFlags.NONE)
    def _on_teleport_cancel(self,s,p:TeleportCancelPacket):self._fire_teleport_event("Cancelled by server",TeleportStatus.CANCELLED,TeleportFlags.NONE)
    async def _on_teleport_finish(self,s:Simulator,p:TeleportFinishPacket):
        self._fire_teleport_event("Src sim done, connecting to dest...",TeleportStatus.PROGRESS,p.teleport_flags)
        new_sim=await self.client.network.connect_to_sim(p.sim_ip_str,p.sim_port,p.region_handle,True,p.seed_capability.decode(),p.region_size_x,p.region_size_y)
        self._fire_teleport_event("New sim connected"if new_sim and new_sim.handshake_complete else "Failed new sim",TeleportStatus.FINISHED if new_sim and new_sim.handshake_complete else TeleportStatus.FAILED,p.teleport_flags)
    def _on_teleport_local(self,s:Simulator,p:TeleportLocalPacket):self.current_position=p.position;self.current_look_at=p.look_at;self.movement.camera.position=p.position;self.movement.camera.look_at(p.look_at,p.position);asyncio.create_task(self.movement.send_update(True));self._fire_teleport_event(f"Local TP to{p.position}",TeleportStatus.FINISHED,p.teleport_flags)
    def _on_avatar_sit_response(self,s:Simulator,p:AvatarSitResponsePacket):self.sitting_on=p.sit_object_id;logger.info(f"SitResponse on {self.sitting_on}. Pos:{p.sit_position}");self.movement.flags|=AgentFlags.SITTING;self.movement.agent_controls=ControlFlags.NONE;args=AvatarSitResponseEventArgs(p.sit_object_id,p.autopilot,p.camera_at_offset,p.camera_eye_offset,p.force_mouselook,p.sit_position,p.sit_rotation);[h(args) for h in self._avatar_sit_response_handlers]
    def _on_script_dialog(self,s:Simulator,p:ScriptDialogPacket):args=ScriptDialogEventArgs(p.object_id,p.object_name_str,p.first_name_str,p.last_name_str,p.message_str,p.image_id,p.chat_channel,p.button_labels_str,s);logger.info(f"ScriptDialog from '{args.object_name}': '{args.message[:50]}...' Buttons: {args.button_labels}");[h(args) for h in self._script_dialog_handlers]
    def _on_script_question(self,s:Simulator,p:ScriptQuestionPacket):args=ScriptQuestionEventArgs(p.task_id,p.item_id,p.object_name_str,p.object_owner_name_str,p.questions,s);logger.info(f"ScriptQuestion from '{args.object_name}': Permissions={args.questions!r}");[h(args) for h in self._script_question_handlers]
    def _on_mute_list_update(self,source_sim:Simulator,packet:MuteListUpdatePacket):
        filename=packet.filename_str;crc=packet.mute_data.MuteCRC;logger.info(f"Rcvd MuteListUpdate,file:{filename},CRC:{crc}.")
        if not filename:logger.warning("MuteListUpdate w/ empty filename.");return
        try:mute_list_vfile_id=CustomUUID(filename)
        except ValueError:logger.error(f"Could not parse VFileID from MuteListUpdate filename:{filename}");return
        self.client.assets.register_asset_received_handler(mute_list_vfile_id,self._parse_mute_list_asset)
        logger.info(f"Requesting mute list asset:{filename}(VFileID:{mute_list_vfile_id})")
        # Pass the vfile_id as asset_uuid for context in _fire_asset_received if it's not a real asset UUID
        asyncio.create_task(self.client.assets.request_asset_xfer(filename,False,
                                                                  vfile_id=mute_list_vfile_id,
                                                                  vfile_type=AssetType.Unknown, # Mute list isn't a standard asset type for parsing
                                                                  item_id_for_callback=mute_list_vfile_id))

    # Signature updated to match new AssetReceivedHandler
    def _parse_mute_list_asset(self, success: bool, asset_obj_or_data: Any, # Asset | bytes | None
                               asset_type_enum: AssetType, asset_uuid: CustomUUID,
                               vfile_id_for_callback: CustomUUID | None,
                               error_message: str | None = None):
        if not success or not asset_obj_or_data:
            logger.error(f"Failed to download mute list asset {asset_uuid} (VFile Context: {vfile_id_for_callback}): {error_message or 'No data'}")
            return

        mute_list_text = ""
        # Mute lists are expected to be plain text, so we primarily care about raw_data if it's an Asset object.
        if isinstance(asset_obj_or_data, self.client.assets.Asset): # Check if it's an Asset instance
            # The base Asset class stores data in raw_data and from_bytes just sets loaded_successfully.
            # If a specialized mute list asset type were created, it might parse into specific fields.
            mute_list_text = asset_obj_or_data.raw_data.decode('utf-8', errors='replace')
            if not asset_obj_or_data.loaded_successfully and not mute_list_text: # If parsing failed and no raw data usable
                 logger.error(f"Mute list asset {asset_uuid} (VFile: {vfile_id_for_callback}) was not loaded successfully by AssetManager and raw data is empty.")
                 return
        elif isinstance(asset_obj_or_data, bytes): # Fallback if raw bytes were passed
            mute_list_text = asset_obj_or_data.decode('utf-8', errors='replace')
        else:
            logger.error(f"Received unexpected data type for mute list asset {asset_uuid} (VFile: {vfile_id_for_callback}): {type(asset_obj_or_data)}")
            return

        try:
            logger.debug(f"Mute list asset for {asset_uuid} (VFile: {vfile_id_for_callback}):\n{mute_list_text[:500]}...")
            new_mute_list:Dict[str,MuteEntry]={};lines=mute_list_text.splitlines()
            for line in lines:
                parts=line.split();
                if not parts or parts[0]!='m':
                    if line.strip():logger.debug(f"Skipping non-mute line in mute asset:{line}");continue
                if len(parts)>=5:
                    try:
                        mute_type_val=int(parts[1]);mute_id_str=parts[2];mute_name=" ".join(parts[3:-1]);mute_flags_val=int(parts[-1])
                        mute_type=MuteType(mute_type_val);mute_id=CustomUUID(mute_id_str) if mute_id_str!="0" else CustomUUID.ZERO;mute_flags=MuteFlags(mute_flags_val)
                        key=f"{mute_id}|{mute_name}";new_mute_list[key]=MuteEntry(type_=mute_type,id_=mute_id,name=mute_name,flags=mute_flags)
                    except(ValueError,IndexError)as e:logger.warning(f"Could not parse mute line:'{line}'. Err:{e}")
                else:logger.warning(f"Malformed mute line:'{line}'")
            self.mute_list=new_mute_list;logger.info(f"Parsed mute list from asset {vfile_id}. {len(self.mute_list)} entries.")
            for handler in self._mute_list_updated_handlers:
                try:handler(self.mute_list.copy())
                except Exception as e:logger.error(f"Err in mute_list_updated_handler:{e}")
        except Exception as e:logger.exception(f"Error processing mute list asset {vfile_id}:{e}")

    # Public Methods (condensed)
    def register_chat_handler(self,c:ChatHandler):self._chat_handlers.append(c);def unregister_chat_handler(self,c:ChatHandler):self._chat_handlers.remove(c)
    async def chat(self,m:str,ch:int=0,t:ChatType=ChatType.NORMAL):await self.client.network.send_packet(ChatFromViewerPacket(m,ch,t),self.client.network.current_sim) if self.client.network.current_sim else logger.warning("No sim for chat")
    def register_im_handler(self,c:IMHandler):self._im_handlers.append(c);def unregister_im_handler(self,c:IMHandler):self._im_handlers.remove(c)
    async def instant_message(self,target_id:CustomUUID,message:str,session_id:CustomUUID|None=None,dialog:InstantMessageDialog=InstantMessageDialog.MessageFromAgent,offline:InstantMessageOnline=InstantMessageOnline.Online):
        if not self.client.network.current_sim:logger.warning("No current sim for IM");return
        if session_id is None:session_id=CustomUUID(int(self.agent_id)^int(target_id)) if target_id!=self.agent_id else self.agent_id
        im=ImprovedInstantMessagePacket();im.agent_data.from_agent_id=self.agent_id;im.message_block.from_agent_name_bytes=self.name.encode();im.message_block.to_agent_id=target_id;im.message_block.message=message.encode();im.message_block.dialog=dialog;im.message_block.offline=offline;im.message_block.im_session_id=session_id;im.message_block.timestamp=int(time.time());im.message_block.position=self.current_position;im.message_block.region_id=self.client.network.current_sim.id if self.client.network.current_sim else CustomUUID.ZERO;im.header.reliable=True;await self.client.network.send_packet(im,self.client.network.current_sim)
    def register_teleport_progress_handler(self,c:TeleportProgressHandler):self._teleport_progress_handlers.append(c);def unregister_teleport_progress_handler(self,c:TeleportProgressHandler):self._teleport_progress_handlers.remove(c)
    async def teleport_to_landmark(self,l_uuid:CustomUUID,t_sec:float=60.0)->bool:
        if not self.client.network.current_sim:self._fire_teleport_event("No sim",TeleportStatus.FAILED,TeleportFlags.NONE);return False
        self._teleport_event.clear();self.teleport_status=TeleportStatus.NONE;self._fire_teleport_event(f"TP to landmark {l_uuid}",TeleportStatus.START,TeleportFlags.ViaLandmark);await self.client.network.send_packet(TeleportLandmarkRequestPacket(self.agent_id,self.session_id,l_uuid),self.client.network.current_sim)
        try:await asyncio.wait_for(self._teleport_event.wait(),timeout=t_sec)
        except asyncio.TimeoutError: self.teleport_status not in[TeleportStatus.FAILED,TeleportStatus.FINISHED,TeleportStatus.CANCELLED] and self._fire_teleport_event("Timeout",TeleportStatus.FAILED,TeleportFlags.NONE)
        return self.teleport_status==TeleportStatus.FINISHED
    async def teleport_to_location(self,r_handle:int,pos:Vector3,look:Vector3,t_sec:float=60.0)->bool:
        if not self.client.network.current_sim:self._fire_teleport_event("No sim",TeleportStatus.FAILED,TeleportFlags.NONE);return False
        self._teleport_event.clear();self.teleport_status=TeleportStatus.NONE;self._fire_teleport_event(f"TP to {r_handle} at {pos}",TeleportStatus.START,TeleportFlags.ViaLocation);await self.client.network.send_packet(TeleportLocationRequestPacket(self.agent_id,self.session_id,r_handle,pos,look),self.client.network.current_sim)
        try:await asyncio.wait_for(self._teleport_event.wait(),timeout=t_sec)
        except asyncio.TimeoutError: self.teleport_status not in[TeleportStatus.FAILED,TeleportStatus.FINISHED,TeleportStatus.CANCELLED] and self._fire_teleport_event("Timeout",TeleportStatus.FAILED,TeleportFlags.NONE)
        return self.teleport_status==TeleportStatus.FINISHED
    async def go_home(self,t_sec:float=60.0)->bool:
        if not self.home_info or self.home_info.region_handle==0:self._fire_teleport_event("Home not set",TeleportStatus.FAILED,TeleportFlags.NONE);return False
        return await self.teleport_to_location(self.home_info.region_handle,self.home_info.position,self.home_info.look_at,t_sec)
    def register_avatar_sit_response_handler(self,c:AvatarSitResponseHandler):self._avatar_sit_response_handlers.append(c);def unregister_avatar_sit_response_handler(self,c:AvatarSitResponseHandler):self._avatar_sit_response_handlers.remove(c)
    async def request_sit(self,target_id:CustomUUID,offset:Vector3=Vector3.ZERO):
        if not self.client.network.current_sim:logger.warning("No current sim for sit request");return
        p=AgentRequestSitPacket(self.agent_id,self.session_id,target_id,offset);p.header.reliable=True;await self.client.network.send_packet(p,self.client.network.current_sim)
    async def sit(self):
        if not self.client.network.current_sim:logger.warning("No current sim for sit");return
        p=AgentSitPacket(self.agent_id,self.session_id);p.header.reliable=True;await self.client.network.send_packet(p,self.client.network.current_sim)
    def register_teleport_lure_offered_handler(self,c:TeleportLureOfferedHandler):self._teleport_lure_offered_handlers.append(c);def unregister_teleport_lure_offered_handler(self,c:TeleportLureOfferedHandler):self._teleport_lure_offered_handlers.remove(c)
    async def send_teleport_lure(self,target_id:CustomUUID,message:str="Join me!"):
        if not self.client.network.current_sim:logger.warning("No current sim for lure");return
        p=StartLurePacket(self.agent_id,self.session_id,0,message,target_id);await self.client.network.send_packet(p,self.client.network.current_sim)
    async def respond_to_teleport_lure(self,requester_id:CustomUUID,lure_id:CustomUUID,accept:bool):
        if not self.client.network.current_sim:logger.warning("No current sim for lure response");return
        if accept:p=TeleportLureRequestPacket(self.agent_id,self.session_id,lure_id,TeleportFlags.ViaLure);await self.client.network.send_packet(p,self.client.network.current_sim);self._teleport_event.clear();self._fire_teleport_event(f"Accepted lure from{requester_id}",TeleportStatus.START,TeleportFlags.ViaLure)
        else:await self.instant_message(requester_id,"",lure_id,InstantMessageDialog.DenyTeleport)
    async def animate(self,anims:Dict[CustomUUID,bool],reliable:bool=True):
        if not self.client.network.current_sim:logger.warning("No sim for animate");return
        p=AgentAnimationPacket(self.agent_id,self.session_id,anims);p.header.reliable=reliable;await self.client.network.send_packet(p,self.client.network.current_sim)
    async def play_animation(self,anim_uuid:CustomUUID,reliable:bool=True):await self.animate({anim_uuid:True},reliable)
    async def stop_animation(self,anim_uuid:CustomUUID,reliable:bool=True):await self.animate({anim_uuid:False},reliable)
    async def activate_gesture(self,item_id:CustomUUID,asset_id:CustomUUID):
        if not self.client.network.current_sim:logger.warning("No sim for gesture");return
        p=ActivateGesturesPacket(self.agent_id,self.session_id,item_id,asset_id);await self.client.network.send_packet(p,self.client.network.current_sim);self.active_gestures[item_id]=asset_id
    async def deactivate_gesture(self,item_id:CustomUUID):
        if not self.client.network.current_sim:logger.warning("No sim for gesture");return
        p=DeactivateGesturesPacket(self.agent_id,self.session_id,item_id);await self.client.network.send_packet(p,self.client.network.current_sim);item_id in self.active_gestures and self.active_gestures.pop(item_id)
    def register_script_dialog_handler(self,c:ScriptDialogHandler):self._script_dialog_handlers.append(c);def unregister_script_dialog_handler(self,c:ScriptDialogHandler):self._script_dialog_handlers.remove(c)
    def register_script_question_handler(self,c:ScriptQuestionHandler):self._script_question_handlers.append(c);def unregister_script_question_handler(self,c:ScriptQuestionHandler):self._script_question_handlers.remove(c)
    async def respond_to_script_dialog(self,obj_id:CustomUUID,chan:int,btn_idx:int,btn_lbl:str,sim:Simulator|None=None):
        ts=sim if sim else self.client.network.current_sim; await self.client.network.send_packet(ScriptDialogReplyPacket(self.agent_id,self.session_id,obj_id,chan,btn_idx,btn_lbl),ts) if ts else logger.warning("No sim for script dialog reply")
    async def respond_to_script_permission_request(self,task_id:CustomUUID,item_id:CustomUUID,perms:ScriptPermission,sim:Simulator|None=None):
        ts=sim if sim else self.client.network.current_sim; await self.client.network.send_packet(ScriptAnswerYesPacket(self.agent_id,self.session_id,task_id,item_id,perms),ts) if ts else logger.warning("No sim for script perm response")
    def register_mute_list_updated_handler(self,c:MuteListUpdatedHandler):self._mute_list_updated_handlers.append(c);def unregister_mute_list_updated_handler(self,c:MuteListUpdatedHandler):self._mute_list_updated_handlers.remove(c)
    async def request_mute_list(self):
        if not self.client.network.current_sim:logger.warning("No sim for mute list req");return
        await self.client.network.send_packet(MuteListRequestPacket(self.agent_id,self.session_id,0),self.client.network.current_sim)
    async def update_mute_entry(self,type_:MuteType,id_:CustomUUID,name:str,flags:MuteFlags=MuteFlags.DEFAULT):
        if not self.client.network.current_sim:logger.warning("No sim for mute update");return
        await self.client.network.send_packet(UpdateMuteListEntryPacket(self.agent_id,self.session_id,type_,id_,name,flags),self.client.network.current_sim)
        k=f"{id_}|{name}";self.mute_list[k]=MuteEntry(type_,id_,name,flags);[h(self.mute_list.copy())for h in self._mute_list_updated_handlers]
    async def remove_mute_entry(self,id_:CustomUUID,name:str):
        if not self.client.network.current_sim:logger.warning("No sim for mute remove");return
        await self.client.network.send_packet(RemoveMuteListEntryPacket(self.agent_id,self.session_id,id_,name),self.client.network.current_sim)
        k=f"{id_}|{name}";k in self.mute_list and self.mute_list.pop(k);[h(self.mute_list.copy())for h in self._mute_list_updated_handlers]
    def __str__(self): return f"Agent(Name='{self.name}', ID='{self.agent_id}')"
