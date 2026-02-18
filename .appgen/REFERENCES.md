# References

Curated patterns extracted from reference repositories.

## Reference 1: 4-20mA Sensor App (`4-20ma-sensor`)

### Aspect: Tag Communication Patterns

#### Pattern Summary

The 4-20mA sensor app publishes sensor readings via tags that other apps can consume. In the `main_loop`, after reading and filtering the analog input, the app calls `self.set_tags_async()` with a dictionary of tag name/value pairs. The two tags published are `"value"` (the filtered/calibrated reading) and `"raw_value"` (the unfiltered ADC reading).

Consumer apps (like the HPU controller) read these tags by calling `self.get_tag("value", app_key)` where `app_key` is the config.Application reference to the sensor app instance. This allows the controller to read from multiple sensor app instances (PT1, PT2, DP, Temp) without any direct coupling - communication is entirely through the tag system.

The tag namespace is implicit per app instance. Each deployed instance of the sensor app publishes its own `"value"` tag, and the controller addresses the correct instance via the `config.Application` reference configured at deployment time.

#### Key Implementation Details
- Tags are published via `await self.set_tags_async({"value": filtered_reading, "raw_value": raw_reading})`
- Tags are consumed via `self.get_tag("value", self.config.pt1_app.value)` where the app reference comes from config
- `config.Application` type in the config schema creates a picker for referencing another deployed app instance
- Tag communication is async and fire-and-forget from the publisher side
- The consumer must handle `None` values gracefully when a tag hasn't been published yet

#### Representative Code

**Publisher (sensor app - `application.py`):**
```python
class Sensor420maApplication(Application):
    config: Sensor420maConfig

    async def setup(self):
        self.loop_target_period = 0.5
        self.sensor = Sensor420ma(
            self.config.ai_pin.value,
            self.platform_iface,
            [self.config.min_range.value, self.config.max_range.value],
            self.config.process_variance.value,
        )
        self.ui = Sensor420maUI(self.config)
        self.ui_manager.add_children(*self.ui.fetch())

    async def main_loop(self):
        await self.sensor.update()
        filtered_reading = self.sensor.value
        raw_reading = self.sensor.raw_value
        self.ui.update(filtered_reading)
        await self.set_tags_async({
            "value": filtered_reading,
            "raw_value": raw_reading
        })
```

**Consumer (controller app - from spec `application.py`):**
```python
async def read_sensors(self):
    """Read sensor values from companion sensor app tags."""
    self.pt1_pressure = self.get_tag("value", self.config.pt1_app.value)
    self.pt2_pressure = self.get_tag("value", self.config.pt2_app.value)
    self.temperature = self.get_tag("value", self.config.temp_app.value)
    self.filter_dp = self.get_tag("value", self.config.dp_app.value)
```

#### Applicability Notes

The HPU controller app will consume tags from 2-4 companion sensor app instances (PT1, PT2, DP, Temp). The controller config must include `config.Application` references for each sensor app. The tag names `"value"` and `"raw_value"` are the standard interface contract from the 4-20mA sensor app.

---

### Aspect: Sensor Reading Interface (4-20mA Conversion & Kalman Filtering)

#### Pattern Summary

The `Sensor420ma` class encapsulates the full pipeline for reading a 4-20mA current loop signal: raw ADC reading via `platform_iface.get_ai(pin)`, Kalman filtering via the `@apply_async_kalman_filter()` decorator from pydoover utils, conversion from 4-20mA to engineering units using a configurable calibration range, and a rolling data store for averaging/initialization checks.

The Kalman filter is applied as a decorator on `get_reading()` with a configurable `process_variance` parameter. The conversion formula maps the 4-20mA range (actually mA values) to the user-configured `[min_range, max_range]` using linear interpolation: `converted = ((reading - 4) / 16) * calibration_range + calibration_low`. Readings below 3.5mA are rejected as wire-break or out-of-range conditions.

The sensor requires at least 3 valid readings before reporting a filtered value (initialization check), which prevents spurious outputs during startup.

#### Key Implementation Details
- Raw reading via `await self.plt_iface.get_ai(self.pin_no)` returns mA value
- Kalman filter applied as decorator: `@apply_async_kalman_filter()` with `kf_process_variance` parameter
- Wire-break detection: readings below 3.5mA are rejected (returns None)
- Linear conversion: `((reading - 4) / 16) * range + offset`
- Initialization guard: minimum 3 valid readings before `value` property returns non-None
- Rolling data store of last 10 values for averaging

#### Representative Code

```python
class Sensor420ma:
    def __init__(self, pin_no, plt_iface, calibration, process_variance=0.5):
        self.pin_no = pin_no
        self.process_variance = process_variance
        self.plt_iface = plt_iface
        self.data_store = []
        self.calibration_low = calibration[0]
        self.calibration_high = calibration[1]
        self.calibration_range = self.calibration_high - self.calibration_low
        self.raw_value = None
        self.filtered_val = 0
        self.max_values = 10

    @apply_async_kalman_filter()
    async def get_reading(self, kf_process_variance=None, _reading=None):
        if _reading is None:
            reading = await self.plt_iface.get_ai(self.pin_no)
        else:
            reading = _reading
        if reading is None:
            return None
        self.raw_value = reading
        if reading < 3.5:
            return None  # Wire-break detection
        return reading

    def convert_reading(self, reading):
        if reading is None:
            return None
        reading = reading - 4
        if reading < 0 and reading > -0.5:
            reading = 0
        converted = (reading / 16) * self.calibration_range + self.calibration_low
        return converted

    @property
    def value(self):
        if self.is_initialised():
            return self.filtered_val
        else:
            return None
```

