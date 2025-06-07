import uuid
import enum
import platform
import dataclasses
import datetime
import ipaddress
import logging

from pylibremetaverse.types import CustomUUID, Vector3
from pylibremetaverse.structured_data import (
    OSDMap, OSDArray, OSDType, parse_llsd_xml,
    OSDBoolean, OSDInteger, OSDReal, OSDString, OSDUUID, OSDDate, OSDBinary
)

logger = logging.getLogger(__name__)

class LoginStatus(enum.Enum):
    FAILED=0;NONE=1;CONNECTING_TO_LOGIN=2;READING_RESPONSE=3;CONNECTING_TO_SIM=4;REDIRECTING=5;SUCCESS=6
class LastExecStatus(enum.Enum):
    NORMAL=0;FROZE=1;FORCED_CRASH=2;OTHER_CRASH=3;LOGOUT_FROZE=4;LOGOUT_CRASH=5

class LoginCredential:
    def __init__(self,fn:str,ln:str,pw_md5:str,tok:str="",mfa_h:str=""):self.first_name=fn;self.last_name=ln;self.password_md5=pw_md5;self.token=tok;self.mfa_hash=mfa_h
    def __repr__(self):return f"<LoginCredential First:{self.first_name} Last:{self.last_name}>"

class LoginParams:
    def __init__(self,cr,cred:LoginCredential,ch:str,ver:str,luri_ovr:str|None=None,st:str="last",t_ms:int=60000):
        self.client_ref=cr;self.credential=cred;self.first_name=cred.first_name;self.last_name=cred.last_name;self.password_md5=cred.password_md5;self.token=cred.token;self.mfa_hash=cred.mfa_hash;self.start_location=st;self.channel=ch;self.version=ver;self.login_uri=luri_ovr if luri_ovr else self.client_ref.settings.login_server;self.timeout_ms=t_ms
        self.options=["inventory-root","inventory-skeleton","inventory-lib-root","inventory-lib-owner","inventory-skel-lib","gestures","event_categories","event_notifications","classified_categories","buddy-list","ui-config","login-flags","global-textures","adult_compliant"]
        if self.mfa_hash:self.options.append("mfa")
        pi=self._get_platform_info();self.platform=pi['platform'];self.platform_version=pi['platform_version'];self.mac=pi['mac'];self.id0=pi['id0']
    def _get_platform_info(self)->dict:
        p=platform.system();os_s,os_v_d="Unknown","0.0"
        if p=="Windows":os_s="Win";os_v_d=platform.version()
        elif p=="Darwin":os_s="Mac";os_v_d=platform.mac_ver()[0]
        elif p=="Linux":os_s="Linux";os_v_d=platform.release()
        return{"platform":os_s,"platform_version":os_v_d,"mac":"00:00:00:00:00:00","id0":"pylibremetaverse_id0"}
    def __repr__(self):return f"<LoginParams User:{self.first_name} {self.last_name} URI:{self.login_uri}>"

@dataclasses.dataclass
class BuddyListEntry:buddy_id:CustomUUID;buddy_rights_given:int;buddy_rights_has:int
@dataclasses.dataclass
class HomeInfo:region_handle:int;position:Vector3;look_at:Vector3

