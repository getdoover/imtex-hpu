import enum
import logging
import time

from pydoover.state import StateMachine

log = logging.getLogger(__name__)


class State(enum.Enum):
    DISABLED = "disabled"
    IDLE = "idle"
    PRESSURISING = "pressurising"
    PRESSURE_OK = "pressure_ok"
    PUMP1_FAULT = "pump1_fault"
    PUMP2_FAULT = "pump2_fault"
    BOTH_PUMPS_FAULT = "both_pumps_fault"
    PT_CAL_WARNING = "pt_cal_warning"
    FILTER_WARNING = "filter_warning"
    FILTER_FAIL = "filter_fail"
    TEMP_HIGH_WARNING = "temp_high_warning"
    TEMP_HIGH_ALARM = "temp_high_alarm"
    PRESSURE_HIGH_ALARM = "pressure_high_alarm"
    PRESSURE_LOW_ALARM = "pressure_low_alarm"
    DP_DT_ALARM = "dp_dt_alarm"
    MASTER_ALARM = "master_alarm"


# States where the system is operational (pumping possible)
OPERATIONAL_STATES = [
    State.IDLE,
    State.PRESSURISING,
    State.PRESSURE_OK,
]

# Warning states (non-critical, system can continue)
WARNING_STATES = [
    State.PT_CAL_WARNING,
    State.FILTER_WARNING,
    State.TEMP_HIGH_WARNING,
]

# Critical alarm states (system shutdown)
CRITICAL_ALARM_STATES = [
    State.PRESSURE_HIGH_ALARM,
    State.PRESSURE_LOW_ALARM,
    State.DP_DT_ALARM,
    State.TEMP_HIGH_ALARM,
    State.FILTER_FAIL,
    State.BOTH_PUMPS_FAULT,
    State.MASTER_ALARM,
]

# Fault states
FAULT_STATES = [
    State.PUMP1_FAULT,
    State.PUMP2_FAULT,
    State.BOTH_PUMPS_FAULT,
]

# All alarm/fault states requiring manual clear
ALARM_CLEARABLE_STATES = [
    State.PRESSURE_HIGH_ALARM,
    State.PRESSURE_LOW_ALARM,
    State.DP_DT_ALARM,
    State.TEMP_HIGH_ALARM,
    State.FILTER_FAIL,
    State.BOTH_PUMPS_FAULT,
    State.MASTER_ALARM,
]

WARNING_CLEARABLE_STATES = [
    State.PT_CAL_WARNING,
    State.FILTER_WARNING,
    State.TEMP_HIGH_WARNING,
]