#### Applicability Notes

The HPU controller does not read analog inputs directly for pressure/temperature - it relies on companion sensor app instances that use this exact pattern. The controller reads VFD feedback (0-10V voltage input) directly via `platform_iface.get_ai()`. Understanding this conversion pipeline helps when configuring the sensor apps for the correct pressure/temperature ranges.

---

### Aspect: Alarm Handling

#### Pattern Summary

The `Alarm` class provides a reusable, configurable alarm with grace period and minimum inter-alarm timing. It takes a `threshold_met` callable (e.g., `lambda value, threshold: value > threshold`) and an async or sync `callback`. The alarm follows a three-gate pattern: (1) is the threshold met? (2) has the grace period elapsed since first trigger? (3) has enough time passed since the last alarm?

The `create_alarm` factory function wraps any async function that returns a value, automatically checking the alarm against its return value on each call. This decorator pattern allows alarms to be attached to sensor reading functions transparently.

Grace period prevents alarm triggering on transient spikes - the threshold must be continuously met for the full grace duration. The min-inter-alarm interval prevents rapid re-triggering after a reset.

#### Key Implementation Details
- `threshold_met(value, threshold)` callable determines alarm condition
- `grace_period` (default 1 hour): how long threshold must be sustained before alarm fires
- `min_inter_alarm` (default 24 hours): minimum time between alarm activations
- `callback` can be async (checked with `asyncio.iscoroutinefunction`)
- `get_threshold_val()` callable allows dynamic threshold retrieval from config
- `create_alarm()` decorator wraps any async value-returning function with alarm checking
- `alarm.alarm_active` boolean tracks current alarm state
- `alarm.reset_alarm()` clears timing state for manual reset

#### Representative Code

```python
class Alarm:
    def __init__(self, threshold_met, callback=None, grace_period=None,
                 min_inter_alarm=None, get_threshold_val=None):
        self.threshold_met = threshold_met
        self.callback = callback
        self.grace_period = grace_period or 60 * 60  # 1 hour default
        self.min_inter_alarm = min_inter_alarm or 60 * 60 * 24  # 1 day default
        self.get_threshold_val = get_threshold_val
        self.last_alarm_time = None
        self.initial_trigger_time = None
        self.alarm_active = False

    async def check_value(self, value, threshold_met, grace_period=None,
                          min_inter_alarm=None):
        threshold = self.get_threshold_val()
        if threshold is None:
            return False
        if value is None:
            return False
        if self.threshold_met(value, threshold) is False:
            self.alarm_active = False
            self.initial_trigger_time = None
            return False
        elif not self.alarm_active:
            if self._check_grace_period():
                if self._check_min_inter_alarm():
                    await self._trigger_alarm()

    async def _trigger_alarm(self):
        self.alarm_active = True
        if self.callback:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        self.last_alarm_time = time.time()
```

#### Applicability Notes

The HPU controller will need multiple alarm instances: pressure high, pressure low, dP/dt rate of change, temperature high, filter DP warning/fail, and PT calibration drift. The grace period pattern is particularly important for the HPU to avoid false alarms from transient pressure spikes during pump cycling. The spec defines specific alarm thresholds as configurable values in the config schema. The `create_alarm` decorator pattern could be used to wrap the sensor reading methods, or alarms can be checked explicitly in the state machine's `evaluate_state` method as shown in the spec.

---

### Aspect: App Structure & Architecture

#### Pattern Summary

The 4-20mA sensor app follows the standard pydoover Docker device app pattern with a clean separation of concerns: `application.py` (main Application subclass with setup/main_loop), `app_config.py` (config.Schema subclass defining all configuration), `app_ui.py` (UI element definitions), and domain modules (`sensor.py`, `alarm.py`).

The entry point is defined in `pyproject.toml` as `doover-app-run = "sensor_4_20ma:main"`, which calls `run_app(Sensor420maApplication(config=Sensor420maConfig()))` from `__init__.py`. The `Application` base class provides the async event loop, platform interface, UI manager, and tag system. The config schema class auto-exports to `doover_config.json` via an `export()` function and a `export-config` script entry point.

The Dockerfile uses a two-stage build with `uv` for dependency management, inheriting from `spaneng/doover_device_base` as the base image.

#### Key Implementation Details
- Package layout: `src/{package_name}/` with `__init__.py` containing `main()` entry point
- Application subclass overrides `async setup()` and `async main_loop()`
- `setup()` initializes sensors, UI, and registers UI elements via `self.ui_manager.add_children()`
- `main_loop()` runs at `self.loop_target_period` interval (0.5s for sensor, 1.0s for controller)
- Config schema defined as `config.Schema` subclass with typed fields (`config.Integer`, `config.Number`, `config.String`, `config.Boolean`, `config.Object`)
- Config exports to JSON schema via `Schema.export(path, name)`
- UI elements: `ui.NumericVariable`, `ui.BooleanVariable`, `ui.TextVariable`, `ui.StateCommand`, `ui.Slider`, `ui.Submodule`
- Dockerfile: multi-stage build, `spaneng/doover_device_base` base, `uv sync` for deps, `CMD ["doover-app-run"]`
- `pyproject.toml` uses hatchling build system with `src/` layout

