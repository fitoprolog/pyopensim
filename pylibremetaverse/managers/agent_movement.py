import asyncio
import time
import logging
import hashlib # For creating hash of update state

from typing import TYPE_CHECKING

from .agent_camera import AgentCamera
from pylibremetaverse.types.enums import ControlFlags, AgentState, AgentFlags
from pylibremetaverse.types import Vector3, Quaternion
from pylibremetaverse.network.packets_agent import AgentUpdatePacket
from pylibremetaverse.network.simulator import Simulator # For type hint

if TYPE_CHECKING:
    from .agent_manager import AgentManager # To avoid circular import

logger = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = 0.5 # seconds

class AgentMovementManager:
    """Handles agent movement, camera, and control flags, sending AgentUpdatePackets."""

    def __init__(self, agent_manager_ref: 'AgentManager'):
        self.agent_manager = agent_manager_ref
        self.client = agent_manager_ref.client # Convenience ref to GridClient

        self.camera = AgentCamera()
        self.agent_controls: ControlFlags = ControlFlags.NONE
        self.body_rotation: Quaternion = Quaternion.Identity
        self.head_rotation: Quaternion = Quaternion.Identity # Relative to body

        self.always_run: bool = False # This is often set by server via AgentWearablesUpdate
        self.flags: AgentFlags = AgentFlags.NONE # Such as FLYING, MOUSELOOK, SITTING
        self.state: AgentState = AgentState.NONE # Animation state, e.g. WALKING, FLYING

        self._update_timer_task: asyncio.Task | None = None
        self._last_update_hash: int = 0
        self._auto_reset_controls: bool = True # If true, non-persistent controls reset after each update

        # Persistent flags that should not be reset by _auto_reset_controls
        self._persistent_controls = (
            ControlFlags.AGENT_CONTROL_FLY |
            ControlFlags.AGENT_CONTROL_MOUSELOOK
            # Potentially others if they represent toggled states rather than momentary actions
        )


    # --- Control Properties ---
    # These provide a more user-friendly way to set/check control flags.
    # Example for 'forward' control:
    @property
    def forward(self) -> bool: return bool(self.agent_controls & ControlFlags.AGENT_CONTROL_AT_POS)
    @forward.setter
    def forward(self, value: bool): self._set_control(ControlFlags.AGENT_CONTROL_AT_POS, value)

    @property
    def backward(self) -> bool: return bool(self.agent_controls & ControlFlags.AGENT_CONTROL_AT_NEG)
    @backward.setter
    def backward(self, value: bool): self._set_control(ControlFlags.AGENT_CONTROL_AT_NEG, value)

    # ... Add similar properties for LEFT_POS, LEFT_NEG, UP_POS (jump), UP_NEG (crouch), RUN, FLY, MOUSELOOK etc.

    @property
    def mouselook(self) -> bool: return bool(self.flags & AgentFlags.MOUSELOOK)
    @mouselook.setter
    def mouselook(self, value: bool):
        if value: self.flags |= AgentFlags.MOUSELOOK; self.agent_controls |= ControlFlags.AGENT_CONTROL_MOUSELOOK
        else: self.flags &= ~AgentFlags.MOUSELOOK; self.agent_controls &= ~ControlFlags.AGENT_CONTROL_MOUSELOOK

    @property
    def fly(self) -> bool: return bool(self.flags & AgentFlags.FLYING)
    @fly.setter
    def fly(self, value: bool):
        if value: self.flags |= AgentFlags.FLYING; self.agent_controls |= ControlFlags.AGENT_CONTROL_FLY
        else: self.flags &= ~AgentFlags.FLYING; self.agent_controls &= ~ControlFlags.AGENT_CONTROL_FLY


    def _set_control(self, flag: ControlFlags, active: bool):
        """Helper to set or clear a control flag."""
        if active: self.agent_controls |= flag
        else: self.agent_controls &= ~flag

    async def set_controls(self, controls_to_set: ControlFlags | int, active: bool, send_update_now: bool = True):
        """
        Sets or clears one or more control flags and optionally sends an update.
        Args:
            controls_to_set: The ControlFlags to modify.
            active: True to set the flags, False to clear them.
            send_update_now: If True, an AgentUpdate will be sent immediately.
        """
        if not isinstance(controls_to_set, ControlFlags): # Allow int for raw flags
            controls_to_set = ControlFlags(controls_to_set)

        if active:
            self.agent_controls |= controls_to_set
        else:
            self.agent_controls &= ~controls_to_set

        if send_update_now:
            await self.send_update()

    async def move_forward(self, active: bool, send_update_now: bool = True):
        controls = ControlFlags.AGENT_CONTROL_AT_POS
        if self.always_run: # Note: always_run is a state, not a control flag itself for this action
            controls |= ControlFlags.AGENT_CONTROL_FAST_AT
        await self.set_controls(controls, active, send_update_now)

    async def move_backward(self, active: bool, send_update_now: bool = True):
        controls = ControlFlags.AGENT_CONTROL_AT_NEG
        if self.always_run:
            controls |= ControlFlags.AGENT_CONTROL_FAST_AT
        await self.set_controls(controls, active, send_update_now)

    async def move_left(self, active: bool, send_update_now: bool = True):
        # Assuming FAST_AT also applies to strafing if always_run is on.
        # C# client doesn't have separate FAST_LEFT/RIGHT control flags.
        # Server interprets AT_POS/NEG + LEFT_POS/NEG + FAST_AT for strafe speed.
        controls = ControlFlags.AGENT_CONTROL_LEFT_POS
        if self.always_run:
            controls |= ControlFlags.AGENT_CONTROL_FAST_AT # This might be how running strafe is done
        await self.set_controls(controls, active, send_update_now)

    async def move_right(self, active: bool, send_update_now: bool = True):
        controls = ControlFlags.AGENT_CONTROL_LEFT_NEG
        if self.always_run:
            controls |= ControlFlags.AGENT_CONTROL_FAST_AT
        await self.set_controls(controls, active, send_update_now)

    async def turn_left(self, active: bool, send_update_now: bool = True):
        await self.set_controls(ControlFlags.AGENT_CONTROL_TURN_LEFT, active, send_update_now)

    async def turn_right(self, active: bool, send_update_now: bool = True):
        await self.set_controls(ControlFlags.AGENT_CONTROL_TURN_RIGHT, active, send_update_now)

    async def jump_up(self, active: bool, send_update_now: bool = True):
        # No specific FAST_UP flag, UP_POS is jump/fly up. Fly flag handles speed.
        await self.set_controls(ControlFlags.AGENT_CONTROL_UP_POS, active, send_update_now)

    async def crouch_down(self, active: bool, send_update_now: bool = True):
        await self.set_controls(ControlFlags.AGENT_CONTROL_UP_NEG, active, send_update_now)

    async def set_fly(self, active: bool, send_update_now: bool = True): # Renamed from fly to set_fly for clarity
        # This method controls the FLY *control* flag, which initiates/stops flying.
        # The AgentFlags.FLYING is the *state* flag.
        await self.set_controls(ControlFlags.AGENT_CONTROL_FLY, active, send_update_now)
        if active: self.flags |= AgentFlags.FLYING
        else: self.flags &= ~AgentFlags.FLYING


    async def set_mouselook(self, active: bool, send_update_now: bool = True):
        await self.set_controls(ControlFlags.AGENT_CONTROL_MOUSELOOK, active, send_update_now)
        if active: self.flags |= AgentFlags.MOUSELOOK
        else: self.flags &= ~AgentFlags.MOUSELOOK

    async def stand(self, send_update_now: bool = True): # send_update_now is a bit redundant here due to explicit calls
        logger.debug("AgentMovement: Stand initiated")
        await self.set_controls(ControlFlags.AGENT_CONTROL_SIT_ON_GROUND, False, send_update_now=False) # Clear sit
        await self.set_controls(ControlFlags.AGENT_CONTROL_UNSIT, True, send_update_now=False) # If was sitting on object
        await self.set_controls(ControlFlags.AGENT_CONTROL_STAND_UP, True, send_update_now=True) # Send with STAND_UP

        # STAND_UP is momentary, clear it after sending.
        # The reset_control_flags called by send_update will clear it if auto_reset is on.
        # If auto_reset is off, or to be absolutely sure:
        if not self._auto_reset_controls:
             await self.set_controls(ControlFlags.AGENT_CONTROL_STAND_UP, False, send_update_now=True)
        self.flags &= ~AgentFlags.SITTING


    async def sit_on_ground(self, send_update_now: bool = True):
        logger.debug("AgentMovement: SitOnGround initiated")
        await self.set_controls(ControlFlags.AGENT_CONTROL_SIT_ON_GROUND, True, send_update_now)
        # Server will set AgentFlags.SITTING upon successful sit.
        # We can preemptively set it or wait for confirmation. For now, let server confirm.

    async def rotate_body_by(self, angle_rad: float, send_update_now: bool = True):
        """Rotates the agent's body around the Z-axis."""
        delta_q = Quaternion.from_euler_angles(0.0, 0.0, angle_rad)
        self.body_rotation = delta_q * self.body_rotation
        self.body_rotation = self.body_rotation.normalize() # Keep it normalized

        if not (self.flags & AgentFlags.MOUSELOOK): # If not in mouselook, head follows body
            self.head_rotation = self.body_rotation # Or Quaternion.IDENTITY if head is relative

        if send_update_now:
            await self.send_update()

    async def rotate_head_pitch_by(self, angle_rad: float, send_update_now: bool = True):
        """Pitches the agent's head. Simplified: Assumes mouselook for head rotation relative to body."""
        # This is complex due to gimbal lock and interaction with body_rotation if not in mouselook.
        # In mouselook, head_rotation is often relative to body_rotation or world.
        # For now, a very simplified pitch on local X-axis of head.
        # Assume self.head_rotation is relative to self.body_rotation.
        # If self.head_rotation is world, then it's more complex.
        # Let's assume it's world-oriented for camera purposes, like body_rotation.

        if not (self.flags & AgentFlags.MOUSELOOK):
            logger.warning("rotate_head_pitch_by typically used in mouselook. Head might follow body.")
            # If not in mouselook, head usually aligns with body or has minimal independent pitch.
            # For now, let's allow pitching the body as well, which is not quite right.
            # A better model is needed if head can pitch independently outside mouselook.
            # This will effectively pitch the body and camera together.
            pitch_axis = self.body_rotation.get_conjugate() * Vector3(0,1,0) # Approximate local Y
            delta_q = Quaternion.from_axis_angle(pitch_axis, angle_rad)
            self.body_rotation = delta_q * self.body_rotation
            self.body_rotation = self.body_rotation.normalize()
            self.head_rotation = self.body_rotation # Head follows body
        else:
            # In mouselook, head_rotation is usually independent for pitch.
            # We need to rotate around the head's current local Y (left) axis.
            # Get current head orientation's left vector (local Y)
            # This assumes head_rotation is a world-space quaternion.
            head_left_vector = self.head_rotation.get_conjugate() * Vector3(0,1,0) # Get local Y from quat

            delta_q = Quaternion.from_axis_angle(head_left_vector, angle_rad)
            self.head_rotation = delta_q * self.head_rotation
            self.head_rotation = self.head_rotation.normalize()

        if send_update_now:
            await self.send_update()

    async def set_always_run(self, new_always_run_state: bool, send_update_now: bool = True):
        """Sets the 'always run' state for the agent and sends a SetAlwaysRunPacket."""
        from ..network.packets_agent import SetAlwaysRunPacket # Local import to avoid issues

        self.always_run = new_always_run_state # Update local state for movement methods
        self.flags = (self.flags | AgentFlags.ALWAYS_RUN) if new_always_run_state else (self.flags & ~AgentFlags.ALWAYS_RUN)

        if self.client.network.current_sim and self.client.network.current_sim.handshake_complete:
            packet = SetAlwaysRunPacket(
                agent_id=self.agent_manager.agent_id,
                session_id=self.agent_manager.session_id,
                always_run=new_always_run_state
            )
            packet.header.reliable = True # This should be reliable
            await self.client.network.send_packet(packet, self.client.network.current_sim)
            logger.info(f"Set AlwaysRun to {new_always_run_state} and sent packet.")
        elif send_update_now: # If no sim, but want to reflect in next generic update if one connects
             await self.send_update()
        else:
            logger.warning("SetAlwaysRun: No connected/handshaked sim to send SetAlwaysRunPacket immediately.")


    def _calculate_update_hash(self) -> int:
        """Calculates a hash of the current movement-related state for duplicate checking."""
        # Simple hash: include critical fields that define an update.
        # More fields might be needed for finer-grained duplicate checks.
        state_tuple = (
            self.agent_controls, self.state, self.flags,
            self.camera.position.X, self.camera.position.Y, self.camera.position.Z,
            self.camera.at_axis.X, self.camera.at_axis.Y, self.camera.at_axis.Z,
            self.camera.left_axis.X, self.camera.left_axis.Y, self.camera.left_axis.Z,
            self.camera.up_axis.X, self.camera.up_axis.Y, self.camera.up_axis.Z,
            self.camera.far,
            self.body_rotation.X, self.body_rotation.Y, self.body_rotation.Z, self.body_rotation.W,
            self.head_rotation.X, self.head_rotation.Y, self.head_rotation.Z, self.head_rotation.W,
        )
        return hash(state_tuple)


    async def send_update(self, reliable: bool = False, simulator: Simulator | None = None):
        """Constructs and sends an AgentUpdatePacket based on current state."""
        target_sim = simulator if simulator else self.client.network.current_sim
        if not target_sim or not target_sim.connected or not target_sim.handshake_complete:
            logger.debug("Cannot send AgentUpdate: No connected/handshaked simulator.")
            return

        # Check if agent is considered "in" the sim (e.g. after CompleteAgentMovement)
        # This flag would be set by AgentManager after server confirms agent is in world.
        # For now, handshake_complete is a proxy.
        # if not target_sim.agent_is_in_world: # Hypothetical flag
        #    logger.debug("Agent not fully in world yet, skipping AgentUpdate.")
        #    return

        current_hash = self._calculate_update_hash()
        if current_hash == self._last_update_hash and \
           not self.client.settings.disable_agent_update_duplicate_check:
            # logger.debug("AgentUpdate skipped, state unchanged (hash).")
            # If controls were momentary and auto-reset is on, still reset them
            if self._auto_reset_controls: self.reset_control_flags()
            return

        self._last_update_hash = current_hash

        update_packet = AgentUpdatePacket(
            agent_id=self.agent_manager.agent_id,
            session_id=self.agent_manager.session_id,
            body_rotation=self.body_rotation,
            head_rotation=self.head_rotation, # Relative to body
            camera_center=self.camera.position,
            camera_at_axis=self.camera.at_axis,
            camera_left_axis=self.camera.left_axis,
            camera_up_axis=self.camera.up_axis,
            far=self.camera.far,
            control_flags=self.agent_controls,
            agent_flags=self.flags, # Contains Flying, Mouselook, etc.
            state=self.state # Animation state
        )
        update_packet.header.reliable = reliable # AgentUpdates are usually unreliable

        await self.client.network.send_packet(update_packet, target_sim)
        # logger.debug(f"Sent AgentUpdate: Controls={self.agent_controls}, State={self.state}")

        if self._auto_reset_controls:
            self.reset_control_flags()

    def reset_control_flags(self):
        """Resets momentary control flags, preserving persistent ones."""
        persistent_set = self.agent_controls & self._persistent_controls
        self.agent_controls = ControlFlags.NONE | persistent_set
        # logger.debug(f"Controls reset. Current: {self.agent_controls}")

    async def _update_loop(self):
        """Periodically sends agent updates."""
        interval = self.client.settings.default_agent_update_interval / 1000.0
        if interval <= 0: interval = DEFAULT_UPDATE_INTERVAL # Fallback

        logger.info(f"Agent update loop started with interval: {interval:.2f}s")
        try:
            while True:
                if self.client.network.connected and self.client.network.current_sim and \
                   self.client.network.current_sim.handshake_complete:
                    await self.send_update(reliable=False)
                else:
                    logger.debug("Update loop: No connected/handshaked sim, skipping update.")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Agent update loop cancelled.")
        except Exception as e:
            logger.exception(f"Error in agent update loop: {e}")
        finally:
            logger.info("Agent update loop stopped.")


    async def start_periodic_updates(self):
        """Starts the periodic agent update task if enabled in settings."""
        if self.client.settings.send_agent_updates and \
           self.client.settings.send_agent_updates_regularly:
            if not self._update_timer_task or self._update_timer_task.done():
                self._update_timer_task = asyncio.create_task(self._update_loop())
                logger.info("Periodic agent updates started.")
            else:
                logger.debug("Periodic agent updates task already running.")
        else:
            logger.info("Periodic agent updates not enabled in settings.")

    async def stop_periodic_updates(self):
        """Stops the periodic agent update task."""
        if self._update_timer_task and not self._update_timer_task.done():
            self._update_timer_task.cancel()
            try:
                await self._update_timer_task
            except asyncio.CancelledError:
                pass # Expected
            logger.info("Periodic agent updates stopped.")
        self._update_timer_task = None

    # --- Placeholder methods for movement actions ---
    def turn_to(self, heading_rads: float): # Simplified, just camera for now
        """Turns the agent to a specific heading by rotating camera and body."""
        # This needs to update self.body_rotation and potentially self.head_rotation
        # For mouselook, only camera might update, body follows or is independent.
        # For non-mouselook, body_rotation should align with camera.
        # For now, just update camera.
        self.camera.look_direction(heading_rads)
        # TODO: Set body_rotation from heading_rads
        # self.body_rotation = Quaternion.from_euler_angles(0,0,heading_rads)
        logger.debug(f"TurnTo: Heading={math.degrees(heading_rads):.1f} (Camera only for now)")

    def stand(self):
        """Makes the agent stand up."""
        self.agent_controls |= ControlFlags.AGENT_CONTROL_STAND_UP
        self.flags &= ~AgentFlags.SITTING # Clear sitting flag
        self.state = AgentState.NONE # Or an appropriate standing animation state
        # send_update will pick this up.
        logger.info("Action: Stand")

    # ... other actions like sit_on_ground(), jump(), etc.
    # These would set appropriate ControlFlags and AgentState.
    # Example:
    # def move_forward_start(self): self.forward = True
    # def move_forward_stop(self): self.forward = False
    # ... etc. for all controls
    # def toggle_fly(self): self.fly = not self.fly
