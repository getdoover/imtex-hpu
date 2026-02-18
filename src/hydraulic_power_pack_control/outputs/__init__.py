from .base import ControllerOutput
from .motor_relay import Motor1RelayOutput, Motor2RelayOutput
from .solenoid_valve import SolenoidValveOutput
from .alarm_lamp import MasterAlarmLampOutput
from .vfd_speed import VFDSpeedOutput

# Registry of all available output modules.
# The application iterates this list to instantiate and update outputs.
AVAILABLE_OUTPUTS = [
    Motor1RelayOutput,
    Motor2RelayOutput,
    SolenoidValveOutput,
    MasterAlarmLampOutput,
    VFDSpeedOutput,
]

__all__ = [
    "ControllerOutput",
    "Motor1RelayOutput",
    "Motor2RelayOutput",
    "SolenoidValveOutput",
    "MasterAlarmLampOutput",
    "VFDSpeedOutput",
    "AVAILABLE_OUTPUTS",
]