#### Representative Code

**`__init__.py` (entry point):**
```python
from pydoover.docker import run_app
from .application import Sensor420maApplication
from .app_config import Sensor420maConfig

def main():
    run_app(Sensor420maApplication(config=Sensor420maConfig()))
```

**`pyproject.toml` (structure):**
```toml
[project]
name = "4-20ma-sensor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pydoover>=0.4.13", "transitions>=0.9.2"]

[project.scripts]
doover-app-run = "sensor_4_20ma:main"
export-config = "sensor_4_20ma.app_config:export"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sensor_4_20ma"]
```

**`app_config.py` (config schema pattern):**
```python
from pathlib import Path
from pydoover import config

class Sensor420maConfig(config.Schema):
    def __init__(self):
        self.ai_pin = config.Integer("AI Pin Number", default=0, minimum=0, maximum=15)
        self.min_range = config.Number("Min Range", default=0.0)
        self.max_range = config.Number("Max Range", default=100.0)
        self.measurement_units = config.String("Measurement Units", default=None)
        self.process_variance = config.Number("Process Variance", default=0.5)

def export():
    Sensor420maConfig().export(Path(__file__).parents[2] / "doover_config.json", "4_20ma_sensor")
```

#### Applicability Notes

The HPU controller follows this exact same structural pattern but with more complexity: additional modules for state machine (`app_state.py`), pressure control logic (`pressure_control.py`), alarm management (`alarm_manager.py`), and an `outputs/` sub-package for digital/analog output modules. The config schema is significantly larger with variant flags, alarm thresholds, DI pin assignments, and sensor app references. The UI includes state commands, live values, alarm indicators, sliders, and submodules for grouping.

---

## Reference 2: Imtex HPU Controller Specification (`imtex-hpu-doover-spec.md`)

### Aspect: State Machine Design

#### Pattern Summary

The HPU controller uses a flat state machine (not hierarchical) with 16 states covering the full operational lifecycle: DISABLED, IDLE, PRESSURISING, PRESSURE_OK, pump fault states (PUMP1_FAULT, PUMP2_FAULT, BOTH_PUMPS_FAULT), warning states (PT_CAL_WARNING, FILTER_WARNING, TEMP_HIGH_WARNING), and critical alarm states (FILTER_FAIL, TEMP_HIGH_ALARM, PRESSURE_HIGH_ALARM, PRESSURE_LOW_ALARM, DP_DT_ALARM, MASTER_ALARM).

The state machine is implemented using the `pydoover.state.StateMachine` class (wrapping the `transitions` library). States can have `on_enter` and `on_exit` callbacks. Transitions define trigger names, source states (can use `"*"` for any state), and destination states. Critical alarms can trigger from any state, while warnings only trigger from operational states (IDLE, PRESSURISING, PRESSURE_OK).

A `spin_state()` method repeatedly calls `evaluate_state()` until the state stabilizes, allowing cascading transitions within a single loop iteration. The `evaluate_state()` method contains the core logic: checking critical alarms first (pressure high, dP/dt, temperature), then state-specific behavior, then warning conditions.

#### Key Implementation Details
- States defined as `enum.Enum` for type safety
- State machine uses `queued=True` for deterministic transition ordering
- Critical alarms override any state (source: `"*"`)
- Warning states only reachable from operational states
- `should_pump_run(pump_number)` method determines pump state based on current state
- `active_pump` property returns 1 or 2 based on fault state
- `on_state_change()` notifies all output modules
- `spin_state()` loop ensures state stabilization before proceeding
- Alarm clearing requires explicit `clear_alarm` / `clear_warning` triggers (manual reset)

#### Representative Code

```python
class State(enum.Enum):
    IDLE = "idle"
    PRESSURISING = "pressurising"
    PRESSURE_OK = "pressure_ok"
    PUMP1_FAULT = "pump1_fault"
    PUMP2_FAULT = "pump2_fault"
    BOTH_PUMPS_FAULT = "both_pumps_fault"
    PT_CAL_WARNING = "pt_cal_warning"
    FILTER_WARNING = "filter_warning"
    FILTER_FAIL = "filter_fail"
    TEMP_HIGH_WARNING = "temp_high_warning"
    TEMP_HIGH_ALARM = "temp_high_alarm"
    PRESSURE_HIGH_ALARM = "pressure_high_alarm"
    DP_DT_ALARM = "dp_dt_alarm"
    MASTER_ALARM = "master_alarm"
    DISABLED = "disabled"

transitions = [
    {"trigger": "enable", "source": State.DISABLED, "dest": State.IDLE},
    {"trigger": "disable", "source": "*", "dest": State.DISABLED},
    {"trigger": "pressure_low", "source": [State.IDLE, State.PRESSURE_OK], "dest": State.PRESSURISING},
    {"trigger": "pressure_ok", "source": State.PRESSURISING, "dest": State.PRESSURE_OK},
    {"trigger": "pump1_fault", "source": [State.PRESSURISING, State.PRESSURE_OK, State.IDLE], "dest": State.PUMP1_FAULT},
    {"trigger": "pressure_high_alarm", "source": "*", "dest": State.PRESSURE_HIGH_ALARM},
    {"trigger": "dp_dt_alarm", "source": "*", "dest": State.DP_DT_ALARM},
    {"trigger": "clear_alarm", "source": [State.PRESSURE_HIGH_ALARM, State.DP_DT_ALARM, ...], "dest": State.IDLE},
]
```

