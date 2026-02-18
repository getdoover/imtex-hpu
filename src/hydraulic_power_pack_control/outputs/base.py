import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class ControllerOutput(ABC):
    """Abstract base class for HPU controller output modules.

    Each output module represents a physical output (digital or analog)
    controlled by the HPU state machine. Outputs are registered in the
    AVAILABLE_OUTPUTS list and iterated generically in the main loop.
    """

    name: str = ""

    def __init__(self, app):
        """Initialize the output module.

        Args:
            app: Reference to the main application instance.
        """
        self.app = app
        self.plt = app.platform_iface
        self.output_pin = self._get_pin()

    def _get_pin(self) -> int:
        """Get the DO/AO pin number from config."""
        pin_attr = f"{self.name}_pin"
        if hasattr(self.app.config, pin_attr):
            return getattr(self.app.config, pin_attr).value
        return None

    @abstractmethod
    async def update(self) -> None:
        """Update the physical output based on current state.

        Called once per main loop iteration after state machine evaluation.
        """
        ...

    async def on_state_change(self, new_state: str) -> None:
        """Optional callback when state machine changes state.

        Override in subclasses that need immediate response to state changes.

        Args:
            new_state: The new state value string.
        """
        pass
