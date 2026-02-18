import logging

from .base import ControllerOutput

log = logging.getLogger(__name__)


class Motor1RelayOutput(ControllerOutput):
    """Motor 1 relay digital output.

    Energizes when Pump 1 should be running, as determined by the
    state machine's should_pump_run(1) method.
    """

    name = "motor_1_relay"

    async def update(self) -> None:
        if self.output_pin is not None:
            run = self.app.state.should_pump_run(1)
            await self.plt.set_do_async(self.output_pin, 1 if run else 0)


class Motor2RelayOutput(ControllerOutput):
    """Motor 2 relay digital output.

    Energizes when Pump 2 should be running, as determined by the
    state machine's should_pump_run(2) method. Only active when
    enable_pump_2 is configured.
    """

    name = "motor_2_relay"

    async def update(self) -> None:
        if self.output_pin is not None and self.app.config.enable_pump_2.value:
            run = self.app.state.should_pump_run(2)
            await self.plt.set_do_async(self.output_pin, 1 if run else 0)
        elif self.output_pin is not None:
            # Ensure relay is off when pump 2 disabled
            await self.plt.set_do_async(self.output_pin, 0)