#### Applicability Notes

This state machine design is the core of the HPU controller app. It must be implemented in `app_state.py`. The `transitions` library is already a dependency of the 4-20mA sensor app (`transitions>=0.9.2`). The state enum values are used as strings in the UI and tag communication.

---

### Aspect: Config Schema

#### Pattern Summary

The HPU controller config schema is extensive, covering variant selection, pressure control parameters, alarm thresholds, sensor app references, DI pin assignments, VFD configuration, and pump timing. It uses the `pydoover.config` module with typed fields and follows the same export pattern as the sensor app.

A notable pattern is the output module config registration: each output class provides a static `get_config_element()` method that returns a config element, and the schema iterates over `AVAILABLE_OUTPUTS` to register all output configs dynamically. This decouples output configuration from the main schema.

Sensor app references use `config.Application` type, which creates a UI picker in the Doover platform for selecting which deployed app instance to read tags from.

#### Key Implementation Details
- Variant flags: `enable_pump_2` (Boolean), `enable_vfd` (Boolean)
- Pressure band: `pressure_upper_band`, `pressure_lower_band` (Number, 0-500 bar)
- Alarm thresholds: `pressure_high_alarm`, `pressure_low_alarm`, `dp_dt_alarm_threshold`, `pt_cal_drift_threshold`, `filter_dp_warning`, `filter_dp_fail`, `temp_high_warning`, `temp_high_alarm`
- dP/dt config: `dp_dt_buffer_size` (Integer, 3-20)
- Pump timing: `pump_start_delay`, `pump_switchover_delay` (Number, seconds)
- VFD config: `vfd_feedback_pin`, `vfd_min_speed`
- Sensor references: `pt1_app`, `pt2_app`, `dp_app`, `temp_app` (config.Application)
- DI pins: `enable_button_pin`, `disable_button_pin`, `master_reset_pin`, `pump1_reset_pin`, `pump2_reset_pin`, `pt1_enable_pin`
- Output configs registered dynamically from output module classes

#### Representative Code

```python
class ImtexHPUConfig(config.Schema):
    def __init__(self):
        # Register output configs dynamically
        self.outputs = {}
        for output in AVAILABLE_OUTPUTS:
            elems = output.get_config_element()
            self.add_element(elems)
            self.outputs[output] = elems

        # Variant flags
        self.enable_pump_2 = config.Boolean("Enable Pump 2 (Redundant)", default=True)
        self.enable_vfd = config.Boolean("Enable VFD Speed Control", default=False)

        # Pressure band control
        self.pressure_upper_band = config.Number("Pressure Upper Band (bar)", default=200.0, minimum=0.0, maximum=500.0)
        self.pressure_lower_band = config.Number("Pressure Lower Band (bar)", default=180.0, minimum=0.0, maximum=500.0)

        # Sensor app references
        self.pt1_app = config.Application("PT1 Sensor App")
        self.pt2_app = config.Application("PT2 Sensor App")
        self.dp_app = config.Application("DP Sensor App")
        self.temp_app = config.Application("Temperature Sensor App")

        # DI pin assignments
        self.enable_button_pin = config.Integer("Enable Button DI Pin", default=0)
        self.disable_button_pin = config.Integer("Disable Button DI Pin", default=1)
        self.master_reset_pin = config.Integer("Master Reset DI Pin", default=2)
```

#### Applicability Notes

This config schema defines every tunable parameter for the HPU controller. It must be implemented in `app_config.py` with the dynamic output config registration pattern. The `config.Application` references are critical for the tag-based sensor communication.

---

### Aspect: UI Definition

#### Pattern Summary

The HPU UI is organized into primary controls (StateCommand for enable/disable), live sensor values (NumericVariable for pressure, temperature, filter DP, dP/dt, VFD speed), pump status indicators (BooleanVariable, TextVariable), virtual alarm indicators (BooleanVariable per alarm type), and adjustable settings (Slider for pressure bands and alarm thresholds). UI elements are grouped into Submodules for alarm status and alarm settings.

The `fetch()` method conditionally includes UI elements based on variant config (pump 2, VFD). The `update()` method accepts all live values and an alarms dictionary for batch updates.

#### Key Implementation Details
- `ui.StateCommand` for enable/disable with `user_options` and `coerce()` method for button callbacks
- `ui.NumericVariable` with `precision` parameter for decimal places
- `ui.BooleanVariable` for pump running status and alarm indicators
- `ui.TextVariable` for active pump label and system state string
- `ui.Slider` for adjustable thresholds with min/max/step
- `ui.Submodule` for grouping related elements (alarm status, alarm settings)
- Conditional element inclusion in `fetch()` based on config variant flags
- Batch update via `update()` method with alarms dict

