# Hydraulic Power Pack Control

<img src="https://imtex-controls.com/wp-content/uploads/2018/11/imtexcontrols-Logo-4colour.png" alt="Imtex Controls" style="max-width: 100px;">

**Hydraulic Power Unit controller for Imtex PST systems with pressure band control, redundant pump logic, and comprehensive alarm management.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/getdoover/imtex-hpu)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/getdoover/imtex-hpu/blob/main/LICENSE)

[Getting Started](#getting-started) | [Configuration](#configuration) | [Developer](https://github.com/getdoover/imtex-hpu/blob/main/DEVELOPMENT.md) | [Need Help?](#need-help)

<br/>

## Overview

The Hydraulic Power Pack Control application is a Doover Docker device app designed for Imtex PST (Partial Stroke Testing) systems. It manages the complete lifecycle of a hydraulic power unit used to actuate valves, including pressurisation control, pump management, and safety monitoring. The controller reads four 4-20mA sensor inputs via companion sensor app instances and drives digital outputs for motor relays, a solenoid valve, and an alarm lamp.

At its core the application implements a 16-state state machine that governs the HPU through disabled, idle, pressurising, pressure-OK, warning, fault, and alarm states. Pressure band control maintains system pressure between configurable upper and lower thresholds by cycling the pump motors. When the active pressure transducer (PT1) readings are unavailable or disabled, the controller automatically falls back to the redundant PT2 sensor.

The system provides multi-layered safety protection with configurable alarm thresholds for high/low pressure, rapid pressure change (dP/dt), temperature, and filter differential pressure. Redundant pump logic with automatic failover ensures that if Pump 1 faults, Pump 2 takes over after a configurable switchover delay. All alarm and fault conditions cascade into a master alarm state and illuminate the master alarm lamp. Physical DI buttons and the Doover UI both provide enable/disable, alarm clear, and pump reset controls.

### Features

- **Pressure band control** -- automatically cycles pumps to maintain system pressure between configurable upper and lower thresholds
- **Redundant pump logic** -- automatic failover from Pump 1 to Pump 2 with configurable switchover delay
- **16-state state machine** -- comprehensive state model covering operational, warning, fault, and critical alarm states
- **4x 4-20mA sensor inputs** -- reads PT1, PT2, filter DP, and temperature sensors via companion Doover sensor app tags
- **dP/dt rate-of-change detection** -- rolling buffer calculates pressure rate of change and alarms on rapid transients
- **PT calibration drift detection** -- compares PT1 and PT2 readings and warns when they diverge beyond threshold
- **Filter DP monitoring** -- warning and fail thresholds for hydraulic filter differential pressure
- **Master alarm cascading** -- all critical alarms escalate to a master alarm state with lamp output
- **Physical button I/O** -- 6 digital input listeners for enable, disable, master reset, pump resets, and PT1 toggle
- **Rich Doover UI** -- live sensor displays, alarm status submodule, adjustable threshold sliders, and control actions
- **Alert notifications** -- deduplicated alert messages sent on alarm/fault state transitions
- **Optional VFD speed feedback** -- reads 0-10V analog input for variable frequency drive speed monitoring
- **5 output modules** -- Motor 1 relay, Motor 2 relay, solenoid valve, master alarm lamp, VFD speed reader

<br/>

## Getting Started

### Prerequisites

1. A Doover device with the `platform_interface` app installed
2. Four instances of the [4-20mA Sensor](https://github.com/getdoover/4-20ma-sensor) companion app configured for PT1, PT2, filter DP, and temperature sensors (PT2 and filter DP are optional depending on your variant)
3. Hardware wiring for digital outputs (motor relays, solenoid valve, alarm lamp) and digital inputs (enable, disable, reset buttons)

### Installation

1. Add the **Hydraulic Power Pack Control** app to your Doover device from the app catalogue
2. Configure the required sensor app references (PT1 Sensor App, Temperature Sensor App) in the app settings
3. Optionally configure PT2 Sensor App and Filter DP Sensor App if your system has dual pressure transducers or filter DP monitoring
4. Set the DI and DO pin assignments to match your hardware wiring
5. Adjust pressure band thresholds, alarm thresholds, and timing parameters for your system

### Quick Start

1. Wire sensor inputs to your 4-20mA sensor app instances and verify they are reporting values
2. Add the HPU Control app and set **PT1 Sensor App** and **Temperature Sensor App** to the correct companion app instances
3. Set **Pressure Upper Band** and **Pressure Lower Band** to your desired operating range
4. Use the **HPU Command** control (or the physical enable button) to switch the system to **Enabled**
5. The controller will begin pressurising automatically when pressure drops below the lower band

<br/>

## Configuration

### Variant Flags

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable Pump 2 (Redundant)** | Enable redundant Pump 2 with automatic failover | `true` |
| **Enable VFD Speed Control** | Enable VFD speed control for motor modulation | `false` |

### Pressure Band Control

| Setting | Description | Default |
|---------|-------------|---------|
| **Pressure Upper Band (bar)** | Upper pressure threshold (bar) to stop pumping. Range 0-500. | `200.0` |
| **Pressure Lower Band (bar)** | Lower pressure threshold (bar) to start pumping. Range 0-500. | `180.0` |

### Alarm Thresholds

| Setting | Description | Default |
|---------|-------------|---------|
| **Pressure High Alarm (bar)** | Pressure high alarm threshold (bar). Critical alarm. | `250.0` |
| **Pressure Low Alarm (bar)** | Pressure low alarm threshold (bar). Critical alarm. | `50.0` |
| **dP/dt Alarm Threshold (bar/s)** | Rate of pressure change alarm threshold (bar/s). Critical alarm. | `10.0` |
| **dP/dt Buffer Size** | Number of samples in dP/dt rolling buffer. Range 3-20. | `5` |
| **PT Calibration Drift Threshold (bar)** | Maximum allowed difference between PT1 and PT2 readings (bar). Warning. | `5.0` |
| **Filter DP Warning (bar)** | Filter differential pressure warning threshold (bar). Warning. | `2.0` |
| **Filter DP Fail (bar)** | Filter differential pressure fail threshold (bar). Critical alarm. | `4.0` |
| **Temperature High Warning** | Temperature high warning threshold. Warning. | `60.0` |
| **Temperature High Alarm** | Temperature high alarm threshold. Critical alarm. | `80.0` |

### Alarm Timing

| Setting | Description | Default |
|---------|-------------|---------|
| **Alarm Grace Period (s)** | Seconds threshold must be sustained before alarm fires | `5.0` |
| **Min Inter-Alarm Interval (s)** | Minimum seconds between repeated alarm triggers | `60.0` |

### Pump Timing

| Setting | Description | Default |
|---------|-------------|---------|
| **Pump Start Delay (s)** | Delay in seconds before starting pump after command | `2.0` |
| **Pump Switchover Delay (s)** | Delay in seconds before backup pump takes over after primary fault | `5.0` |

### Sensor App References

| Setting | Description | Default |
|---------|-------------|---------|
| **PT1 Sensor App** | PT1 pressure sensor app instance reference | *Required* |
| **PT2 Sensor App** | PT2 pressure sensor app instance reference (if dual PT) | `null` |
| **Filter DP Sensor App** | Filter differential pressure sensor app instance reference | `null` |
| **Temperature Sensor App** | Temperature sensor app instance reference | *Required* |

### Digital Input Pin Assignments

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable Button DI Pin** | Digital input pin for system enable button | `0` |
| **Disable Button DI Pin** | Digital input pin for system disable button | `1` |
| **Master Reset DI Pin** | Digital input pin for master alarm reset button | `2` |
| **Pump 1 Reset DI Pin** | Digital input pin for pump 1 fault reset button | `3` |
| **Pump 2 Reset DI Pin** | Digital input pin for pump 2 fault reset button | `4` |
| **PT1 Enable DI Pin** | Digital input pin for PT1 enable/disable toggle | `5` |

### VFD Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **VFD Feedback AI Pin** | Analog input pin for VFD speed feedback (0-10V) | `0` |
| **VFD Minimum Speed (%)** | Minimum VFD speed percentage | `10.0` |

### Digital Output Pin Assignments

| Setting | Description | Default |
|---------|-------------|---------|
| **Motor 1 Relay DO Pin** | DO pin for Motor 1 relay output | `0` |
| **Motor 2 Relay DO Pin** | DO pin for Motor 2 relay output | `1` |
| **Solenoid Valve DO Pin** | DO pin for solenoid valve output | `2` |
| **Master Alarm Lamp DO Pin** | DO pin for master alarm lamp output | `3` |

### Other

| Setting | Description | Default |
|---------|-------------|---------|
| **Tag Namespace** | Optional namespace for outbound tags | `null` |

### Example Configuration

```json
{
  "enable_pump_2_(redundant)": true,
  "enable_vfd_speed_control": false,
  "pressure_upper_band_(bar)": 200.0,
  "pressure_lower_band_(bar)": 180.0,
  "pressure_high_alarm_(bar)": 250.0,
  "pressure_low_alarm_(bar)": 50.0,
  "dp/dt_alarm_threshold_(bar/s)": 10.0,
  "dp/dt_buffer_size": 5,
  "pt_calibration_drift_threshold_(bar)": 5.0,
  "filter_dp_warning_(bar)": 2.0,
  "filter_dp_fail_(bar)": 4.0,
  "temperature_high_warning": 60.0,
  "temperature_high_alarm": 80.0,
  "alarm_grace_period_(s)": 5.0,
  "min_inter-alarm_interval_(s)": 60.0,
  "pump_start_delay_(s)": 2.0,
  "pump_switchover_delay_(s)": 5.0,
  "pt1_sensor_app": "<pt1-app-instance-id>",
  "temperature_sensor_app": "<temp-app-instance-id>"
}
```

<br/>

## UI Elements

This application provides a comprehensive Doover UI for monitoring and controlling the HPU.

### State Commands

| Element | Description |
|---------|-------------|
| **HPU Command** | Enable or disable the HPU system. Options: `Enabled`, `Disabled`. |

### Variables (Display)

| Element | Description |
|---------|-------------|
| **System State** | Current state machine state (e.g. IDLE, PRESSURISING, PRESSURE OK, MASTER ALARM) |
| **System Pressure (bar)** | Live pressure reading from the active pressure transducer. Colour-coded: red 0-50, green 50-250, red 250-500. |
| **Active Pump** | Which pump is currently designated as active (Pump 1 or Pump 2) |
| **Pump 1 Running** | Whether Pump 1 motor relay is currently energised |
| **Pump 2 Running** | Whether Pump 2 motor relay is currently energised (shown when Pump 2 enabled) |
| **Temperature** | Live temperature sensor reading |
| **Filter DP (bar)** | Live filter differential pressure reading |
| **dP/dt (bar/s)** | Calculated rate of pressure change from rolling buffer |
| **VFD Speed (%)** | VFD speed feedback as percentage (shown when VFD enabled) |

### Alarm Status (Submodule)

| Element | Description |
|---------|-------------|
| **Pressure High Alarm** | True when system pressure exceeds the high alarm threshold |
| **Pressure Low Alarm** | True when system pressure drops below the low alarm threshold |
| **dP/dt Alarm** | True when rate of pressure change exceeds the dP/dt threshold |
| **Temperature High Warning** | True when temperature exceeds the warning threshold |
| **Temperature High Alarm** | True when temperature exceeds the alarm threshold |
| **Filter DP Warning** | True when filter DP exceeds the warning threshold |
| **Filter DP Fail** | True when filter DP exceeds the fail threshold |
| **PT Cal Drift Warning** | True when PT1 and PT2 readings diverge beyond the drift threshold |
| **Pump 1 Fault** | True when Pump 1 has faulted |
| **Pump 2 Fault** | True when Pump 2 has faulted |
| **Master Alarm** | True when the system is in the master alarm state |

### Alarm Settings (Submodule -- Parameters)

| Element | Range | Step | Default |
|---------|-------|------|---------|
| **Pressure Upper Band (bar)** | 0 -- 500 | 1 | 200 |
| **Pressure Lower Band (bar)** | 0 -- 500 | 1 | 180 |
| **Pressure High Alarm (bar)** | 0 -- 500 | 1 | 250 |
| **dP/dt Alarm Threshold (bar/s)** | 0 -- 50 | 0.5 | 10 |
| **Filter DP Warning (bar)** | 0 -- 10 | 0.1 | 2.0 |
| **Filter DP Fail (bar)** | 0 -- 10 | 0.1 | 4.0 |
| **Temp High Warning** | 0 -- 150 | 1 | 60 |
| **Temp High Alarm** | 0 -- 150 | 1 | 80 |

### Actions (Buttons)

| Element | Description |
|---------|-------------|
| **Clear Alarm** | Clear a critical alarm and return to IDLE (requires confirmation). Available in alarm states. |
| **Clear Warning** | Clear a warning and return to IDLE. Available in warning states. |
| **Reset Pump 1** | Reset Pump 1 fault and return to IDLE (requires confirmation). Available when in Pump 1 Fault state. |
| **Reset Pump 2** | Reset Pump 2 fault and return to IDLE (requires confirmation). Available when in Pump 2 Fault state. Shown when Pump 2 is enabled. |

<br/>

## Tags

This application publishes the following tags for inter-app communication and dashboard use:

| Tag | Description |
|-----|-------------|
| **State** | Current state machine state string (e.g. `idle`, `pressurising`, `master_alarm`) |
| **Pressure** | Active system pressure reading (bar) from PT1 or PT2 fallback |
| **Temperature** | Current temperature sensor reading |
| **FilterDP** | Current filter differential pressure reading (bar) |
| **dPdt** | Calculated rate of pressure change (bar/s) |
| **ActivePump** | Currently active pump number (1 or 2) |
| **Pump1Running** | Whether Pump 1 is currently running (boolean) |
| **Pump2Running** | Whether Pump 2 is currently running (boolean) |

<br/>

## How It Works

1. **Sensor Reading** -- On each 1 Hz control loop iteration, the application reads live values from four companion 4-20mA sensor apps (PT1, PT2, filter DP, temperature) via Doover inter-app tags. PT1 is the preferred pressure source with automatic fallback to PT2 if PT1 is disabled or unavailable.

2. **dP/dt Calculation** -- The current pressure reading is appended to a rolling buffer (configurable size, default 5 samples). The rate of pressure change (dP/dt) is calculated as the slope between the oldest and newest samples in the buffer.

3. **State Machine Evaluation** -- The 16-state state machine evaluates all sensor values against configured thresholds. Critical alarms (pressure high/low, dP/dt, temperature) are checked first and can fire from any enabled state. Warning conditions (filter DP, temperature, PT calibration drift) are checked from operational states. Pump faults trigger automatic failover to the backup pump after a configurable delay. All critical alarms cascade into the master alarm state.

4. **Output Module Updates** -- Five output modules are updated based on the current state: Motor 1 relay (energised when Pump 1 should run), Motor 2 relay (energised when Pump 2 should run, if enabled), solenoid valve (energised in operational/warning states, de-energised in alarms), master alarm lamp (energised in any alarm or fault state), and VFD speed reader (reads analog feedback when VFD is enabled).

5. **UI Update** -- All UI elements are refreshed with current sensor values, pump status, active state, and alarm indicator flags. Alarm alert notifications are sent on state transitions with deduplication to prevent repeated alerts.

6. **Tag Publishing** -- The controller publishes its current state, sensor values, and pump status as Doover tags for consumption by other apps or dashboards.

<br/>

## Integrations

This device app works with:

- **[4-20mA Sensor App](https://github.com/getdoover/4-20ma-sensor)** -- Four companion instances provide calibrated sensor readings (PT1, PT2, filter DP, temperature) via inter-app tag communication
- **Doover Platform Interface** -- Provides digital I/O (DI pulse listeners, DO relay control, AI voltage reading) and tag infrastructure
- **Physical I/O Hardware** -- Motor contactors/relays, solenoid valve, alarm lamp, and momentary push buttons connected via digital I/O pins
- **Doover Dashboard** -- Published tags enable real-time monitoring and historical data visualisation

<br/>

## Need Help?

- Email: support@doover.com
- [Doover Documentation](https://docs.doover.com)
- [App Developer Documentation](https://github.com/getdoover/imtex-hpu/blob/main/DEVELOPMENT.md)

<br/>

## Version History

### v0.1.0 (Current)
- Initial release
- 16-state state machine for complete HPU lifecycle management
- Pressure band control with configurable upper/lower thresholds
- Redundant pump logic with automatic failover and configurable switchover delay
- 4x 4-20mA sensor input support via companion app tag communication
- dP/dt rolling buffer rate-of-change detection
- PT calibration drift detection between dual pressure transducers
- Filter differential pressure warning and fail monitoring
- Temperature warning and alarm thresholds
- Master alarm cascading from all critical alarm states
- 5 output modules: Motor 1 relay, Motor 2 relay, solenoid valve, alarm lamp, VFD speed
- 6 digital input listeners for physical buttons
- Comprehensive Doover UI with alarm status submodule and adjustable threshold sliders
- Alert notification system with deduplication

<br/>

## License

This app is licensed under the [Apache License 2.0](https://github.com/getdoover/imtex-hpu/blob/main/LICENSE).
