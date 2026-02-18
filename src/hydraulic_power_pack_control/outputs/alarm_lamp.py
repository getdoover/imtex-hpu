import logging

from .base import ControllerOutput
from ..app_state import State

log = logging.getLogger(__name__)

# States where the master alarm lamp should be energized
ALARM_LAMP_STATES = [
    State.MASTER_ALARM,
    State.PRESSURE_HIGH_ALARM,
    State.PRESSURE_LOW_ALARM,
    State.DP_DT_ALARM,
    State.TEMP_HIGH_ALARM,
    State.FILTER_FAIL,
    State.BOTH_PUMPS_FAULT,
    State.PUMP1_FAULT,
    State.PUMP2_FAULT,
]


class MasterAlarmLampOutput(ControllerOutput):
    """Master alarm lamp digital output.

    The alarm lamp is energized when the system is in any alarm or
    fault state. This is a single physical lamp that serves as the
    master alarm indicator.
    """

    name = "master_alarm_lamp"

    async def update(self) -> None:
        if self.output_pin is not None:
            current_state = self.app.state.get_state_enum()
            alarmed = current_state in ALARM_LAMP_STATES
            await self.plt.set_do_async(self.output_pin, 1 if alarmed else 0)