#### Representative Code

```python
class ImtexHPUUI:
    def __init__(self, config: ImtexHPUConfig):
        self.command = ui.StateCommand("command", "HPU Command",
            user_options=[ui.Option("disabled", "Disabled"), ui.Option("enabled", "Enabled")],
            default="disabled")
        self.pressure = ui.NumericVariable("pressure", "System Pressure (bar)", precision=1)
        self.pump1_running = ui.BooleanVariable("pump1_running", "Pump 1 Running")
        self.system_state = ui.TextVariable("system_state", "System State")
        self.alarm_pressure_high = ui.BooleanVariable("alarm_pressure_high", "Pressure High Alarm")
        self.pressure_upper_band = ui.Slider("pressure_upper_band", "Pressure Upper Band (bar)",
            min_val=0, max_val=500, step_size=1, default=config.pressure_upper_band.value)
        self.alarm_status_submodule = ui.Submodule("alarm_status", "Alarm Status",
            children=[self.alarm_pressure_high, ...])

    def fetch(self):
        elems = [self.command, self.pressure, self.system_state, ...]
        if self.config.enable_pump_2.value:
            elems.append(self.pump2_running)
        return elems
```

#### Applicability Notes

The UI definition provides the complete interface for both the Doover cloud dashboard and the local engineering app. The StateCommand with `coerce()` is the pattern for DI button callbacks to change the UI command state. Submodules provide logical grouping in the UI.

---

### Aspect: Output Modules (Motor Relays, SOV, Alarm Lamp)

#### Pattern Summary

Output modules follow an abstract base class pattern (`ControllerOutput`) where each physical output (motor relay, solenoid valve, alarm lamp) is a separate class with a standard interface. Each output provides: (1) a static `get_config_element()` for its config (typically a DO pin number), (2) an async `update()` method called each main loop, and (3) an optional `on_state_change()` callback.

The output module registry (`AVAILABLE_OUTPUTS` list) allows the application to iterate over all outputs generically, and the config schema to register all output config elements dynamically. This pattern makes it easy to add new outputs (e.g., pump lamps, VFD speed) without modifying the application or config classes.

#### Key Implementation Details
- `ControllerOutput` ABC with `name`, `get_config_element()`, `update()`, `on_state_change()`
- Each output reads its DO pin from config and calls `self.plt.set_do(pin, value)`
- Motor relay outputs check `self.app.state.should_pump_run(pump_number)`
- SOV output checks state is not in critical alarm states (DISABLED, MASTER_ALARM, etc.)
- Alarm lamp output checks state against a list of `ALARM_STATES`
- `AVAILABLE_OUTPUTS` list used for registry and iteration

#### Representative Code

```python
class Motor1RelayOutput(ControllerOutput):
    name = "motor_1_relay"

    @staticmethod
    def get_config_element():
        return config.Integer("Motor 1 Relay DO Pin", default=0, minimum=0, maximum=10)

    async def update(self) -> None:
        if self.output_pin is not None:
            run = self.app.state.should_pump_run(1)
            await self.plt.set_do(self.output_pin, 1 if run else 0)

class SolenoidValveOutput(ControllerOutput):
    name = "solenoid_valve"

    async def update(self) -> None:
        if self.output_pin is not None:
            active = self.app.state.state not in [
                State.DISABLED, State.MASTER_ALARM,
                State.BOTH_PUMPS_FAULT, State.PRESSURE_HIGH_ALARM,
            ]
            await self.plt.set_do(self.output_pin, 1 if active else 0)

class MasterAlarmLampOutput(ControllerOutput):
    name = "master_alarm_lamp"
    ALARM_STATES = [State.MASTER_ALARM, State.PRESSURE_HIGH_ALARM, State.DP_DT_ALARM,
                    State.TEMP_HIGH_ALARM, State.FILTER_FAIL, State.BOTH_PUMPS_FAULT,
                    State.PUMP1_FAULT, State.PUMP2_FAULT]

    async def update(self) -> None:
        if self.output_pin is not None:
            alarmed = self.app.state.state in self.ALARM_STATES
            await self.plt.set_do(self.output_pin, 1 if alarmed else 0)
```

#### Applicability Notes

The output module pattern is essential for the HPU controller. The `outputs/` sub-package should contain: `base.py` (ABC), `motor_relay.py` (Motor1, Motor2), `solenoid_valve.py`, `alarm_lamp.py`, and optionally `vfd_speed.py` for the VFD variant. The `__init__.py` should export `AVAILABLE_OUTPUTS` and `ControllerOutput`.

---

### Aspect: Pressure Band Control Logic

#### Pattern Summary

The HPU uses simple hysteresis (on/off band) control for pressure maintenance, not continuous PID. When pressure drops below `pressure_lower_band`, the pump starts (state transitions to PRESSURISING). When pressure reaches `pressure_upper_band`, the pump stops (state transitions to PRESSURE_OK). This band-gap prevents rapid pump cycling.

For VFD-equipped variants, a PID loop can modulate motor speed targeting the midpoint of the pressure band, but the basic pattern is on/off with hysteresis.