class ImtexHPUState:
    """HPU Controller state machine with 16 states."""

    state: str  # Current state value (set by StateMachine)

    states = [
        {"name": State.DISABLED.value},
        {"name": State.IDLE.value},
        {"name": State.PRESSURISING.value},
        {"name": State.PRESSURE_OK.value},
        {"name": State.PUMP1_FAULT.value},
        {"name": State.PUMP2_FAULT.value},
        {"name": State.BOTH_PUMPS_FAULT.value},
        {"name": State.PT_CAL_WARNING.value},
        {"name": State.FILTER_WARNING.value},
        {"name": State.FILTER_FAIL.value},
        {"name": State.TEMP_HIGH_WARNING.value},
        {"name": State.TEMP_HIGH_ALARM.value},
        {"name": State.PRESSURE_HIGH_ALARM.value},
        {"name": State.PRESSURE_LOW_ALARM.value},
        {"name": State.DP_DT_ALARM.value},
        {"name": State.MASTER_ALARM.value},
    ]

    transitions = [
        # Enable / Disable
        {"trigger": "enable", "source": State.DISABLED.value, "dest": State.IDLE.value},
        {"trigger": "disable", "source": "*", "dest": State.DISABLED.value},

        # Pressure band control
        {"trigger": "pressure_low", "source": [State.IDLE.value, State.PRESSURE_OK.value], "dest": State.PRESSURISING.value},
        {"trigger": "pressure_ok", "source": State.PRESSURISING.value, "dest": State.PRESSURE_OK.value},

        # Pump faults (from operational states)
        {"trigger": "pump1_fault", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value], "dest": State.PUMP1_FAULT.value},
        {"trigger": "pump2_fault", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value, State.PUMP1_FAULT.value], "dest": State.PUMP2_FAULT.value},
        {"trigger": "both_pumps_fault", "source": [State.PUMP1_FAULT.value, State.PUMP2_FAULT.value], "dest": State.BOTH_PUMPS_FAULT.value},

        # Pump fault resets -> back to IDLE
        {"trigger": "pump1_reset", "source": State.PUMP1_FAULT.value, "dest": State.IDLE.value},
        {"trigger": "pump2_reset", "source": State.PUMP2_FAULT.value, "dest": State.IDLE.value},

        # Critical alarms (from any state via "*")
        {"trigger": "pressure_high_alarm", "source": "*", "dest": State.PRESSURE_HIGH_ALARM.value},
        {"trigger": "pressure_low_alarm", "source": "*", "dest": State.PRESSURE_LOW_ALARM.value},
        {"trigger": "dp_dt_alarm", "source": "*", "dest": State.DP_DT_ALARM.value},
        {"trigger": "temp_high_alarm", "source": "*", "dest": State.TEMP_HIGH_ALARM.value},
        {"trigger": "filter_fail", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value], "dest": State.FILTER_FAIL.value},

        # Warning states (from operational states only)
        {"trigger": "pt_cal_warning", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value], "dest": State.PT_CAL_WARNING.value},
        {"trigger": "filter_warning", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value], "dest": State.FILTER_WARNING.value},
        {"trigger": "temp_high_warning", "source": [State.IDLE.value, State.PRESSURISING.value, State.PRESSURE_OK.value], "dest": State.TEMP_HIGH_WARNING.value},

        # Master alarm (from critical alarm states)
        {"trigger": "master_alarm", "source": [
            State.PRESSURE_HIGH_ALARM.value,
            State.PRESSURE_LOW_ALARM.value,
            State.DP_DT_ALARM.value,
            State.TEMP_HIGH_ALARM.value,
            State.FILTER_FAIL.value,
            State.BOTH_PUMPS_FAULT.value,
        ], "dest": State.MASTER_ALARM.value},

        # Clear alarm -> IDLE (from alarm states)
        {"trigger": "clear_alarm", "source": [
            State.PRESSURE_HIGH_ALARM.value,
            State.PRESSURE_LOW_ALARM.value,
            State.DP_DT_ALARM.value,
            State.TEMP_HIGH_ALARM.value,
            State.FILTER_FAIL.value,
            State.BOTH_PUMPS_FAULT.value,
            State.MASTER_ALARM.value,
        ], "dest": State.IDLE.value},

        # Clear warning -> IDLE (from warning states)
        {"trigger": "clear_warning", "source": [
            State.PT_CAL_WARNING.value,
            State.FILTER_WARNING.value,
            State.TEMP_HIGH_WARNING.value,
        ], "dest": State.IDLE.value},
    ]

    def __init__(self, app=None):
        self.app = app
        self._pump1_faulted = False
        self._pump2_faulted = False
        self._switchover_timer = None

        self.state_machine = StateMachine(
            states=self.states,
            transitions=self.transitions,
            model=self,
            initial=State.DISABLED.value,
            queued=True,
        )

    def get_state_enum(self) -> State:
        """Return current state as a State enum member."""
        return State(self.state)

    @property
    def active_pump(self) -> int:
        """Return which pump is currently designated as active (1 or 2)."""
        if self._pump1_faulted and not self._pump2_faulted:
            return 2
        return 1

    def should_pump_run(self, pump_number: int) -> bool:
        """Determine whether a given pump should be running."""
        current = self.get_state_enum()

        # No pumps run in disabled or critical alarm states
        if current == State.DISABLED:
            return False
        if current in CRITICAL_ALARM_STATES:
            return False

        # Only run pump during PRESSURISING (or PUMP1_FAULT/PUMP2_FAULT with backup)
        should_be_pumping = current in [State.PRESSURISING, State.PUMP1_FAULT, State.PUMP2_FAULT]

        if not should_be_pumping:
            return False

        if pump_number == 1:
            if self._pump1_faulted:
                return False
            return self.active_pump == 1
        elif pump_number == 2:
            if self._pump2_faulted:
                return False
            if not self.app or not self.app.config.enable_pump_2.value:
                return False
            return self.active_pump == 2
        return False

    async def evaluate_state(self):
        """Evaluate current inputs and trigger appropriate state transitions."""
        current = self.get_state_enum()
        app = self.app

        if app is None:
            return

        # --- Critical alarm checks (from any state except DISABLED) ---
        if current != State.DISABLED:
            # Pressure high alarm
            if app.pressure is not None and app.pressure > app.config.pressure_high_alarm.value:
                if current != State.PRESSURE_HIGH_ALARM and current != State.MASTER_ALARM:
                    await self.pressure_high_alarm()
                    return

            # Pressure low alarm (only when enabled and pressurised)
            if current in OPERATIONAL_STATES and current != State.IDLE:
                if app.pressure is not None and app.pressure < app.config.pressure_low_alarm.value:
                    if current != State.PRESSURE_LOW_ALARM:
                        await self.pressure_low_alarm()
                        return

            # dP/dt alarm
            if app.dp_dt_value is not None and abs(app.dp_dt_value) > app.config.dp_dt_alarm_threshold.value:
                if current != State.DP_DT_ALARM and current != State.MASTER_ALARM:
                    await self.dp_dt_alarm()
                    return

            # Temperature high alarm
            if app.temperature is not None and app.temperature > app.config.temp_high_alarm.value:
                if current != State.TEMP_HIGH_ALARM and current != State.MASTER_ALARM:
                    await self.temp_high_alarm()
                    return

        # --- State-specific behavior ---
        if current == State.DISABLED:
            # Nothing to do in disabled state
            pass

        elif current == State.IDLE:
            # Check if pressure has dropped below lower band
            if app.pressure is not None and app.pressure < app.config.pressure_lower_band.value:
                await self.pressure_low()
                return

            # Check warning conditions
            await self._check_warnings()

        elif current == State.PRESSURISING:
            # Check if pressure has reached upper band
            if app.pressure is not None and app.pressure >= app.config.pressure_upper_band.value:
                await self.pressure_ok()
                return

            # Check warning conditions
            await self._check_warnings()

        elif current == State.PRESSURE_OK:
            # Check if pressure has dropped below lower band
            if app.pressure is not None and app.pressure < app.config.pressure_lower_band.value:
                await self.pressure_low()
                return

            # Check warning conditions
            await self._check_warnings()

        elif current == State.PUMP1_FAULT:
            # Auto-switchover to pump 2 if available
            if app.config.enable_pump_2.value and not self._pump2_faulted:
                if self._switchover_timer is None:
                    self._switchover_timer = time.time()
                elif time.time() - self._switchover_timer >= app.config.pump_switchover_delay.value:
                    self._switchover_timer = None
                    # Pump 2 takes over - transition back to pressurising/idle
                    # depending on pressure
                    log.info("Auto-switchover to Pump 2")
            elif self._pump2_faulted:
                await self.both_pumps_fault()
                return

        elif current == State.PUMP2_FAULT:
            if self._pump1_faulted:
                await self.both_pumps_fault()
                return

        elif current in CRITICAL_ALARM_STATES and current != State.MASTER_ALARM:
            # Critical alarm states can cascade to master alarm
            await self.master_alarm()
            return

    async def _check_warnings(self):
        """Check warning conditions (only called from operational states)."""
        app = self.app
        if app is None:
            return

        # Filter DP fail (critical - check first)
        if app.filter_dp is not None and app.filter_dp > app.config.filter_dp_fail.value:
            await self.filter_fail()
            return

        # Temperature high warning
        if app.temperature is not None and app.temperature > app.config.temp_high_warning.value:
            if app.temperature <= app.config.temp_high_alarm.value:
                await self.temp_high_warning()
                return

        # Filter DP warning
        if app.filter_dp is not None and app.filter_dp > app.config.filter_dp_warning.value:
            if app.filter_dp <= app.config.filter_dp_fail.value:
                await self.filter_warning()
                return

        # PT calibration drift warning
        if (app.pt1_pressure is not None and app.pt2_pressure is not None
                and app.config.enable_pump_2.value):
            drift = abs(app.pt1_pressure - app.pt2_pressure)
            if drift > app.config.pt_cal_drift_threshold.value:
                await self.pt_cal_warning()
                return

    async def spin_state(self, max_iterations: int = 15) -> str:
        """Repeatedly evaluate state until it stabilizes."""
        for _ in range(max_iterations):
            old_state = self.state
            await self.evaluate_state()
            if self.state == old_state:
                break
        return self.state

    # --- State enter/exit callbacks ---

    async def on_enter_disabled(self):
        log.info("State -> DISABLED: All outputs off")
        self._switchover_timer = None

    async def on_enter_idle(self):
        log.info("State -> IDLE: System enabled, pressure within band")
        self._switchover_timer = None

    async def on_enter_pressurising(self):
        log.info("State -> PRESSURISING: Pump running to build pressure")

    async def on_enter_pressure_ok(self):
        log.info("State -> PRESSURE_OK: Pressure within upper band")

    async def on_enter_pump1_fault(self):
        log.warning("State -> PUMP1_FAULT: Pump 1 faulted")
        self._pump1_faulted = True
        self._switchover_timer = None

    async def on_enter_pump2_fault(self):
        log.warning("State -> PUMP2_FAULT: Pump 2 faulted")
        self._pump2_faulted = True

    async def on_enter_both_pumps_fault(self):
        log.error("State -> BOTH_PUMPS_FAULT: Both pumps faulted, master alarm")

    async def on_enter_pt_cal_warning(self):
        log.warning("State -> PT_CAL_WARNING: PT1/PT2 calibration drift detected")

    async def on_enter_filter_warning(self):
        log.warning("State -> FILTER_WARNING: Filter DP above warning threshold")

    async def on_enter_filter_fail(self):
        log.error("State -> FILTER_FAIL: Filter DP above fail threshold")

    async def on_enter_temp_high_warning(self):
        log.warning("State -> TEMP_HIGH_WARNING: Temperature above warning threshold")

    async def on_enter_temp_high_alarm(self):
        log.error("State -> TEMP_HIGH_ALARM: Temperature above alarm threshold")

    async def on_enter_pressure_high_alarm(self):
        log.error("State -> PRESSURE_HIGH_ALARM: Pressure above high alarm threshold")

    async def on_enter_pressure_low_alarm(self):
        log.error("State -> PRESSURE_LOW_ALARM: Pressure below low alarm threshold")

    async def on_enter_dp_dt_alarm(self):
        log.error("State -> DP_DT_ALARM: Rapid pressure change detected")

    async def on_enter_master_alarm(self):
        log.error("State -> MASTER_ALARM: Critical alarm active")

    async def on_exit_pump1_fault(self):
        """Clear pump 1 fault flag on exit."""
        self._pump1_faulted = False
        self._switchover_timer = None

    async def on_exit_pump2_fault(self):
        """Clear pump 2 fault flag on exit."""
        self._pump2_faulted = False

    # Type hints for trigger methods (generated by StateMachine)
    async def enable(self): ...
    async def disable(self): ...
    async def pressure_low(self): ...
    async def pressure_ok(self): ...
    async def pump1_fault(self): ...
    async def pump2_fault(self): ...
    async def both_pumps_fault(self): ...
    async def pump1_reset(self): ...
    async def pump2_reset(self): ...
    async def pressure_high_alarm(self): ...
    async def pressure_low_alarm(self): ...
    async def dp_dt_alarm(self): ...
    async def temp_high_alarm(self): ...
    async def filter_fail(self): ...
    async def pt_cal_warning(self): ...
    async def filter_warning(self): ...
    async def temp_high_warning(self): ...
    async def master_alarm(self): ...
    async def clear_alarm(self): ...
    async def clear_warning(self): ...
