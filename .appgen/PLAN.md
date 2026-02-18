# Build Plan

## App Summary
- Name: hydraulic-power-pack-control
- Type: docker
- Description: Hydraulic Power Unit controller for Imtex PST systems. Controls hydraulic actuator valve actuation with 4x 4-20mA sensor inputs, pressure band control, redundant pump logic, and alarm management.
- Package Name: `imtex_hpu_controller`
- Has UI: true

## External Integration
- Service: None (communicates with companion 4-20mA sensor apps via Doover tag system)
- Documentation: N/A
- Authentication: N/A

## Data Flow
- **Inputs:**
  - 4x sensor tag values from companion 4-20mA sensor app instances (PT1 pressure, PT2 pressure, filter DP, temperature) via `get_tag("value", app_key)`
  - 6x digital inputs via `platform_iface` for physical buttons (enable, disable, master reset, pump 1 reset, pump 2 reset, PT1 enable)
  - VFD feedback voltage (0-10V analog input) via `platform_iface.get_ai()` (Full variant only)
  - UI commands (enable/disable StateCommand, alarm clear actions, slider parameter changes)
- **Processing:**
  - State machine evaluation (16 states covering operational lifecycle, pump faults, warnings, and alarms)
  - Pressure band hysteresis control (start pump below lower band, stop pump above upper band)
  - dP/dt rate-of-change detection via rolling buffer
  - PT calibration drift detection (PT1 vs PT2 comparison)
  - Filter DP monitoring (warning and fail thresholds)
  - Redundant pump failover logic with configurable switchover delay
  - Master alarm cascading from critical alarm conditions
- **Outputs:**
  - Digital outputs via `platform_iface.set_do()`: Motor 1 relay, Motor 2 relay, solenoid valve, master alarm lamp
  - UI updates: live sensor values, pump status, alarm indicators, system state
  - Tags for inter-app communication: State, Pressure, Temperature, FilterDP, dPdt, ActivePump, Pump1Running, Pump2Running
  - Alert notifications for alarm conditions

## Configuration Schema

### Variant Flags
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| enable_pump_2 | Boolean | no | true | Enable redundant Pump 2 with automatic failover |
| enable_vfd | Boolean | no | false | Enable VFD speed control for motor modulation |

### Pressure Band Control
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| pressure_upper_band | Number | no | 200.0 | Upper pressure threshold (bar) to stop pumping. Range 0-500. |
| pressure_lower_band | Number | no | 180.0 | Lower pressure threshold (bar) to start pumping. Range 0-500. |

### Alarm Thresholds
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| pressure_high_alarm | Number | no | 250.0 | Pressure high alarm threshold (bar). Critical alarm. |
| pressure_low_alarm | Number | no | 50.0 | Pressure low alarm threshold (bar). Critical alarm. |
| dp_dt_alarm_threshold | Number | no | 10.0 | Rate of pressure change alarm threshold (bar/s). Critical alarm. |
| dp_dt_buffer_size | Integer | no | 5 | Number of samples in dP/dt rolling buffer. Range 3-20. |
| pt_cal_drift_threshold | Number | no | 5.0 | Maximum allowed difference between PT1 and PT2 readings (bar). Warning. |
| filter_dp_warning | Number | no | 2.0 | Filter differential pressure warning threshold (bar). Warning. |
| filter_dp_fail | Number | no | 4.0 | Filter differential pressure fail threshold (bar). Critical alarm. |
| temp_high_warning | Number | no | 60.0 | Temperature high warning threshold. Warning. |
| temp_high_alarm | Number | no | 80.0 | Temperature high alarm threshold. Critical alarm. |

### Alarm Timing
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| alarm_grace_period | Number | no | 5.0 | Seconds threshold must be sustained before alarm fires |
| alarm_min_inter_alarm | Number | no | 60.0 | Minimum seconds between repeated alarm triggers |

### Pump Timing
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| pump_start_delay | Number | no | 2.0 | Delay in seconds before starting pump after command |
| pump_switchover_delay | Number | no | 5.0 | Delay in seconds before backup pump takes over after primary fault |

### Sensor App References
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| pt1_app | Application | yes | - | PT1 pressure sensor app instance reference |
| pt2_app | Application | no | - | PT2 pressure sensor app instance reference (if dual PT) |
| dp_app | Application | no | - | Filter differential pressure sensor app instance reference |
| temp_app | Application | yes | - | Temperature sensor app instance reference |