#### Key Implementation Details
- Two configurable thresholds: `pressure_lower_band` (start pump) and `pressure_upper_band` (stop pump)
- Hysteresis prevents hunting: pump doesn't stop until upper band reached, doesn't start until lower band reached
- State machine transitions: IDLE/PRESSURE_OK -> PRESSURISING (on pressure_low trigger), PRESSURISING -> PRESSURE_OK (on pressure_ok trigger)
- Pressure reading comes from active PT sensor (PT1 preferred, fallback to PT2)
- VFD variant can use PID targeting band midpoint instead of simple on/off

#### Representative Code

```python
async def evaluate_state(self):
    s = self.state
    app = self.app

    if s == State.IDLE:
        if app.pressure is not None and app.pressure < app.config.pressure_lower_band.value:
            await self.pressure_low()  # -> PRESSURISING

    elif s == State.PRESSURISING:
        if app.pressure is not None and app.pressure >= app.config.pressure_upper_band.value:
            await self.pressure_ok()  # -> PRESSURE_OK

    elif s == State.PRESSURE_OK:
        if app.pressure is not None and app.pressure < app.config.pressure_lower_band.value:
            await self.pressure_low()  # -> PRESSURISING
```

#### Applicability Notes

This is the core operational logic for the HPU. The pressure band values (default 180-200 bar) must be configurable. The controller's main loop reads pressure from sensor tags, and the state machine determines pump state based on these thresholds.

---

### Aspect: Redundant Pump Logic

#### Pattern Summary

The HPU supports optional redundant pumping with automatic failover. Pump 1 is always primary. If Pump 1 faults, the state machine transitions to PUMP1_FAULT and Pump 2 automatically takes over after a configurable switchover delay. If both pumps fault, the system enters BOTH_PUMPS_FAULT with master alarm. Pump fault recovery requires physical button press (DI) or remote UI command.

The `should_pump_run(pump_number)` method on the state machine determines whether a given pump should be running based on the current state. The `active_pump` property returns 1 or 2 based on which pump is currently designated.

#### Key Implementation Details
- `enable_pump_2` config flag enables/disables redundancy
- `pump_switchover_delay` configurable delay before backup takes over
- State transitions: operational state -> PUMP1_FAULT -> (auto switchover to pump 2)
- PUMP1_FAULT + PUMP2_FAULT -> BOTH_PUMPS_FAULT (master alarm)
- Reset via DI button (`pump1_reset_pin`, `pump2_reset_pin`) or UI command
- `should_pump_run(pump_number)` returns False for disabled, critical alarm, or faulted pump
- `active_pump` property returns 2 only when pump 1 is faulted

#### Applicability Notes

Redundant pump logic must be implemented in the state machine. The pump fault detection mechanism (motor overload relay, VFD fault signal) needs to be defined - possibly via a DI input or timeout if pressure doesn't rise after pump start.

---

### Aspect: dP/dt Rate of Change Detection

#### Pattern Summary

The controller maintains a rolling buffer of `(timestamp, pressure)` tuples to detect rapid pressure changes that indicate leaks or burst hoses. The rate of change is calculated as `dP/dt = (P_newest - P_oldest) / (T_newest - T_oldest)`. If the absolute value exceeds the configured threshold, a DP_DT_ALARM is triggered.

The buffer uses Python's `collections.deque` with a configurable `maxlen` (default 5 samples). This provides a simple moving window without explicit cleanup.

#### Key Implementation Details
- `deque(maxlen=dp_dt_buffer_size)` for automatic oldest-sample eviction
- Each sample: `(time.time(), self.pressure)` appended each main loop
- Rate calculation only when buffer has >= 2 samples
- Threshold comparison uses absolute value: `abs(dp_dt) > threshold`
- Detects both positive (burst/overpressure) and negative (leak) rate changes
- Buffer size configurable (default 5, range 3-20) to tune sensitivity vs. noise rejection

#### Representative Code

```python
def calculate_dp_dt(self):
    if self.pressure is not None:
        self.pressure_buffer.append((time.time(), self.pressure))
    if len(self.pressure_buffer) >= 2:
        t_old, p_old = self.pressure_buffer[0]
        t_new, p_new = self.pressure_buffer[-1]
        dt = t_new - t_old
        if dt > 0:
            self.dp_dt_value = (p_new - p_old) / dt
        else:
            self.dp_dt_value = 0.0
    else:
        self.dp_dt_value = None
```

#### Applicability Notes

The dP/dt calculation runs every main loop iteration (1s default). With a buffer size of 5, it calculates rate over approximately 5 seconds. This must be tuned based on actual pump cycling behavior to avoid false alarms during normal pressurising/depressurising.

---

### Aspect: PT Calibration Drift Detection

#### Pattern Summary

With redundant pressure transmitters (PT1 and PT2), the controller compares readings each loop. If the absolute difference exceeds `pt_cal_drift_threshold` (default 5 bar), the system enters PT_CAL_WARNING. This is a non-critical warning - the system continues operating but alerts the engineer that one sensor may need recalibration.

Individual PTs can be disabled via DI button or engineering app for maintenance, which removes them from the comparison and pressure selection logic.

#### Key Implementation Details
- Drift check: `abs(pt1_pressure - pt2_pressure) > pt_cal_drift_threshold`
- Only checked when both PT1 and PT2 have valid readings (not None)
- Warning state only (not critical alarm) - system continues operating
- PT1 preferred for active pressure, PT2 as fallback
- `pt1_enabled` / `pt2_enabled` flags toggled via DI or UI
- PT disable removes sensor from both drift comparison and pressure selection

