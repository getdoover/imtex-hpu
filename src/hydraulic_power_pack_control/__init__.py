from pydoover.docker import run_app

from .application import HydraulicPowerPackControlApplication
from .app_config import HydraulicPowerPackControlConfig

def main():
    """
    Run the application.
    """
    run_app(HydraulicPowerPackControlApplication(config=HydraulicPowerPackControlConfig()))
