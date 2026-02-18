import logging

from .base import ControllerOutput
from ..app_state import State, OPERATIONAL_STATES

log = logging.getLogger(__name__)


class VFDSpeedOutput(ControllerOutput):
    """VFD speed feedback reader (optional Full variant).

    Reads the VFD speed feedback from an analog input (0-10V)
    when the enable_vfd config flag is set. The speed value is
    stored on the application instance for UI display.

    Note: This output module reads AI rather than writing DO,
    as VFD speed commands would typically be handled by a separate
    VFD controller. This reads the feedback signal.
    """

    name = "vfd_feedback"

    def _get_pin(self) -> int:
        """Override to get VFD feedback AI pin."""
        if hasattr(self.app.config, "vfd_feedback_pin"):
            return self.app.config.vfd_feedback_pin.value
        return None

    async def update(self) -> None:
        if not self.app.config.enable_vfd.value:
            self.app.vfd_speed = None
            return

        if self.output_pin is not None:
            current_state = self.app.state.get_state_enum()
            if current_state in OPERATIONAL_STATES:
                try:
                    voltage = await self.plt.get_ai_async(self.output_pin)
                    if voltage is not None:
                        # Convert 0-10V to 0-100% speed
                        self.app.vfd_speed = (voltage / 10.0) * 100.0
                    else:
                        self.app.vfd_speed = None
                except Exception as e:
                    log.warning(f"Failed to read VFD feedback: {e}")
                    self.app.vfd_speed = None
            else:
                self.app.vfd_speed = 0.0