#### Applicability Notes

This feature requires the controller to track both PT readings separately even though only one is used as the active pressure source. The drift threshold must be configurable per deployment since transmitter accuracy varies.

---

### Aspect: Filter DP Monitoring

#### Pattern Summary

The differential pressure across the hydraulic filter is monitored with two thresholds: warning (filter starting to clog) and fail (filter critically clogged). Warning is non-critical (notification only), while fail triggers a shutdown with master alarm.

#### Key Implementation Details
- Two thresholds: `filter_dp_warning` (default 2 bar) and `filter_dp_fail` (default 4 bar)
- Warning: `FILTER_WARNING` state, notification/lamp, system continues
- Fail: `FILTER_FAIL` state, master alarm, pumps stop
- DP reading from companion `imtex_hpu_dp_sensor` app via tags
- Checked only in operational states (IDLE, PRESSURISING, PRESSURE_OK)

#### Applicability Notes

Filter DP monitoring is a standard feature in all variants except Basic. The fail threshold triggers a critical shutdown because a clogged filter can cause pump damage.

---

### Aspect: Master Alarm Cascading

#### Pattern Summary

Multiple alarm conditions cascade into a master alarm that activates a physical alarm lamp DO and stops all pumps. The master alarm is a catch-all state that triggers from any of: pressure high, dP/dt alarm, temperature high, filter fail, or both pumps faulted.

Clearing the master alarm requires a physical master reset button (DI) or remote UI command. After clearing, the system returns to IDLE state.

#### Key Implementation Details
- Master alarm triggered by any critical alarm condition
- Physical DO output for master alarm lamp
- Manual reset required (no auto-clear)
- Reset via DI2 (master reset button) or UI command
- Reset callback checks current state to determine `clear_alarm` vs `clear_warning`
- After reset, all alarm flags cleared and state returns to IDLE

#### Applicability Notes

The master alarm is the single physical alarm output, replacing individual alarm lamps for the reduced IO strategy. Virtual alarm indicators in the UI provide the detail of which specific alarm triggered.

---

### Aspect: DI Button Callbacks

#### Pattern Summary

Physical buttons are connected to digital inputs and handled via the `platform_iface.start_di_pulse_listener()` method. Each DI has a callback function that fires on rising edge detection. The callbacks modify the UI command state (enable/disable) or trigger state machine transitions (reset alarms, reset pump faults).

The callback signature is `async def callback(di, val, dt_secs, counter, edge)`. Inside the callback, `await self.get_di(di)` confirms the DI is still active (debounce/verification).

#### Key Implementation Details
- `platform_iface.start_di_pulse_listener(pin, callback, "rising")` for each DI
- Callbacks registered in `setup()` method
- DI confirmation: `if await self.get_di(di)` inside callback
- Enable button: `self.ui.command.coerce("enabled")`
- Disable button: `self.ui.command.coerce("disabled")`
- Master reset: calls `state.clear_alarm()` or `state.clear_warning()` based on current state
- Pump reset: clears fault flag and calls `state.pump1_reset()` / `state.pump2_reset()`

#### Representative Code

```python
async def setup(self):
    self.platform_iface.start_di_pulse_listener(
        self.config.enable_button_pin.value, self.on_enable_button, "rising")
    self.platform_iface.start_di_pulse_listener(
        self.config.disable_button_pin.value, self.on_disable_button, "rising")
    self.platform_iface.start_di_pulse_listener(
        self.config.master_reset_pin.value, self.on_master_reset, "rising")

async def on_enable_button(self, di, val, dt_secs, counter, edge):
    if await self.get_di(di):
        self.ui.command.coerce("enabled")

async def on_master_reset(self, di, val, dt_secs, counter, edge):
    if await self.get_di(di):
        if self.state.state in [State.PRESSURE_HIGH_ALARM, State.DP_DT_ALARM, ...]:
            await self.state.clear_alarm()
        elif self.state.state in [State.FILTER_WARNING, State.PT_CAL_WARNING, ...]:
            await self.state.clear_warning()
```

#### Applicability Notes

All 6 DI buttons must be registered in `setup()`. The callback pattern with DI confirmation is the standard pydoover approach for physical button handling.

---

### Aspect: Tag Communication Map

#### Pattern Summary

The HPU system uses a hub-and-spoke tag communication model. Sensor apps (spokes) publish `"value"` and `"raw_value"` tags. The controller (hub) reads these via `get_tag()` with the sensor app key from config. The controller then publishes its own tags (State, Pressure, Temperature, etc.) for consumption by the local HMI app.

Tags are addressed by app instance key. The controller uses `config.Application` references to specify which sensor app instance to read from. Outbound tags from the controller use a configurable `tag_namespace`.

#### Key Implementation Details
- Inbound tags (sensor -> controller): `self.get_tag("value", self.config.pt1_app.value)`
- Outbound tags (controller -> HMI): `await self.set_tags(tags, app_key=namespace)`
- Tag names: `"value"`, `"raw_value"` (sensor), `"State"`, `"Pressure"`, `"Temperature"`, `"FilterDP"`, `"dPdt"`, `"ActivePump"`, `"Pump1Running"`, `"Pump2Running"` (controller)
- Namespace configurable via `tag_namespace` config field
- Tags updated every main loop iteration

