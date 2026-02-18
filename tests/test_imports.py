"""
Basic tests for an application.

This ensures all modules are importable and that the config is valid.
"""

def test_import_app():
    from hydraulic_power_pack_control.application import HydraulicPowerPackControlApplication
    assert HydraulicPowerPackControlApplication

def test_config():
    from hydraulic_power_pack_control.app_config import HydraulicPowerPackControlConfig

    config = HydraulicPowerPackControlConfig()
    assert isinstance(config.to_dict(), dict)

def test_ui():
    from hydraulic_power_pack_control.app_ui import HydraulicPowerPackControlUI
    assert HydraulicPowerPackControlUI

def test_state():
    from hydraulic_power_pack_control.app_state import HydraulicPowerPackControlState
    assert HydraulicPowerPackControlState