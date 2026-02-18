import logging

from .base import ControllerOutput
from ..app_state import State

log = logging.getLogger(__name__)

# States where the solenoid valve should NOT be energized
SOV_OFF_STATES = [
    State.DISABLED,
    State.MASTER_ALARM,
    State.BOTH_PUMPS_FAULT,
    State.PRESSURE_HIGH_ALARM,
    State.PRESSURE_LOW_ALARM,
    State.DP_DT_ALARM,
    State.TEMP_HIGH_ALARM,
    State.FILTER_FAIL,
]


class SolenoidValveOutput(ControllerOutput):
    """Solenoid valve digital output.

    The solenoid valve is energized whenever the system is in an
    operational or warning state. It is de-energized in disabled state
    and all critical alarm states to ensure safe shutdown.
    """

    name = "solenoid_valve"

    async def update(self) -> None:
        if self.output_pin is not None:
            current_state = self.app.state.get_state_enum()
            active = current_state not in SOV_OFF_STATES
            await self.plt.set_do_async(self.output_pin, 1 if active else 0)