### DI Pin Assignments
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| enable_button_pin | Integer | no | 0 | Digital input pin for system enable button |
| disable_button_pin | Integer | no | 1 | Digital input pin for system disable button |
| master_reset_pin | Integer | no | 2 | Digital input pin for master alarm reset button |
| pump1_reset_pin | Integer | no | 3 | Digital input pin for pump 1 fault reset button |
| pump2_reset_pin | Integer | no | 4 | Digital input pin for pump 2 fault reset button |
| pt1_enable_pin | Integer | no | 5 | Digital input pin for PT1 enable/disable toggle |

### VFD Configuration (Full variant)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| vfd_feedback_pin | Integer | no | 0 | Analog input pin for VFD speed feedback (0-10V) |
| vfd_min_speed | Number | no | 10.0 | Minimum VFD speed percentage |

### Output Module Configs (registered dynamically)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| motor_1_relay_pin | Integer | no | 0 | DO pin for Motor 1 relay output |
| motor_2_relay_pin | Integer | no | 1 | DO pin for Motor 2 relay output |
| solenoid_valve_pin | Integer | no | 2 | DO pin for solenoid valve output |
| master_alarm_lamp_pin | Integer | no | 3 | DO pin for master alarm lamp output |

### Tag Namespace
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| tag_namespace | String | no | null | Optional namespace for outbound tags |

## UI Elements

### Variables (Display)
| Name | Key | Type | Description |
|------|-----|------|-------------|
| System Pressure (bar) | pressure | NumericVariable (precision=1) | Active pressure reading from selected PT sensor |
| System State | system_state | TextVariable | Current state machine state as human-readable string |
| Active Pump | active_pump | TextVariable | Which pump is currently designated (1 or 2) |
| Pump 1 Running | pump1_running | BooleanVariable | Whether Pump 1 motor relay is energized |
| Pump 2 Running | pump2_running | BooleanVariable | Whether Pump 2 motor relay is energized (conditional on enable_pump_2) |
| Temperature | temperature | NumericVariable (precision=1) | Current temperature reading |
| Filter DP (bar) | filter_dp | NumericVariable (precision=2) | Current filter differential pressure |
| dP/dt (bar/s) | dp_dt | NumericVariable (precision=2) | Current rate of pressure change |
| VFD Speed (%) | vfd_speed | NumericVariable (precision=1) | Current VFD motor speed percentage (conditional on enable_vfd) |

### Alarm Status Submodule
| Name | Key | Type | Description |
|------|-----|------|-------------|
| Pressure High Alarm | alarm_pressure_high | BooleanVariable | True when in PRESSURE_HIGH_ALARM state |
| Pressure Low Alarm | alarm_pressure_low | BooleanVariable | True when in PRESSURE_LOW_ALARM state |
| dP/dt Alarm | alarm_dp_dt | BooleanVariable | True when in DP_DT_ALARM state |
| Temperature High Warning | alarm_temp_warning | BooleanVariable | True when in TEMP_HIGH_WARNING state |
| Temperature High Alarm | alarm_temp_alarm | BooleanVariable | True when in TEMP_HIGH_ALARM state |
| Filter DP Warning | alarm_filter_warning | BooleanVariable | True when in FILTER_WARNING state |
| Filter DP Fail | alarm_filter_fail | BooleanVariable | True when in FILTER_FAIL state |
| PT Cal Drift Warning | alarm_pt_cal_drift | BooleanVariable | True when in PT_CAL_WARNING state |
| Pump 1 Fault | alarm_pump1_fault | BooleanVariable | True when in PUMP1_FAULT state |
| Pump 2 Fault | alarm_pump2_fault | BooleanVariable | True when in PUMP2_FAULT state |
| Master Alarm | alarm_master | BooleanVariable | True when in MASTER_ALARM state |

