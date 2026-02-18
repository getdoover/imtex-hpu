from pydoover.docker import run_app

from .application import ImtexHPUApplication
from .app_config import ImtexHPUConfig


def main():
    """Run the Imtex HPU Controller application."""
    run_app(ImtexHPUApplication(config=ImtexHPUConfig()))