class LoginResponseData:
    def __init__(self):
        self.success:bool=False;self.reason:str|None=None;self.message:str|None=None
        self.agent_id:CustomUUID=CustomUUID.ZERO;self.session_id:CustomUUID=CustomUUID.ZERO;self.secure_session_id:CustomUUID=CustomUUID.ZERO
        self.first_name:str|None=None;self.last_name:str|None=None;self.start_location:str|None=None
        self.agent_access:str|None=None;self.agent_access_max:str|None=None;self.look_at:Vector3=Vector3.ZERO
        self.home:HomeInfo|None=None;self.sim_ip:str|None=None;self.sim_port:int=0;self.sim_version:str|None=None
        self.region_x:int=0;self.region_y:int=0;self.region_size_x:int=256;self.region_size_y:int=256;self.region_handle:int=0
        self.circuit_code:int=0;self.seed_capability:str|None=None;self.buddy_list:list[BuddyListEntry]=[]
        self.inventory_root:CustomUUID=CustomUUID.ZERO;self.library_root:CustomUUID=CustomUUID.ZERO
        self.library_owner_id:CustomUUID=CustomUUID.ZERO # Corrected
        self.seconds_since_epoch:int=0
        self.gestures:OSDArray|list=OSDArray();self.event_categories:OSDArray|list=OSDArray()
        self.classified_categories:OSDArray|list=OSDArray();self.ui_config:OSDMap|dict=OSDMap() # ui-config is a map
        self.login_flags:OSDMap|dict=OSDMap();self.global_textures:OSDMap|dict=OSDMap()
        self.inventory_skeleton:OSDArray|list=OSDArray() # Corrected
        self.library_skeleton:OSDArray|list=OSDArray() # Corrected
        self.udp_blacklist:list[str]=[];self.max_agent_groups:int=0;self.openid_token:str|None=None
        self.openid_url:str|None=None;self.agent_flags:int=0;self.adult_compliant:bool=False

    def parse_xmlrpc(self, data_hash): pass # Placeholder
    def parse_llsd(self, llsd_xml_data: str | bytes):
        if not llsd_xml_data:self.success=False;self.reason="nodata";self.message="No login data.";return
        parsed_osd = parse_llsd_xml(llsd_xml_data)
        if not isinstance(parsed_osd,OSDMap):self.success=False;self.reason="badformat";self.message="Malformed login response.";return
        def get_val(k:str,d,t:OSDType):v=parsed_osd.get(k);return v if v and v.osd_type==t else d
        self.success=get_val('login',OSDBoolean(False),OSDType.BOOLEAN).as_boolean();self.reason=get_val('reason',OSDString(""),OSDType.STRING).as_string();self.message=get_val('message',OSDString(""),OSDType.STRING).as_string()
        if not self.success:logger.info(f"Login failed. R:{self.reason}, M:{self.message}");return
        self.agent_id=get_val('agent_id',OSDUUID(CustomUUID.ZERO),OSDType.UUID).as_uuid();self.session_id=get_val('session_id',OSDUUID(CustomUUID.ZERO),OSDType.UUID).as_uuid();self.secure_session_id=get_val('secure_session_id',OSDUUID(CustomUUID.ZERO),OSDType.UUID).as_uuid()
        self.first_name=get_val('first_name',OSDString(""),OSDType.STRING).as_string();self.last_name=get_val('last_name',OSDString(""),OSDType.STRING).as_string();self.start_location=get_val('start_location',OSDString("last"),OSDType.STRING).as_string();self.agent_access=get_val('agent_access',OSDString("M"),OSDType.STRING).as_string();self.agent_access_max=get_val('agent_access_max',OSDString(""),OSDType.STRING).as_string()
        look_at_str=get_val('look_at',OSDString("[0.0,0.0,0.0]"),OSDType.STRING).as_string();parts=look_at_str.strip('[] ').split(',');self.look_at=Vector3(*map(float,parts)) if len(parts)==3 else Vector3.ZERO
        home_osd=parsed_osd.get('home');
        if isinstance(home_osd,OSDMap):h_map=home_osd.as_python_object();rh=int(h_map.get('region_handle',0));pos=h_map.get('position',[0,0,0]);la=h_map.get('look_at',[0,0,0]);self.home=HomeInfo(rh,Vector3(*pos),Vector3(*la))
        sim_ip_osd=parsed_osd.get('sim_ip');self.sim_ip=ipaddress.ip_address(sim_ip_osd.as_string()).__str__() if sim_ip_osd and sim_ip_osd.osd_type==OSDType.STRING else None;self.sim_port=get_val('sim_port',OSDInteger(0),OSDType.INTEGER).as_integer()
        self.region_x=get_val('region_x',OSDInteger(0),OSDType.INTEGER).as_integer();self.region_y=get_val('region_y',OSDInteger(0),OSDType.INTEGER).as_integer();self.region_handle=(self.region_x<<32)+self.region_y
        self.circuit_code=get_val('circuit_code',OSDInteger(0),OSDType.INTEGER).as_integer();self.seed_capability=get_val('seed_capability',OSDString(None),OSDType.STRING).as_string()
        bl_osd=parsed_osd.get('buddy-list');self.buddy_list=[BuddyListEntry(item.get('buddy_id').as_uuid(),item.get('buddy_rights_given').as_integer(),item.get('buddy_rights_has').as_integer()) for item in bl_osd if isinstance(item,OSDMap)] if isinstance(bl_osd,OSDArray) else []
        inv_root_osd=get_val('inventory-root',OSDArray([]),OSDType.ARRAY);self.inventory_root=inv_root_osd[0].get('folder_id').as_uuid() if inv_root_osd and inv_root_osd[0]and isinstance(inv_root_osd[0],OSDMap)else CustomUUID.ZERO
        lib_root_osd=get_val('inventory-lib-root',OSDArray([]),OSDType.ARRAY);self.library_root=lib_root_osd[0].get('folder_id').as_uuid() if lib_root_osd and lib_root_osd[0]and isinstance(lib_root_osd[0],OSDMap)else CustomUUID.ZERO
        lib_owner_osd=get_val('inventory-lib-owner',OSDArray([]),OSDType.ARRAY);self.library_owner_id=lib_owner_osd[0].get('agent_id').as_uuid() if lib_owner_osd and lib_owner_osd[0]and isinstance(lib_owner_osd[0],OSDMap)else CustomUUID.ZERO
        self.seconds_since_epoch=get_val('seconds_since_epoch',OSDInteger(0),OSDType.INTEGER).as_integer()
        for k,a in[('gestures','gestures'),('event_categories','event_categories'),('classified_categories','classified_categories'),('inventory-skeleton','inventory_skeleton'),('inventory-skel-lib','library_skeleton')]:setattr(self,a,get_val(k,OSDArray([]),OSDType.ARRAY))
        for k,a in[('ui-config','ui_config'),('login-flags','login_flags'),('global-textures','global_textures')]:setattr(self,a,get_val(k,OSDMap({}),OSDType.MAP))
        self.max_agent_groups=get_val('max-agent-groups',OSDInteger(0),OSDType.INTEGER).as_integer();udp_bl_osd=parsed_osd.get('udp_blacklist',parsed_osd.get('udp-blacklist'));self.udp_blacklist=[i.as_string() for i in udp_bl_osd if i.osd_type==OSDType.STRING] if isinstance(udp_bl_osd,OSDArray) else []
        self.openid_token=get_val('openid_token',OSDString(None),OSDType.STRING).as_string();self.openid_url=get_val('openid_url',OSDString(None),OSDType.STRING).as_string();self.agent_flags=get_val('agent_flags',OSDInteger(0),OSDType.INTEGER).as_integer();self.adult_compliant=get_val('adult_compliant',OSDBoolean(False),OSDType.BOOLEAN).as_boolean()

    def __str__(self):return(f"<LoginResponseData Success:{self.success} Agent:{self.first_name} {self.last_name} AgentID:{self.agent_id} Sim:{self.sim_ip}:{self.sim_port}>")