### Parameters (User Input) - Alarm Settings Submodule
| Name | Key | Type | Default | Description |
|------|-----|------|---------|-------------|
| Pressure Upper Band (bar) | pressure_upper_band | Slider (0-500, step=1) | 200 | Adjustable upper pressure threshold |
| Pressure Lower Band (bar) | pressure_lower_band | Slider (0-500, step=1) | 180 | Adjustable lower pressure threshold |
| Pressure High Alarm (bar) | pressure_high_alarm_setting | Slider (0-500, step=1) | 250 | Adjustable pressure high alarm threshold |
| dP/dt Alarm Threshold (bar/s) | dp_dt_alarm_setting | Slider (0-50, step=0.5) | 10 | Adjustable rate of change threshold |
| Filter DP Warning (bar) | filter_dp_warning_setting | Slider (0-10, step=0.1) | 2.0 | Adjustable filter DP warning threshold |
| Filter DP Fail (bar) | filter_dp_fail_setting | Slider (0-10, step=0.1) | 4.0 | Adjustable filter DP fail threshold |
| Temp High Warning | temp_high_warning_setting | Slider (0-150, step=1) | 60 | Adjustable temperature warning threshold |
| Temp High Alarm | temp_high_alarm_setting | Slider (0-150, step=1) | 80 | Adjustable temperature alarm threshold |

### Actions (Commands)
| Name | Key | Type | Description |
|------|-----|------|-------------|
| HPU Command | command | StateCommand (disabled/enabled) | Enable or disable the HPU system |
| Clear Alarm | clear_alarm | Action (red, confirm) | Manually clear active alarm and return to IDLE |
| Clear Warning | clear_warning | Action | Manually clear active warning |
| Reset Pump 1 | reset_pump1 | Action (confirm) | Reset Pump 1 fault flag |
| Reset Pump 2 | reset_pump2 | Action (confirm) | Reset Pump 2 fault flag (conditional on enable_pump_2) |

### Alert Notifications
| Name | Key | Type | Description |
|------|-----|------|-------------|
| Notifications | notifications | AlertStream | Sends alert notifications for alarm events with deduplication |

## State Machine

### States (16 total)
| State | Type | Description |
|-------|------|-------------|
| DISABLED | Control | System disabled, all outputs off |
| IDLE | Operational | Enabled but pressure within band, pumps off |
| PRESSURISING | Operational | Pump running to build pressure |
| PRESSURE_OK | Operational | Pressure within upper band, pump stopped |
| PUMP1_FAULT | Fault | Pump 1 faulted, auto-switchover to pump 2 if available |
| PUMP2_FAULT | Fault | Pump 2 faulted |
| BOTH_PUMPS_FAULT | Critical | Both pumps faulted, master alarm |
| PT_CAL_WARNING | Warning | PT1/PT2 calibration drift detected |
| FILTER_WARNING | Warning | Filter DP above warning threshold |
| FILTER_FAIL | Critical | Filter DP above fail threshold |
| TEMP_HIGH_WARNING | Warning | Temperature above warning threshold |
| TEMP_HIGH_ALARM | Critical | Temperature above alarm threshold |
| PRESSURE_HIGH_ALARM | Critical | Pressure above high alarm threshold |
| PRESSURE_LOW_ALARM | Critical | Pressure below low alarm threshold (unexpected) |
| DP_DT_ALARM | Critical | Rapid pressure change detected (leak/burst) |
| MASTER_ALARM | Critical | Catch-all critical alarm state |

### Key Transitions
- `enable`: DISABLED -> IDLE
- `disable`: * -> DISABLED
- `pressure_low`: IDLE/PRESSURE_OK -> PRESSURISING
- `pressure_ok`: PRESSURISING -> PRESSURE_OK
- `pump1_fault`: operational states -> PUMP1_FAULT
- `pump2_fault`: operational states -> PUMP2_FAULT
- `pressure_high_alarm`: * -> PRESSURE_HIGH_ALARM
- `dp_dt_alarm`: * -> DP_DT_ALARM
- `temp_high_alarm`: * -> TEMP_HIGH_ALARM
- `filter_fail`: operational states -> FILTER_FAIL
- `master_alarm`: critical states -> MASTER_ALARM
- `clear_alarm`: alarm states -> IDLE
- `clear_warning`: warning states -> IDLE (or previous operational state)

## Package Structure

