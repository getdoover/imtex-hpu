import random
import math
import time

from pydoover.docker import Application, run_app
from pydoover.config import Schema


class HPUSimulator(Application):
    """Simulator that publishes fake sensor tag values.

    Simulates 4 companion sensor apps (PT1, PT2, filter DP, temperature)
    by publishing "value" tags that the HPU controller reads.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started = time.time()
        self.base_pressure = 190.0  # Start within pressure band

    async def setup(self):
        self.loop_target_period = 0.5

    async def main_loop(self):
        elapsed = time.time() - self.started

        # Simulate pressure with slow sine wave oscillation
        pressure = self.base_pressure + 15 * math.sin(elapsed / 30)
        # Add small noise
        pressure += random.uniform(-0.5, 0.5)

        # Simulate temperature slowly rising then stabilizing
        temperature = 25.0 + 10 * (1 - math.exp(-elapsed / 120))
        temperature += random.uniform(-0.2, 0.2)

        # Simulate filter DP (slowly increasing as filter clogs)
        filter_dp = 0.5 + 0.001 * elapsed
        filter_dp += random.uniform(-0.05, 0.05)

        await self.set_tags_async({
            "value": round(pressure, 2),
            "raw_value": round(pressure + random.uniform(-1, 1), 2),
        })


def main():
    """Run the HPU simulator application."""
    run_app(HPUSimulator(config=Schema()))


if __name__ == "__main__":
    main()
