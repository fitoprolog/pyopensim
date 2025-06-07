import enum
import dataclasses
import struct
import logging

from pylibremetaverse.types import CustomUUID
from pylibremetaverse import utils as plm_utils

DEFAULT_MAX_PACKET_SIZE = 1200
logger = logging.getLogger(__name__)

class PacketType(enum.Enum):
    TestPacket = 0; UseCircuitCode = 1; RegionHandshake = 4; RegionHandshakeReply = 5
    CompleteAgentMovement = 7; AgentMovementComplete = 8; LogoutRequest = 9; CloseCircuit = 10
    EconomyDataRequest = 11; TeleportLocationRequest = 12; TeleportLandmarkRequest = 13
    TeleportFinish = 14; TeleportLocal = 15; UpdateMuteListEntry = 20; RemoveMuteListEntry = 21
    MuteListRequest = 22; MuteListUpdate = 23; TeleportStart = 25; TeleportProgress = 26
    TeleportFailed = 27; ChatFromViewer = 46; ChatFromSimulator = 44; StartLure = 53
    ImprovedInstantMessage = 54; AgentRequestSit = 55; AgentSit = 56; AvatarSitResponse = 57
    TeleportCancel = 58; AvatarAnimation = 59; AgentAnimation = 60; AgentDataUpdate = 74
    ActivateGestures = 71; DeactivateGestures = 72; ScriptDialog = 76; ScriptDialogReply = 77
    ScriptQuestion = 81; ScriptAnswerYes = 82

    ObjectUpdateCached = 6; RequestMultipleObjects = 48; KillObject = 11 # Note: KillObject is Server->Client
    RequestObjectPropertiesFamily = 16; ObjectPropertiesFamily = 63; ObjectProperties = 90
    ObjectSelect = 17; ObjectDeselect = 18; ObjectLink = 29; ObjectDelink = 30
    ObjectMove = 31; ObjectScale = 32; ObjectRotation = 33
    ObjectName = 34; ObjectDescription = 35; ObjectText = 36; ObjectClickAction = 37
    ObjectAdd = 38
    ObjectAdd = 38
    ObjectGrab = 26                # Low Freq (0xFFFFFF1A) Client -> Server
    ObjectDeGrab = 27              # Low Freq (0xFFFFFF1B) Client -> Server
    AssetUploadRequest = 39
    AssetUploadComplete = 40
    UpdateCreateInventoryItem = 41 # Client -> Server
    UpdateInventoryItem = 41       # Server -> Client (Uses the same ID as request, but different direction/content)

    # Friends Packets (Client -> Server)
    OfferFriendship = 111      # Low Freq (0xFFFFFF6F)
    AcceptFriendship = 112     # Low Freq (0xFFFFFF70)
    DeclineFriendship = 113    # Low Freq (0xFFFFFF71)
    OnlineNotification = 114   # Low Freq (0xFFFFFF72) - Server to Client
    OfflineNotification = 115  # Low Freq (0xFFFFFF73) - Server to Client
    FindAgent = 116            # Low Freq (0xFFFFFF74) - Client to Server
    AgentOnlineStatus = 117    # Low Freq (0xFFFFFF75) - Server to Client
    ChangeUserRights = 118     # Low Freq (0xFFFFFF76) - Client to Server
    TerminateFriendship = 119  # Low Freq (0xFFFFFF77) - Client to Server

    # Parcel Packets
    ParcelPropertiesRequest = 92 # Low Freq (0xFFFFFF5C) - Client to Server
    ParcelProperties = 77        # Low Freq (0xFFFFFF4D) - Server to Client
    ParcelAccessListRequest = 86 # Low Freq (0xFFFFFF56) - Client to Server
    ParcelAccessListReply = 87   # Low Freq (0xFFFFFF57) - Server to Client (matches C# ParcelAccessList)
    # ParcelDwellRequest = 88    # Low Freq (0xFFFFFF58)
    # ParcelDwell = 89           # Low Freq (0xFFFFFF59)
    # ParcelInfoRequest = 98     # Low Freq (0xFFFFFF62)
    # ParcelInfoReply = 99       # Low Freq (0xFFFFFF63)
    # Other parcel packets...

    # Group Packets
    AgentGroupDataUpdate = 52    # Low Freq (0xFFFFFF34) - Server to Client
    AgentSetGroup = 109          # Low Freq (0xFFFFFF6D) - Client to Server

    # Image/Texture Packets (UDP)
    RequestImage = 19
    ImageData = 26
    ImageNotInDatabase = 27

    # Appearance Packets
    AgentSetAppearance = 205      # Low Freq, 0xFFFFFECD
    AvatarAppearance = 204        # Low Freq, 0xFFFFFECC
    AgentWearablesUpdate = 206    # Low Freq, 0xFFFFFECE
    AgentWearablesRequest = 207   # Low Freq, 0xFFFFFECF
    AgentIsNowWearing = 62        # Low Freq, 0xFFFFFF3E

    PacketAck = 244

    # High Frequency
    ObjectUpdate = 5
    ImprovedTerseObjectUpdate = 7
    AgentUpdate = 1001
    AgentThrottle = 1002

    Unhandled = -1