```
hydraulic-power-pack-control/
├── src/imtex_hpu_controller/
│   ├── __init__.py              # Entry point: main() -> run_app(...)
│   ├── application.py           # ImtexHPUApplication(Application)
│   ├── app_config.py            # ImtexHPUConfig(config.Schema) + export()
│   ├── app_ui.py                # ImtexHPUUI class
│   ├── app_state.py             # ImtexHPUState class with State enum
│   └── outputs/
│       ├── __init__.py           # AVAILABLE_OUTPUTS list, ControllerOutput export
│       ├── base.py               # ControllerOutput ABC
│       ├── motor_relay.py        # Motor1RelayOutput, Motor2RelayOutput
│       ├── solenoid_valve.py     # SolenoidValveOutput
│       ├── alarm_lamp.py         # MasterAlarmLampOutput
│       └── vfd_speed.py          # VFDSpeedOutput (optional variant)
├── simulators/
│   ├── sample/
│   │   ├── main.py               # Simulator publishing fake sensor tags
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── docker-compose.yml
│   └── app_config.json
├── tests/
│   ├── __init__.py
│   └── test_imports.py
├── doover_config.json
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Documentation Chunks

### Required Chunks
- `config-schema.md` - Configuration types and patterns (Application refs, Boolean, Number, Integer, Enum)
- `docker-application.md` - Application class structure (setup, main_loop, ui.callback, loop control)
- `docker-project.md` - Entry point, Dockerfile, pyproject.toml, simulators, testing

### Recommended Chunks
- `docker-ui.md` - UI components: StateCommand, NumericVariable, BooleanVariable, TextVariable, Slider, Submodule, Action, AlertStream, WarningIndicator, Range coloring
- `docker-advanced.md` - State machines (StateMachine, evaluate_state, spin_state, queued transitions, timeouts), hardware I/O (platform_iface, DI pulse listeners, DO control, AI reading), rolling statistics (deque), debounced input
- `tags-channels.md` - Tag reading from companion apps (get_tag with app_key), tag publishing (set_tags), channel publishing for logging/debug

### Discovery Keywords
pressure, pump, motor, relay, solenoid, valve, alarm, lamp, state machine, transition, hysteresis, band, threshold, dP/dt, rate of change, calibration, drift, filter, differential, temperature, VFD, speed, digital input, button, callback, DI, DO, analog, 4-20mA, sensor, tag, redundant, failover, switchover, deque, rolling buffer, warning, fault, master alarm, cascade

## Reference Patterns Applied

| Pattern | Source Aspect | How Applied |
|---------|--------------|-------------|
| Tag Communication | Ref 1: Tag Communication Patterns | Controller reads `"value"` tag from 4 companion sensor apps via `get_tag("value", self.config.pt1_app.value)`. Config uses `config.Application` for sensor app references. |
| Sensor Interface Contract | Ref 1: Sensor Reading Interface | Controller does not read analog sensors directly (except VFD feedback). Understands the `"value"` and `"raw_value"` tag contract from sensor apps. Handles None gracefully during sensor initialization. |
| Alarm with Grace Period | Ref 1: Alarm Handling | Alarm class pattern with `grace_period` and `min_inter_alarm` applied to all alarm conditions. Prevents false alarms from transient pressure spikes during pump cycling. |
| App Structure | Ref 1: App Structure & Architecture | Same `src/` layout, hatchling build, `run_app()` entry point, config export pattern, Dockerfile multi-stage with uv. Extended with outputs sub-package. |
| State Machine Design | Ref 2: State Machine Design | 16-state flat state machine using `pydoover.state.StateMachine` with `queued=True`. `State` enum, `evaluate_state()`, `spin_state()` pattern. Critical alarms from `"*"`, warnings from operational states only. |
| Config Schema Pattern | Ref 2: Config Schema | Extensive config with variant flags, alarm thresholds, DI pins, sensor app refs, pump timing. Dynamic output config registration via `get_config_element()`. |
| UI Definition | Ref 2: UI Definition | StateCommand for enable/disable, NumericVariable for live values, BooleanVariable for pump/alarm status, Slider for threshold adjustment, Submodules for grouping. Conditional elements based on variant config. |
| Output Module Registry | Ref 2: Output Modules | Abstract `ControllerOutput` base class with `AVAILABLE_OUTPUTS` registry. Each output has `get_config_element()`, `update()`, `on_state_change()`. Motor relay checks `should_pump_run()`, SOV checks not in critical states, alarm lamp checks alarm states list. |
| Pressure Band Control | Ref 2: Pressure Band Control | Simple hysteresis on/off with `pressure_lower_band` (start) and `pressure_upper_band` (stop). State machine transitions handle the logic. |
| Redundant Pump Logic | Ref 2: Redundant Pump Logic | `enable_pump_2` config flag. `should_pump_run(pump_number)` and `active_pump` property on state machine. Auto-switchover with configurable delay. Reset via DI or UI. |
| dP/dt Detection | Ref 2: dP/dt Rate of Change | `collections.deque(maxlen=buffer_size)` with `(timestamp, pressure)` tuples. Calculate `(P_new - P_old) / (T_new - T_old)`. Absolute value compared to threshold. |
| PT Cal Drift | Ref 2: PT Calibration Drift | `abs(pt1 - pt2) > threshold` check when both readings valid. Warning only (not critical). PT1 preferred, PT2 fallback. |
| Filter DP Monitoring | Ref 2: Filter DP Monitoring | Two-tier thresholds: warning (notification) and fail (shutdown + master alarm). DP from companion sensor app. |
| Master Alarm Cascade | Ref 2: Master Alarm Cascading | Single physical alarm lamp DO. Multiple alarm conditions cascade into master alarm. Manual reset required via DI or UI. |
| DI Button Callbacks | Ref 2: DI Button Callbacks | `platform_iface.start_di_pulse_listener(pin, callback, "rising")` registered in `setup()`. DI confirmation inside callback. Enable/disable via `ui.command.coerce()`. Reset triggers state machine transitions. |
| Tag Map | Ref 2: Tag Communication Map | Outbound tags: State, Pressure, Temperature, FilterDP, dPdt, ActivePump, Pump1Running, Pump2Running. Optional namespace via config. |
| Variant Matrix | Ref 2: Variant Matrix | Single codebase, three variants (Basic/Standard/Full) controlled by `enable_pump_2` and `enable_vfd` boolean config flags. UI `fetch()` conditionally includes elements. |
| Main Loop Structure | Ref 2: Application Main Loop | Strict 6-step sequence: (1) read sensors, (2) calculate dP/dt, (3) spin state machine, (4) update outputs, (5) update UI, (6) publish tags. |

## Implementation Notes

### Key Patterns to Follow
- Application class typed as `config: ImtexHPUConfig` for IDE autocomplete
- `loop_target_period = 1` second (1 Hz control loop)
- State machine uses `queued=True` for deterministic transition ordering
- `spin_state()` loop ensures state stabilization before proceeding to outputs
- Output modules iterated generically via `AVAILABLE_OUTPUTS` registry
- UI elements conditionally included in `fetch()` based on variant config flags
- DI pulse listeners registered in `setup()` with rising-edge detection
- All sensor tag reads must handle `None` gracefully (sensor not yet initialized or app offline)
- PT selection: PT1 preferred, PT2 fallback if PT1 disabled or returns None
- Alarm deduplication using `active_alerts` set pattern from docker-ui.md
- Alert notifications sent via `AlertStream` for alarm state transitions
- `on_state_change()` callback on state machine notifies all output modules

### External Packages Needed
- `pydoover>=0.4.13` - Core framework (Application, config, ui, state, platform_iface)
- `transitions>=0.9.2` - State machine library (used internally by pydoover.state.StateMachine)

### Special Considerations
- The controller does NOT read 4-20mA sensors directly. It relies on companion sensor app instances. The only direct hardware I/O is: DI buttons (6x), DO outputs (4x), and optionally AI for VFD feedback (1x).
- The state machine has 16 states with complex transition rules. Critical alarms can trigger from any state (`source: "*"`), while warnings only trigger from operational states.
- Pressure band control is simple hysteresis (on/off), not PID. The VFD variant may add PID targeting band midpoint but the basic pattern is on/off.
- The `outputs/` sub-package uses an abstract base class pattern with a registry list (`AVAILABLE_OUTPUTS`). Each output module provides its own config element via `get_config_element()`.
- Config schema is large (~30+ fields). The dynamic output config registration pattern keeps the main config class clean.
- Master alarm is the single physical alarm output. Virtual alarm indicators in the UI provide specificity.
- Manual reset required for all alarm and fault states (no auto-clear).

### Main Loop Interval
- Recommended: 1.0 second (`loop_target_period = 1`)
- This provides responsive pressure control while matching the sensor app update rate (0.5s per sensor instance)

### Dependencies Configuration (doover_config.json)
- `depends_on`: `["platform_interface"]` for DI/DO/AI hardware access
