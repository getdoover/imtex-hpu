from pathlib import Path

from pydoover import config


class ImtexHPUConfig(config.Schema):
    def __init__(self):
        # --- Variant Flags ---
        self.enable_pump_2 = config.Boolean(
            "Enable Pump 2 (Redundant)",
            description="Enable redundant Pump 2 with automatic failover",
            default=True,
        )
        self.enable_vfd = config.Boolean(
            "Enable VFD Speed Control",
            description="Enable VFD speed control for motor modulation",
            default=False,
        )

        # --- Pressure Band Control ---
        self.pressure_upper_band = config.Number(
            "Pressure Upper Band (bar)",
            description="Upper pressure threshold (bar) to stop pumping. Range 0-500.",
            default=200.0,
            minimum=0.0,
            maximum=500.0,
        )
        self.pressure_lower_band = config.Number(
            "Pressure Lower Band (bar)",
            description="Lower pressure threshold (bar) to start pumping. Range 0-500.",
            default=180.0,
            minimum=0.0,
            maximum=500.0,
        )

        # --- Alarm Thresholds ---
        self.pressure_high_alarm = config.Number(
            "Pressure High Alarm (bar)",
            description="Pressure high alarm threshold (bar). Critical alarm.",
            default=250.0,
        )
        self.pressure_low_alarm = config.Number(
            "Pressure Low Alarm (bar)",
            description="Pressure low alarm threshold (bar). Critical alarm.",
            default=50.0,
        )
        self.dp_dt_alarm_threshold = config.Number(
            "dP/dt Alarm Threshold (bar/s)",
            description="Rate of pressure change alarm threshold (bar/s). Critical alarm.",
            default=10.0,
        )
        self.dp_dt_buffer_size = config.Integer(
            "dP/dt Buffer Size",
            description="Number of samples in dP/dt rolling buffer. Range 3-20.",
            default=5,
            minimum=3,
            maximum=20,
        )
        self.pt_cal_drift_threshold = config.Number(
            "PT Calibration Drift Threshold (bar)",
            description="Maximum allowed difference between PT1 and PT2 readings (bar). Warning.",
            default=5.0,
        )
        self.filter_dp_warning = config.Number(
            "Filter DP Warning (bar)",
            description="Filter differential pressure warning threshold (bar). Warning.",
            default=2.0,
        )
        self.filter_dp_fail = config.Number(
            "Filter DP Fail (bar)",
            description="Filter differential pressure fail threshold (bar). Critical alarm.",
            default=4.0,
        )
        self.temp_high_warning = config.Number(
            "Temperature High Warning",
            description="Temperature high warning threshold. Warning.",
            default=60.0,
        )
        self.temp_high_alarm = config.Number(
            "Temperature High Alarm",
            description="Temperature high alarm threshold. Critical alarm.",
            default=80.0,
        )

        # --- Alarm Timing ---
        self.alarm_grace_period = config.Number(
            "Alarm Grace Period (s)",
            description="Seconds threshold must be sustained before alarm fires",
            default=5.0,
        )
        self.alarm_min_inter_alarm = config.Number(
            "Min Inter-Alarm Interval (s)",
            description="Minimum seconds between repeated alarm triggers",
            default=60.0,
        )

        # --- Pump Timing ---
        self.pump_start_delay = config.Number(
            "Pump Start Delay (s)",
            description="Delay in seconds before starting pump after command",
            default=2.0,
        )
        self.pump_switchover_delay = config.Number(
            "Pump Switchover Delay (s)",
            description="Delay in seconds before backup pump takes over after primary fault",
            default=5.0,
        )

        # --- Sensor App References ---
        self.pt1_app = config.Application(
            "PT1 Sensor App",
            description="PT1 pressure sensor app instance reference",
        )
        self.pt2_app = config.Application(
            "PT2 Sensor App",
            description="PT2 pressure sensor app instance reference (if dual PT)",
            default=None,
        )
        self.dp_app = config.Application(
            "Filter DP Sensor App",
            description="Filter differential pressure sensor app instance reference",
            default=None,
        )
        self.temp_app = config.Application(
            "Temperature Sensor App",
            description="Temperature sensor app instance reference",
        )

        # --- DI Pin Assignments ---
        self.enable_button_pin = config.Integer(
            "Enable Button DI Pin",
            description="Digital input pin for system enable button",
            default=0,
        )
        self.disable_button_pin = config.Integer(
            "Disable Button DI Pin",
            description="Digital input pin for system disable button",
            default=1,
        )
        self.master_reset_pin = config.Integer(
            "Master Reset DI Pin",
            description="Digital input pin for master alarm reset button",
            default=2,
        )
        self.pump1_reset_pin = config.Integer(
            "Pump 1 Reset DI Pin",
            description="Digital input pin for pump 1 fault reset button",
            default=3,
        )
        self.pump2_reset_pin = config.Integer(
            "Pump 2 Reset DI Pin",
            description="Digital input pin for pump 2 fault reset button",
            default=4,
        )
        self.pt1_enable_pin = config.Integer(
            "PT1 Enable DI Pin",
            description="Digital input pin for PT1 enable/disable toggle",
            default=5,
        )

        # --- VFD Configuration (Full variant) ---
        self.vfd_feedback_pin = config.Integer(
            "VFD Feedback AI Pin",
            description="Analog input pin for VFD speed feedback (0-10V)",
            default=0,
        )
        self.vfd_min_speed = config.Number(
            "VFD Minimum Speed (%)",
            description="Minimum VFD speed percentage",
            default=10.0,
        )

        # --- Output Module Configs ---
        self.motor_1_relay_pin = config.Integer(
            "Motor 1 Relay DO Pin",
            description="DO pin for Motor 1 relay output",
            default=0,
        )
        self.motor_2_relay_pin = config.Integer(
            "Motor 2 Relay DO Pin",
            description="DO pin for Motor 2 relay output",
            default=1,
        )
        self.solenoid_valve_pin = config.Integer(
            "Solenoid Valve DO Pin",
            description="DO pin for solenoid valve output",
            default=2,
        )
        self.master_alarm_lamp_pin = config.Integer(
            "Master Alarm Lamp DO Pin",
            description="DO pin for master alarm lamp output",
            default=3,
        )

        # --- Tag Namespace ---
        self.tag_namespace = config.String(
            "Tag Namespace",
            description="Optional namespace for outbound tags",
            default=None,
        )


def export():
    ImtexHPUConfig().export(
        Path(__file__).parents[2] / "doover_config.json",
        "hydraulic_power_pack_control",
    )


if __name__ == "__main__":
    export()