@enum.unique
class PacketFlags(enum.IntFlag):
    NONE=0;ZEROCODED=0x80;RELIABLE=0x40;RESENT=0x20;ACK=0x10
@dataclasses.dataclass
class PacketHeader:
    sequence:int=0;flags:PacketFlags=PacketFlags.NONE;SIZE=4
    @classmethod
    def from_bytes(cls,b:bytes,o:int=0)->"PacketHeader":
        if len(b)<o+cls.SIZE:raise ValueError("Buffer too small");f=b[o];s=(b[o+1]<<16)|(b[o+2]<<8)|b[o+3];return cls(s,PacketFlags(f))
    def to_bytes(self)->bytes:h=bytearray(self.SIZE);h[0]=self.flags.value;h[1]=(self.sequence>>16)&0xFF;h[2]=(self.sequence>>8)&0xFF;h[3]=self.sequence&0xFF;return bytes(h)
    @property
    def reliable(self)->bool:return bool(self.flags&PacketFlags.RELIABLE)
    @reliable.setter
    def reliable(self,v:bool):self.flags=self.flags|PacketFlags.RELIABLE if v else self.flags&~PacketFlags.RELIABLE
class Packet:
    def __init__(self,t:PacketType,h:PacketHeader|None=None):self.type:PacketType=t;self.header:PacketHeader=h if h is not None else PacketHeader()
    def from_bytes_body(self,b:bytes,o:int,l:int):raise NotImplementedError(f"{self.__class__.__name__}")
    def to_bytes(self)->bytes:raise NotImplementedError(f"{self.__class__.__name__}")
    def to_bytes_with_header(self,max_s:int=DEFAULT_MAX_PACKET_SIZE)->bytes:
        hb=self.header.to_bytes();bb=self.to_bytes();ufp=hb+bb
        if self.header.flags&PacketFlags.ZEROCODED:
            db=bytearray(max_s+100);el=plm_utils.zero_encode(ufp,db)
            if el>0 and el<len(ufp):logger.debug(f"Zero-coded {self.type.name} from {len(ufp)} to {el}b.");fpd=bytes(db[:el])
            else:self.header.flags&=~PacketFlags.ZEROCODED;logger.debug(f"Zero-coding {self.type.name} not beneficial. Sending unencoded.");fpd=ufp
        else:fpd=ufp
        if len(fpd)>max_s:logger.error(f"Packet {self.type.name}(Seq:{self.header.sequence})exceeds MAX_PACKET_SIZE({len(fpd)}>{max_s})")
        return fpd
    def __str__(self):return f"{self.type.name}(Seq={self.header.sequence}, Flags={self.header.flags})"
    def __repr__(self):return f"<{self.__class__.__name__} type={self.type.name} seq={self.header.sequence} flags={self.header.flags!r}>"
