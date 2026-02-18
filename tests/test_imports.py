"""
Basic tests for the HPU controller application.

This ensures all modules are importable and that the config is valid.
"""

import pytest

from hydraulic_power_pack_control.app_config import ImtexHPUConfig

# Create a single config instance to avoid pydoover Schema class-level
# element name duplication errors on repeated instantiation.
_config = ImtexHPUConfig()


def test_import_app():
    from hydraulic_power_pack_control.application import ImtexHPUApplication
    assert ImtexHPUApplication


def test_config():
    assert isinstance(_config.to_dict(), dict)


def test_ui():
    from hydraulic_power_pack_control.app_ui import ImtexHPUUI

    ui = ImtexHPUUI(_config)
    elements = ui.fetch()
    assert elements
    assert len(elements) > 0


def test_state():
    from hydraulic_power_pack_control.app_state import ImtexHPUState, State
    state = ImtexHPUState()
    assert state.state == State.DISABLED.value


def test_outputs():
    from hydraulic_power_pack_control.outputs import AVAILABLE_OUTPUTS, ControllerOutput
    assert len(AVAILABLE_OUTPUTS) == 5
    for output_cls in AVAILABLE_OUTPUTS:
        assert issubclass(output_cls, ControllerOutput)


def test_state_enum():
    from hydraulic_power_pack_control.app_state import State
    assert len(State) == 16
    assert State.DISABLED.value == "disabled"
    assert State.IDLE.value == "idle"
    assert State.MASTER_ALARM.value == "master_alarm"
