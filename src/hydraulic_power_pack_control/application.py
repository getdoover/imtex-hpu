import logging
import time
from collections import deque

from pydoover.docker import Application
from pydoover import ui

from .app_config import ImtexHPUConfig
from .app_ui import ImtexHPUUI
from .app_state import (
    ImtexHPUState,
    State,
    ALARM_CLEARABLE_STATES,
    WARNING_CLEARABLE_STATES,
)
from .outputs import AVAILABLE_OUTPUTS

log = logging.getLogger(__name__)


class ImtexHPUApplication(Application):
    """Imtex HPU Controller Application.

    Controls hydraulic power unit actuation with 4x 4-20mA sensor inputs
    (via companion sensor apps), pressure band control, redundant pump
    logic, and alarm management.

    Main loop follows strict 6-step sequence:
    1. Read sensor values from companion app tags
    2. Calculate dP/dt from rolling buffer
    3. Run state machine (evaluate + spin)
    4. Update all output modules (DOs)
    5. Update UI with live values and alarm states
    6. Publish tags for inter-app communication
    """

    config: ImtexHPUConfig  # Type hint for IDE autocomplete

    loop_target_period = 1  # 1 Hz control loop

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_inst: ImtexHPUUI = None
        self.state: ImtexHPUState = None
        self.outputs: list = []

        # Sensor values (read from companion app tags)
        self.pt1_pressure: float = None
        self.pt2_pressure: float = None
        self.pressure: float = None  # Active pressure (PT1 preferred, PT2 fallback)
        self.temperature: float = None
        self.filter_dp: float = None

        # Calculated values
        self.dp_dt_value: float = None
        self.pressure_buffer: deque = None
        self.vfd_speed: float = None

        # PT1 enable state (toggled via DI)
        self.pt1_enabled: bool = True

        # Alert deduplication
        self.active_alerts: set = set()

        # Previous state for change detection
        self._previous_state: str = None

    async def setup(self):
        """Initialize UI, state machine, outputs, and DI listeners."""
        # Initialize state machine
        self.state = ImtexHPUState(app=self)

        # Initialize UI
        self.ui_inst = ImtexHPUUI(self.config)
        self.ui_manager.add_children(*self.ui_inst.fetch())

        # Initialize pressure buffer for dP/dt
        buffer_size = self.config.dp_dt_buffer_size.value
        self.pressure_buffer = deque(maxlen=buffer_size)

        # Initialize output modules
        self.outputs = []
        for output_cls in AVAILABLE_OUTPUTS:
            try:
                output = output_cls(self)
                self.outputs.append(output)
                log.info(f"Initialized output: {output.name}")
            except Exception as e:
                log.warning(f"Failed to initialize output {output_cls.name}: {e}")

        # Register DI pulse listeners for physical buttons
        await self._register_di_listeners()

        log.info("HPU Controller setup complete")

    async def _register_di_listeners(self):
        """Register digital input pulse listeners for physical buttons."""
        try:
            self.platform_iface.start_di_pulse_listener(
                self.config.enable_button_pin.value,
                self._on_enable_button,
                "rising",
            )
            self.platform_iface.start_di_pulse_listener(
                self.config.disable_button_pin.value,
                self._on_disable_button,
                "rising",
            )
            self.platform_iface.start_di_pulse_listener(
                self.config.master_reset_pin.value,
                self._on_master_reset,
                "rising",
            )
            self.platform_iface.start_di_pulse_listener(
                self.config.pump1_reset_pin.value,
                self._on_pump1_reset,
                "rising",
            )
            self.platform_iface.start_di_pulse_listener(
                self.config.pump2_reset_pin.value,
                self._on_pump2_reset,
                "rising",
            )
            self.platform_iface.start_di_pulse_listener(
                self.config.pt1_enable_pin.value,
                self._on_pt1_enable_toggle,
                "rising",
            )
            log.info("DI pulse listeners registered")
        except Exception as e:
            log.warning(f"Failed to register DI listeners: {e}")

    # --- DI Button Callbacks ---

    async def _on_enable_button(self, di, val, dt_secs, counter, edge):
        """Handle enable button press."""
        if await self.platform_iface.get_di_async(di):
            log.info("Enable button pressed (DI)")
            self.ui_inst.command.coerce("enabled")

    async def _on_disable_button(self, di, val, dt_secs, counter, edge):
        """Handle disable button press."""
        if await self.platform_iface.get_di_async(di):
            log.info("Disable button pressed (DI)")
            self.ui_inst.command.coerce("disabled")

    async def _on_master_reset(self, di, val, dt_secs, counter, edge):
        """Handle master alarm reset button press."""
        if await self.platform_iface.get_di_async(di):
            log.info("Master reset button pressed (DI)")
            current = self.state.get_state_enum()
            if current in [State(s.value) for s in ALARM_CLEARABLE_STATES]:
                await self.state.clear_alarm()
                self.active_alerts.clear()
            elif current in [State(s.value) for s in WARNING_CLEARABLE_STATES]:
                await self.state.clear_warning()

    async def _on_pump1_reset(self, di, val, dt_secs, counter, edge):
        """Handle pump 1 fault reset button press."""
        if await self.platform_iface.get_di_async(di):
            log.info("Pump 1 reset button pressed (DI)")
            if self.state.get_state_enum() == State.PUMP1_FAULT:
                await self.state.pump1_reset()

    async def _on_pump2_reset(self, di, val, dt_secs, counter, edge):
        """Handle pump 2 fault reset button press."""
        if await self.platform_iface.get_di_async(di):
            log.info("Pump 2 reset button pressed (DI)")
            if self.state.get_state_enum() == State.PUMP2_FAULT:
                await self.state.pump2_reset()

    async def _on_pt1_enable_toggle(self, di, val, dt_secs, counter, edge):
        """Handle PT1 enable/disable toggle button press."""
        if await self.platform_iface.get_di_async(di):
            self.pt1_enabled = not self.pt1_enabled
            log.info(f"PT1 {'enabled' if self.pt1_enabled else 'disabled'} (DI)")

    # --- UI Callbacks ---

    @ui.callback("command")
    async def on_command(self, new_value):
        """Handle HPU enable/disable command from UI."""
        log.info(f"HPU command received: {new_value}")
        if new_value == "enabled":
            if self.state.get_state_enum() == State.DISABLED:
                await self.state.enable()
        elif new_value == "disabled":
            await self.state.disable()

    @ui.callback("clear_alarm")
    async def on_clear_alarm(self, new_value):
        """Handle clear alarm action from UI."""
        log.info("Clear alarm requested (UI)")
        current = self.state.get_state_enum()
        if current in ALARM_CLEARABLE_STATES:
            await self.state.clear_alarm()
            self.active_alerts.clear()
        self.ui_inst.clear_alarm.coerce(None)

    @ui.callback("clear_warning")
    async def on_clear_warning(self, new_value):
        """Handle clear warning action from UI."""
        log.info("Clear warning requested (UI)")
        current = self.state.get_state_enum()
        if current in WARNING_CLEARABLE_STATES:
            await self.state.clear_warning()
        self.ui_inst.clear_warning.coerce(None)

    @ui.callback("reset_pump1")
    async def on_reset_pump1(self, new_value):
        """Handle pump 1 reset action from UI."""
        log.info("Pump 1 reset requested (UI)")
        if self.state.get_state_enum() == State.PUMP1_FAULT:
            await self.state.pump1_reset()
        self.ui_inst.reset_pump1.coerce(None)

    @ui.callback("reset_pump2")
    async def on_reset_pump2(self, new_value):
        """Handle pump 2 reset action from UI."""
        log.info("Pump 2 reset requested (UI)")
        if self.state.get_state_enum() == State.PUMP2_FAULT:
            await self.state.pump2_reset()
        self.ui_inst.reset_pump2.coerce(None)

    @ui.callback("pressure_upper_band")
    async def on_pressure_upper_band(self, new_value):
        """Handle pressure upper band slider change from UI."""
        if new_value is not None:
            log.info(f"Pressure upper band changed to: {new_value}")

    @ui.callback("pressure_lower_band")
    async def on_pressure_lower_band(self, new_value):
        """Handle pressure lower band slider change from UI."""
        if new_value is not None:
            log.info(f"Pressure lower band changed to: {new_value}")

    @ui.callback("pressure_high_alarm_setting")
    async def on_pressure_high_alarm_setting(self, new_value):
        """Handle pressure high alarm slider change from UI."""
        if new_value is not None:
            log.info(f"Pressure high alarm threshold changed to: {new_value}")

    @ui.callback("dp_dt_alarm_setting")
    async def on_dp_dt_alarm_setting(self, new_value):
        """Handle dP/dt alarm slider change from UI."""
        if new_value is not None:
            log.info(f"dP/dt alarm threshold changed to: {new_value}")

    @ui.callback("filter_dp_warning_setting")
    async def on_filter_dp_warning_setting(self, new_value):
        """Handle filter DP warning slider change from UI."""
        if new_value is not None:
            log.info(f"Filter DP warning changed to: {new_value}")

    @ui.callback("filter_dp_fail_setting")
    async def on_filter_dp_fail_setting(self, new_value):
        """Handle filter DP fail slider change from UI."""
        if new_value is not None:
            log.info(f"Filter DP fail changed to: {new_value}")

    @ui.callback("temp_high_warning_setting")
    async def on_temp_high_warning_setting(self, new_value):
        """Handle temperature high warning slider change from UI."""
        if new_value is not None:
            log.info(f"Temp high warning changed to: {new_value}")

    @ui.callback("temp_high_alarm_setting")
    async def on_temp_high_alarm_setting(self, new_value):
        """Handle temperature high alarm slider change from UI."""
        if new_value is not None:
            log.info(f"Temp high alarm changed to: {new_value}")

    # --- Main Loop ---

    async def main_loop(self):
        """Main control loop: 6-step sequence executed at 1 Hz."""
        try:
            # Step 1: Read sensor values from companion app tags
            self._read_sensors()

            # Step 2: Calculate dP/dt from rolling buffer
            self._calculate_dp_dt()

            # Step 3: Run state machine (evaluate + spin until stable)
            current_state = await self.state.spin_state()

            # Check for state change and send alerts
            if current_state != self._previous_state:
                await self._on_state_change(current_state)
                self._previous_state = current_state

            # Step 4: Update all output modules (DOs)
            for output in self.outputs:
                try:
                    await output.update()
                except Exception as e:
                    log.error(f"Failed to update output {output.name}: {e}")

            # Step 5: Update UI
            self._update_ui()

            # Step 6: Publish tags for inter-app communication
            await self._update_tags()

        except Exception as e:
            log.exception(f"Error in main loop: {e}")

    # --- Step 1: Read Sensors ---

    def _read_sensors(self):
        """Read sensor values from companion sensor app tags."""
        # Read PT1 pressure
        pt1_app_key = self.config.pt1_app.value
        if pt1_app_key:
            self.pt1_pressure = self.get_tag("value", pt1_app_key)

        # Read PT2 pressure (if configured)
        pt2_app_key = self.config.pt2_app.value
        if pt2_app_key:
            self.pt2_pressure = self.get_tag("value", pt2_app_key)

        # Select active pressure: PT1 preferred, PT2 fallback
        if self.pt1_enabled and self.pt1_pressure is not None:
            self.pressure = self.pt1_pressure
        elif self.pt2_pressure is not None:
            self.pressure = self.pt2_pressure
        else:
            self.pressure = self.pt1_pressure  # May be None

        # Read temperature
        temp_app_key = self.config.temp_app.value
        if temp_app_key:
            self.temperature = self.get_tag("value", temp_app_key)

        # Read filter DP (if configured)
        dp_app_key = self.config.dp_app.value
        if dp_app_key:
            self.filter_dp = self.get_tag("value", dp_app_key)

    # --- Step 2: Calculate dP/dt ---

    def _calculate_dp_dt(self):
        """Calculate rate of pressure change from rolling buffer."""
        if self.pressure is not None:
            self.pressure_buffer.append((time.time(), self.pressure))

        if len(self.pressure_buffer) >= 2:
            t_old, p_old = self.pressure_buffer[0]
            t_new, p_new = self.pressure_buffer[-1]
            dt = t_new - t_old
            if dt > 0:
                self.dp_dt_value = (p_new - p_old) / dt
            else:
                self.dp_dt_value = 0.0
        else:
            self.dp_dt_value = None

    # --- State Change Handler ---

    async def _on_state_change(self, new_state: str):
        """Handle state change: notify outputs and send alerts."""
        log.info(f"State changed: {self._previous_state} -> {new_state}")

        # Notify all output modules
        for output in self.outputs:
            try:
                await output.on_state_change(new_state)
            except Exception as e:
                log.error(f"Output {output.name} state change error: {e}")

        # Send alert notifications for alarm/fault transitions
        new_state_enum = State(new_state)
        alert_messages = {
            State.PRESSURE_HIGH_ALARM: "ALARM: Pressure high alarm triggered",
            State.PRESSURE_LOW_ALARM: "ALARM: Pressure low alarm triggered",
            State.DP_DT_ALARM: "ALARM: Rapid pressure change detected (dP/dt)",
            State.TEMP_HIGH_ALARM: "ALARM: Temperature high alarm triggered",
            State.TEMP_HIGH_WARNING: "WARNING: Temperature high warning",
            State.FILTER_FAIL: "ALARM: Filter DP fail threshold exceeded",
            State.FILTER_WARNING: "WARNING: Filter DP warning threshold exceeded",
            State.PT_CAL_WARNING: "WARNING: PT calibration drift detected",
            State.PUMP1_FAULT: "FAULT: Pump 1 faulted",
            State.PUMP2_FAULT: "FAULT: Pump 2 faulted",
            State.BOTH_PUMPS_FAULT: "ALARM: Both pumps faulted",
            State.MASTER_ALARM: "ALARM: Master alarm active",
        }

        if new_state_enum in alert_messages:
            await self._send_alert_once(
                new_state,
                alert_messages[new_state_enum],
            )

        # Clear alerts when returning to normal states
        if new_state_enum in [State.IDLE, State.DISABLED]:
            self.active_alerts.clear()

    async def _send_alert_once(self, alert_id: str, message: str):
        """Send alert only once until cleared (deduplication)."""
        if alert_id in self.active_alerts:
            return
        try:
            await self.ui_inst.notifications.send_alert(message)
            self.active_alerts.add(alert_id)
        except Exception as e:
            log.warning(f"Failed to send alert: {e}")

    # --- Step 5: Update UI ---

    def _update_ui(self):
        """Update all UI elements with current values."""
        current = self.state.get_state_enum()

        alarms = {
            "pressure_high": current == State.PRESSURE_HIGH_ALARM,
            "pressure_low": current == State.PRESSURE_LOW_ALARM,
            "dp_dt": current == State.DP_DT_ALARM,
            "temp_warning": current == State.TEMP_HIGH_WARNING,
            "temp_alarm": current == State.TEMP_HIGH_ALARM,
            "filter_warning": current == State.FILTER_WARNING,
            "filter_fail": current == State.FILTER_FAIL,
            "pt_cal_drift": current == State.PT_CAL_WARNING,
            "pump1_fault": current in [State.PUMP1_FAULT, State.BOTH_PUMPS_FAULT],
            "pump2_fault": current in [State.PUMP2_FAULT, State.BOTH_PUMPS_FAULT],
            "master": current == State.MASTER_ALARM,
        }

        self.ui_inst.update(
            state=self.state.state,
            pressure=self.pressure,
            temperature=self.temperature,
            filter_dp=self.filter_dp,
            dp_dt=self.dp_dt_value,
            active_pump=self.state.active_pump,
            pump1_running=self.state.should_pump_run(1),
            pump2_running=self.state.should_pump_run(2),
            vfd_speed=self.vfd_speed,
            alarms=alarms,
        )

    # --- Step 6: Update Tags ---

    async def _update_tags(self):
        """Publish tags for inter-app communication."""
        tags = {
            "State": self.state.state,
            "Pressure": self.pressure,
            "Temperature": self.temperature,
            "FilterDP": self.filter_dp,
            "dPdt": self.dp_dt_value,
            "ActivePump": self.state.active_pump,
            "Pump1Running": self.state.should_pump_run(1),
            "Pump2Running": self.state.should_pump_run(2),
        }

        await self.set_tags_async(tags)
