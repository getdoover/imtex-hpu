# AppGen State

## Current Phase
Phase 6 - Document

## Status
completed

## App Details
- **Name:** hydraulic-power-pack-control
- **Description:** Hydraulic Power Unit controller for Imtex PST systems. Controls hydraulic actuator valve actuation with 4x 4-20mA sensor inputs, pressure band control, redundant pump logic, and alarm management.
- **App Type:** docker
- **Has UI:** true
- **Container Registry:** ghcr.io/getdoover
- **Target Directory:** /Users/jarrod/Documents/span/apps/hydraulic-power-pack-control
- **GitHub Repo:** getdoover/imtex-hpu
- **Repo Visibility:** public
- **GitHub URL:** https://github.com/getdoover/imtex-hpu
- **Icon URL:** https://imtex-controls.com/wp-content/uploads/2018/11/imtexcontrols-Logo-4colour.png

## Completed Phases
- [x] Phase 1: Creation - 2026-02-19
- [x] Phase 2: Docker Config - 2026-02-19 (UI kept, doover_config.json restructured for Docker device app)
- [x] Phase R: References - 2026-02-19 (REFERENCES.md created with patterns from 2 references)
- [x] Phase 3: Docker Plan - 2026-02-19 (PLAN.md created with complete build plan, no ambiguity, no user questions needed)
- [x] Phase 4: Docker Build - 2026-02-19 (Full application code generated: 16-state state machine, 5 output modules, comprehensive UI with alarm submodules, 6 DI listeners, tag-based sensor communication, dP/dt rolling buffer, all tests passing)
- [x] Phase 5: Docker Check - 2026-02-19 (All 5 validation checks passed: uv sync, imports, config schema export, file structure, tests 6/6)
- [x] Phase 6: Document - 2026-02-19 (README.md generated with all required sections: Overview, Features, Getting Started, Configuration (31 settings), UI Elements (9 variables, 11 alarm indicators, 8 sliders, 5 actions/commands), Tags (8), How It Works, Integrations, Version History)

## References
- **Has References:** true

### Reference 1
- **Location:** /Users/jarrod/Documents/span/apps/4-20ma-sensor
- **Type:** local
- **Extract:** Companion sensor app pattern. This app runs in parallel with x4 instances of the 4-20mA sensor app, communicating via tags. Extract tag communication patterns, sensor reading interface, alarm handling, and app structure.

### Reference 2
- **Location:** /Users/jarrod/Documents/master-vault/01-Customers/Imtex/imtex-hpu-doover-spec.md
- **Type:** local
- **Extract:** Complete HPU controller specification including: state machine design, config schema, UI definition, output modules (motor relays, solenoid valve, alarm lamp), pressure band control logic, redundant pump logic, dP/dt rate of change detection, PT calibration drift detection, filter DP monitoring, master alarm cascading, DI button callbacks, tag communication map, and variant matrix.

## User Decisions
- App name: hydraulic-power-pack-control
- Description: Hydraulic Power Unit controller for Imtex PST systems
- GitHub repo: getdoover/imtex-hpu
- App type: docker
- Has UI: true
- Has references: true
- Icon URL: https://imtex-controls.com/wp-content/uploads/2018/11/imtexcontrols-Logo-4colour.png

## Validation Results (Phase 5)

| Check | Status | Notes |
|-------|--------|-------|
| Dependencies (uv sync) | PASS | Resolved 25 packages, audited 24 packages |
| Imports | PASS | `from hydraulic_power_pack_control.application import *` succeeds |
| Config Schema (export-config) | PASS | Exports valid JSON to doover_config.json |
| File Structure | PASS | All expected files present: __init__.py, application.py, app_config.py, app_ui.py, app_state.py, outputs/ |
| Tests (pytest) | PASS | 6/6 tests passed (test_import_app, test_config, test_ui, test_state, test_outputs, test_state_enum) |

## Next Action
Phase 6 complete. README.md generated. Application is fully documented and ready for deployment.