#### Representative Code

```python
async def update_tags(self):
    ns = self.config.tag_namespace.value
    tags = {
        "State": self.state.state.value,
        "Pressure": self.pressure,
        "Temperature": self.temperature,
        "FilterDP": self.filter_dp,
        "dPdt": self.dp_dt_value,
        "ActivePump": self.state.active_pump,
        "Pump1Running": self.state.should_pump_run(1),
        "Pump2Running": self.state.should_pump_run(2),
    }
    await self.set_tags(tags, app_key=ns)
```

#### Applicability Notes

The tag map defines the complete inter-app communication contract. The sensor apps use `set_tags_async()` while the controller uses `set_tags()` with an explicit `app_key` for namespace control.

---

### Aspect: Variant Matrix

#### Pattern Summary

The HPU controller supports three variants (Basic, Standard, Full) through config flags rather than separate codebases. The `enable_pump_2` and `enable_vfd` boolean config fields control feature availability. The UI conditionally includes elements based on these flags, and the state machine logic naturally handles single-pump mode.

#### Key Implementation Details
- **Basic:** Single pump, single PT, temperature sensor, no filter DP, no VFD, master alarm only
- **Standard:** Dual pumps, dual PTs, temperature, filter DP, all 6 DI buttons, master + pump lamps
- **Full:** Everything in Standard plus VFD speed control
- Variants controlled by `enable_pump_2` (Boolean) and `enable_vfd` (Boolean) config flags
- UI `fetch()` conditionally includes elements based on config
- Single codebase for all variants
- IO pin assignments fully configurable for flexibility across hardware configurations

#### Applicability Notes

The variant matrix is handled purely through configuration. The app code should always include all variant code paths, with config flags determining runtime behavior. This avoids code branching and simplifies testing.

---

### Aspect: Application Main Loop Structure

#### Pattern Summary

The controller application's `main_loop()` follows a strict 6-step sequence each iteration: (1) read sensor values from companion app tags, (2) calculate dP/dt from rolling buffer, (3) run state machine to evaluate and transition, (4) update all output modules (DOs), (5) update UI with all live values and alarm states, (6) publish tags for inter-app communication.

The `setup()` method initializes output module instances, UI, state machine, DI pulse listeners, and the dP/dt buffer. The config is typed as `ImtexHPUConfig` for IDE autocomplete.

#### Key Implementation Details
- `loop_target_period = 1` second (configurable)
- Sensor readings stored as instance attributes (`self.pressure`, `self.temperature`, etc.)
- PT selection: PT1 preferred, PT2 fallback if PT1 disabled or None
- Output modules iterated generically: `for output in self.outputs: await output.update()`
- Alarm dict constructed from state comparisons, passed to UI update
- Tags updated last, after all processing complete

#### Representative Code

```python
async def main_loop(self):
    # 1. Read sensor values from companion app tags
    await self.read_sensors()
    # 2. Calculate dP/dt from rolling buffer
    self.calculate_dp_dt()
    # 3. Run state machine
    await self.state.spin_state()
    # 4. Update outputs
    for output in self.outputs:
        await output.update()
    # 5. Update UI
    alarms = {
        "pressure_high": self.state.state == State.PRESSURE_HIGH_ALARM,
        "dp_dt": self.state.state == State.DP_DT_ALARM,
        ...
    }
    self.ui.update(pressure=self.pressure, ...)
    # 6. Update tags for inter-app communication
    await self.update_tags()
```

#### Applicability Notes

This main loop structure should be followed exactly in the HPU controller implementation. The ordering matters: sensors must be read before state evaluation, state must be evaluated before output updates, and UI/tags are updated last.

---

### Aspect: Package Structure

#### Pattern Summary

The spec defines a well-organized package structure with clear separation of concerns. The main application package (`imtex_hpu_controller/`) contains the application class, config, UI, and state machine as top-level modules, with outputs in a sub-package. A simulators directory provides development-time simulation capability.

#### Key Implementation Details
- `src/imtex_hpu_controller/` package root
- `__init__.py` - entry point with `main()` function
- `application.py` - `ImtexHPUApplication(Application)` class
- `app_config.py` - `ImtexHPUConfig(config.Schema)` class
- `app_ui.py` - `ImtexHPUUI` class
- `app_state.py` - `ImtexHPUState` class with `State` enum
- `pressure_control.py` - pressure band control logic (optional, can be in state machine)
- `alarm_manager.py` - alarm monitoring and dP/dt detection (optional, can be in application)
- `outputs/` sub-package with `base.py`, `motor_relay.py`, `solenoid_valve.py`, `alarm_lamp.py`, `vfd_speed.py`
- `simulators/hpu_sim.py` for development testing

#### Applicability Notes

This exact structure should be used when scaffolding the HPU controller app in Phase 3. The naming convention uses underscores for the Python package (`imtex_hpu_controller`) and hyphens for the project name (`hydraulic-power-pack-control`).

---

## Extraction Metadata
- Extracted at: 2026-02-19
- References processed: 2
- References skipped: 0
