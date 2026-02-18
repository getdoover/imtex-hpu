from pydoover import ui

from .app_config import ImtexHPUConfig
from .app_state import State


def _safe_value(config_element, fallback):
    """Safely get a config element's value, returning fallback if not set."""
    try:
        return config_element.value
    except (ValueError, AttributeError):
        return fallback


class ImtexHPUUI:
    """UI definition for the Imtex HPU Controller.

    Includes live sensor displays, pump status, alarm indicators,
    adjustable parameters, and control actions.
    """

    def __init__(self, config: ImtexHPUConfig):
        self.config = config

        # --- Actions / Commands ---
        self.command = ui.StateCommand(
            "command",
            "HPU Command",
            user_options=[
                ui.Option("disabled", "Disabled"),
                ui.Option("enabled", "Enabled"),
            ],
        )

        self.clear_alarm = ui.Action(
            "clear_alarm",
            "Clear Alarm",
            colour=ui.Colour.red,
            requires_confirm=True,
        )
        self.clear_warning = ui.Action(
            "clear_warning",
            "Clear Warning",
        )
        self.reset_pump1 = ui.Action(
            "reset_pump1",
            "Reset Pump 1",
            requires_confirm=True,
        )
        self.reset_pump2 = ui.Action(
            "reset_pump2",
            "Reset Pump 2",
            requires_confirm=True,
        )

        # --- Variables (Display) ---
        self.system_state = ui.TextVariable("system_state", "System State")
        self.pressure = ui.NumericVariable(
            "pressure",
            "System Pressure (bar)",
            precision=1,
            ranges=[
                ui.Range("Low", 0, 50, ui.Colour.red),
                ui.Range("Normal", 50, 250, ui.Colour.green),
                ui.Range("High", 250, 500, ui.Colour.red),
            ],
        )
        self.active_pump = ui.TextVariable("active_pump", "Active Pump")
        self.pump1_running = ui.BooleanVariable("pump1_running", "Pump 1 Running")
        self.pump2_running = ui.BooleanVariable("pump2_running", "Pump 2 Running")
        self.temperature = ui.NumericVariable(
            "temperature",
            "Temperature",
            precision=1,
        )
        self.filter_dp = ui.NumericVariable(
            "filter_dp",
            "Filter DP (bar)",
            precision=2,
        )
        self.dp_dt = ui.NumericVariable(
            "dp_dt",
            "dP/dt (bar/s)",
            precision=2,
        )
        self.vfd_speed = ui.NumericVariable(
            "vfd_speed",
            "VFD Speed (%)",
            precision=1,
        )

        # --- Alarm Status Submodule ---
        self.alarm_status = ui.Submodule("alarm_status", "Alarm Status")
        self.alarm_pressure_high = ui.BooleanVariable("alarm_pressure_high", "Pressure High Alarm")
        self.alarm_pressure_low = ui.BooleanVariable("alarm_pressure_low", "Pressure Low Alarm")
        self.alarm_dp_dt = ui.BooleanVariable("alarm_dp_dt", "dP/dt Alarm")
        self.alarm_temp_warning = ui.BooleanVariable("alarm_temp_warning", "Temperature High Warning")
        self.alarm_temp_alarm = ui.BooleanVariable("alarm_temp_alarm", "Temperature High Alarm")
        self.alarm_filter_warning = ui.BooleanVariable("alarm_filter_warning", "Filter DP Warning")
        self.alarm_filter_fail = ui.BooleanVariable("alarm_filter_fail", "Filter DP Fail")
        self.alarm_pt_cal_drift = ui.BooleanVariable("alarm_pt_cal_drift", "PT Cal Drift Warning")
        self.alarm_pump1_fault = ui.BooleanVariable("alarm_pump1_fault", "Pump 1 Fault")
        self.alarm_pump2_fault = ui.BooleanVariable("alarm_pump2_fault", "Pump 2 Fault")
        self.alarm_master = ui.BooleanVariable("alarm_master", "Master Alarm")

        self.alarm_status.add_children(
            self.alarm_pressure_high,
            self.alarm_pressure_low,
            self.alarm_dp_dt,
            self.alarm_temp_warning,
            self.alarm_temp_alarm,
            self.alarm_filter_warning,
            self.alarm_filter_fail,
            self.alarm_pt_cal_drift,
            self.alarm_pump1_fault,
            self.alarm_pump2_fault,
            self.alarm_master,
        )

        # --- Alarm Settings Submodule (Parameters) ---
        self.alarm_settings = ui.Submodule("alarm_settings", "Alarm Settings")
        self.pressure_upper_band_setting = ui.Slider(
            "pressure_upper_band",
            "Pressure Upper Band (bar)",
            min_val=0,
            max_val=500,
            step_size=1,
            default=_safe_value(config.pressure_upper_band, 200),
        )
        self.pressure_lower_band_setting = ui.Slider(
            "pressure_lower_band",
            "Pressure Lower Band (bar)",
            min_val=0,
            max_val=500,
            step_size=1,
            default=_safe_value(config.pressure_lower_band, 180),
        )
        self.pressure_high_alarm_setting = ui.Slider(
            "pressure_high_alarm_setting",
            "Pressure High Alarm (bar)",
            min_val=0,
            max_val=500,
            step_size=1,
            default=_safe_value(config.pressure_high_alarm, 250),
        )
        self.dp_dt_alarm_setting = ui.Slider(
            "dp_dt_alarm_setting",
            "dP/dt Alarm Threshold (bar/s)",
            min_val=0,
            max_val=50,
            step_size=0.5,
            default=_safe_value(config.dp_dt_alarm_threshold, 10),
        )
        self.filter_dp_warning_setting = ui.Slider(
            "filter_dp_warning_setting",
            "Filter DP Warning (bar)",
            min_val=0,
            max_val=10,
            step_size=0.1,
            default=_safe_value(config.filter_dp_warning, 2.0),
        )
        self.filter_dp_fail_setting = ui.Slider(
            "filter_dp_fail_setting",
            "Filter DP Fail (bar)",
            min_val=0,
            max_val=10,
            step_size=0.1,
            default=_safe_value(config.filter_dp_fail, 4.0),
        )
        self.temp_high_warning_setting = ui.Slider(
            "temp_high_warning_setting",
            "Temp High Warning",
            min_val=0,
            max_val=150,
            step_size=1,
            default=_safe_value(config.temp_high_warning, 60),
        )
        self.temp_high_alarm_setting = ui.Slider(
            "temp_high_alarm_setting",
            "Temp High Alarm",
            min_val=0,
            max_val=150,
            step_size=1,
            default=_safe_value(config.temp_high_alarm, 80),
        )

        self.alarm_settings.add_children(
            self.pressure_upper_band_setting,
            self.pressure_lower_band_setting,
            self.pressure_high_alarm_setting,
            self.dp_dt_alarm_setting,
            self.filter_dp_warning_setting,
            self.filter_dp_fail_setting,
            self.temp_high_warning_setting,
            self.temp_high_alarm_setting,
        )

        # --- Alert Notifications ---
        self.notifications = ui.AlertStream()

    def fetch(self):
        """Return UI elements for registration, conditionally based on config."""
        elements = [
            self.command,
            self.system_state,
            self.pressure,
            self.active_pump,
            self.pump1_running,
        ]

        # Conditionally include Pump 2 elements
        if _safe_value(self.config.enable_pump_2, True):
            elements.append(self.pump2_running)

        elements.extend([
            self.temperature,
            self.filter_dp,
            self.dp_dt,
        ])

        # Conditionally include VFD speed
        if _safe_value(self.config.enable_vfd, False):
            elements.append(self.vfd_speed)

        elements.extend([
            self.clear_alarm,
            self.clear_warning,
            self.reset_pump1,
        ])

        # Conditionally include Pump 2 reset
        if _safe_value(self.config.enable_pump_2, True):
            elements.append(self.reset_pump2)

        elements.extend([
            self.alarm_status,
            self.alarm_settings,
            self.notifications,
        ])

        return elements

    def update(
        self,
        state: str = None,
        pressure: float = None,
        temperature: float = None,
        filter_dp: float = None,
        dp_dt: float = None,
        active_pump: int = None,
        pump1_running: bool = False,
        pump2_running: bool = False,
        vfd_speed: float = None,
        alarms: dict = None,
    ):
        """Update all UI elements with current values."""
        if state is not None:
            self.system_state.update(state.replace("_", " ").upper())

        if pressure is not None:
            self.pressure.update(pressure)

        if temperature is not None:
            self.temperature.update(temperature)

        if filter_dp is not None:
            self.filter_dp.update(filter_dp)

        if dp_dt is not None:
            self.dp_dt.update(dp_dt)

        if active_pump is not None:
            self.active_pump.update(f"Pump {active_pump}")

        self.pump1_running.update(pump1_running)
        self.pump2_running.update(pump2_running)

        if vfd_speed is not None:
            self.vfd_speed.update(vfd_speed)

        # Update alarm indicators
        if alarms:
            self.alarm_pressure_high.update(alarms.get("pressure_high", False))
            self.alarm_pressure_low.update(alarms.get("pressure_low", False))
            self.alarm_dp_dt.update(alarms.get("dp_dt", False))
            self.alarm_temp_warning.update(alarms.get("temp_warning", False))
            self.alarm_temp_alarm.update(alarms.get("temp_alarm", False))
            self.alarm_filter_warning.update(alarms.get("filter_warning", False))
            self.alarm_filter_fail.update(alarms.get("filter_fail", False))
            self.alarm_pt_cal_drift.update(alarms.get("pt_cal_drift", False))
            self.alarm_pump1_fault.update(alarms.get("pump1_fault", False))
            self.alarm_pump2_fault.update(alarms.get("pump2_fault", False))
            self.alarm_master.update(alarms.get("master", False))
