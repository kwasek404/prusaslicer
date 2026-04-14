# AGENTS.md

## Purpose

Personal PrusaSlicer + Klipper configuration for a Creality Ender-3 with BLTouch. No source code, no build system, no CI - this is a dotfiles-style repo of INI profiles and Klipper firmware config, symlinked into `~/.config/PrusaSlicer/` (Linux) or `%APPDATA%\PrusaSlicer` (Windows). See `README.md` for installation.

## Hardware

Heavily modified Creality Ender-3, cartesian kinematics.

| Component | Details |
|---|---|
| **Board** | Creality v4.2.7 (STM32F103), stock A4988 stepper drivers (no TMC2209) |
| **Firmware** | Klipper via USB serial |
| **X-axis** | V-slot with rubber rollers. Known bent/warped gantry bar causing 0.1-0.3mm left-to-right deviation after CRTouch compensation. Compensated via `[axis_twist_compensation]` |
| **Y-axis** | V-slot with rubber rollers |
| **Z-axis** | Dual independent leadscrews, single stepper driver signal (no independent Z control). Manually synchronized periodically |
| **Belts** | Non-original GT2, similar to OEM spec |
| **Extruder** | Ender3 CR10 Redrex Dual Gear (BMG-style clone) |
| **Bowden tube** | ~30cm length, cannot be shortened further |
| **Hotend** | All-metal, max_temp=290C in Klipper config |
| **Probe** | CRTouch (BLTouch compatible), used as virtual Z endstop |
| **Bed** | Glass, mounted with 8 clips (losing ~1cm printable area per side) |
| **Enclosure** | Insulated (foam) chamber, electronics mounted outside. Chamber reaches 45-60C during ASA/ABS prints |
| **Part cooling** | Custom design, radial fan (~4010/5010). Blows too hard at 100% (breaks PLA layer adhesion). Hotend fan pulls air upward (does not blow on print) |
| **Filament sensor** | Present on PA4 |

### Verified Bed Limits

Glass bed 235x235mm with 1mm chamfer (frez) on each edge. 8 clips (~5mm each, 7mm safety margin). Modified frame limits nozzle travel.

| Boundary | X | Y | Notes |
|---|---|---|---|
| Glass edge | -2.5 to 231.5 | -1 to 234 | Physical glass extent |
| Flat surface (no chamfer) | -1.5 to 230.5 | 0 to 233 | Usable surface |
| Nozzle travel limit | 0 to 258 | -5 to 234 | Frame constraints |
| **Printable area (nozzle)** | **4 to 222** | **7 to 226** | Clips + safety margin |
| **Probe area (CRTouch)** | **4 to 215** | **7 to 226** | Nozzle travel + probe offset |

CRTouch offset: x_offset=-42.15, y_offset=-6.99. Probe is 42mm left and 7mm forward of nozzle. Right side of bed cannot be fully probed (probe max X=215.85 due to nozzle X max=258).

### Known Mechanical Issues

- **Bent X gantry**: causes first layer problems (small parts detaching on one side). Compensated in firmware via `[axis_twist_compensation]`. Would require full rebuild to fix mechanically.
- **Dual Z not synchronized**: no mechanical or electronic sync, manual adjustment only. Must be checked periodically.
- **max_accel=1000**: conservative value, likely can be raised after input shaper verification.
- **Bed mesh 50x50=2500 points**: extreme density, but adaptive mesh macro scales it down per print area.

## Structure

```
print/       PrusaSlicer print profiles (layer height, speeds, infill)
filament/    PrusaSlicer filament profiles (temps, cooling, pressure advance)
printer/     PrusaSlicer printer profiles (bed size, G-code flavor, start/end G-code)
klipper/     Klipper firmware config (printer.cfg for Creality v4.2.7 board)
ansible/     Deployment automation (Klipper config deploy via Ansible)
```

## Profile Naming Convention

- **Print**: `<layer_height> <QUALITY> (<nozzle> nozzle) @CREALITY - Kopiuj.ini`
- **Filament**: `<Brand> <Material> @ENDER3.ini`
- **Printer**: `Creality Ender-3 BLTouch (<nozzle> nozzle) Klipper.ini`

The `- Kopiuj` suffix in print profiles means "copy" (Polish) - these are derived from Creality defaults. The `@ENDER3` / `@CREALITY` suffixes are PrusaSlicer vendor tags for profile matching.

## INI Format and Inheritance

All profiles are PrusaSlicer INI files. Each has an `inherits` key referencing a built-in PrusaSlicer profile (e.g., `inherits = 0.20 mm NORMAL (0.4 mm nozzle) @CREALITY`). Only **overridden** settings appear in the file - everything else comes from the parent. This means:

- Files are intentionally sparse. Missing settings are not bugs.
- Changing a value means the override takes effect; removing a line reverts to the inherited default.
- The `compatible_printers_condition` and `compatible_prints_condition` fields use PrusaSlicer expression syntax (e.g., `nozzle_diameter[0]==0.4`) to bind profiles to specific hardware configurations.

## Two Nozzle Variants

The printer supports two nozzle sizes (0.2mm and 0.4mm), each with its own print and printer profile. Key differences:

| Aspect | 0.2mm nozzle | 0.4mm nozzle |
|---|---|---|
| Bed shape | 3x3 to 238x238 | 3x3 to 228x228 |
| Extrusion width | Explicit 0.2mm everywhere | Automatic (0 = auto) |
| Perimeter generator | Classic | Arachne |
| Start G-code macro | `START_PRINT_STAGE_TWO_02` | `START_PRINT_STAGE_TWO_04` |
| Retract lift | None | 0.4mm + travel ramping |

When adding or modifying profiles, always check which nozzle variant is affected and keep both in sync where appropriate.

## Klipper Integration

PrusaSlicer is configured with `gcode_flavor = klipper` and `use_firmware_retraction = 1`. Retraction is handled entirely by Klipper's `[firmware_retraction]` section - PrusaSlicer's `retract_length` is set to 0.

### Macro Chain (Start/End G-code)

The printer profiles define a two-stage start sequence:

1. `START_PRINT_STAGE_ONE` - heats bed, homes, runs adaptive bed mesh, heats nozzle
2. `G4 P60000` - 60-second dwell (thermal soak)
3. `START_PRINT_STAGE_TWO_0x` - purge line (nozzle-specific: `_02` or `_04`)
4. Print runs
5. `END_PRINT` - cooldown, park head, disable steppers

These macros are defined in `klipper/printer.cfg`. Any changes to start/end G-code must be coordinated between the printer INI profiles and the Klipper config.

### Per-Filament Overrides via G-code

Filament profiles use `start_filament_gcode` to override Klipper's firmware retraction and pressure advance at print time:

```
SET_PRESSURE_ADVANCE ADVANCE=<value>
SET_RETRACTION RETRACT_LENGTH=<len> [RETRACT_SPEED=<s>] [UNRETRACT_SPEED=<s>]
```

- **ABS/ASA**: pressure_advance=0.0, retract=3.5mm (speeds inherited from printer.cfg default of 40mm/s)
- **PETG**: pressure_advance=0.72, retract=3.8mm @ 100mm/s both directions
- **PLA**: No overrides (oldest profile, uses printer.cfg defaults: PA=0.1, retract=3.5mm @ 40mm/s)

When adding new filament profiles, always include `SET_PRESSURE_ADVANCE` and `SET_RETRACTION` in `start_filament_gcode` with calibrated values.

## Gotchas

- **PrusaSlicer version drift**: profiles span versions 2.5.0-alpha2 through 2.9.4. Newer versions add keys (e.g., scarf seam, travel ramping) that older versions ignore. Opening old profiles in new PrusaSlicer may trigger implicit upgrades - commit only intentional changes.
- **Bed shape mismatch**: the 0.2mm and 0.4mm printer profiles define different printable areas (238x238 vs 228x228). This is intentional but easy to overlook.
- **`cooling = 0` everywhere**: all filament profiles disable PrusaSlicer's automatic cooling logic. Fan speeds are set explicitly via `min_fan_speed`/`max_fan_speed`. This is deliberate - do not "fix" it.
- **Filename spaces**: all INI filenames contain spaces and parentheses. Use proper quoting in shell commands.
- **No validation tooling**: there are no linters, tests, or CI. Manual review and test prints are the verification method.

## Deployment

Klipper config is deployed via Ansible. Run from the `ansible/` directory:

```bash
cd ansible && ansible-playbook deploy.yml
```

- Copies `klipper/printer.cfg` to `klipper.i.kwasek.org:/home/kwasek/printer_data/config/printer.cfg`
- Creates a backup of the remote file before overwriting
- Restarts the `klipper` systemd service only when the file actually changes

Dry run: `ansible-playbook deploy.yml --check --diff`

To pull the current remote config into the local repo (e.g., after a Klipper update):

```bash
cd ansible && ansible-playbook fetch.yml
```

This overwrites `klipper/printer.cfg` with the remote version. Review with `git diff`, then commit or `git checkout -- klipper/printer.cfg` to discard.

To build and flash MCU firmware (e.g., after Klipper host update):

```bash
cd ansible && ansible-playbook flash-firmware.yml
```

- Copies `klipper/firmware.config` as `.config` to the remote Klipper source tree
- Runs `make clean && make` to build `klipper.bin`
- Stops Klipper service
- Flashes firmware via `~/klipper/scripts/flash-sdcard.sh` using USB serial (`/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`, board `creality-v4.2.7`)
- Starts Klipper service and checks MCU version in logs
- The firmware config (`klipper/firmware.config`) is version-controlled - update it here if menuconfig settings change

**WARNING - firmware.config must be the full `make olddefconfig` output, not just the manually selected options from `make menuconfig`.** The Kconfig system treats missing keys as disabled. A minimal config with only "positive" options will produce firmware missing critical peripherals (ADC, SPI, I2C, sensors) - the MCU will boot but Klipper will fail with `MCU Protocol error: Firmware constant 'ADC_MAX' not found`. After changing menuconfig settings, always run `make olddefconfig` and commit the resulting `.config` as `klipper/firmware.config`.

When upgrading Klipper, new Kconfig options may appear. Re-run `make olddefconfig` on the remote host to expand the stored config with new defaults, then fetch and commit the updated file.

**After the playbook completes, a full power cycle is required:**

1. Stop Klipper: `ansible klipper -b -m systemd -a "name=klipper state=stopped"`
2. Power off the printer at the power strip (USB must also lose power)
3. Wait a few seconds, then power everything back on
4. The Creality v4.2.7 bootloader loads the new firmware from its internal SD card during cold boot
5. Klipper will start automatically (systemd `Restart=always`)
6. Verify: check `klippy.log` for `Loaded MCU 'mcu'` line - the version must match `Git version` in the same log

## Moonraker API Usage

Host: `http://klipper.i.kwasek.org:7125`. All requests go through `bypass curl` (Crush sandbox blocks raw curl).

### Request behavior

Moonraker blocks the HTTP response until the G-code command finishes executing. This means:

- `M109 S265` (wait for hotend temp) - response returns only after 265C is reached
- `G28` (home all) - response returns after homing completes
- `G1 E100 F100` (extrude 100mm) - response returns after extrusion finishes
- `BED_MESH_CALIBRATE` - response returns after all probe points are done

**Never use `sleep` before checking results.** The response itself is the completion signal. Use `--max-time` only for fire-and-forget commands (e.g., interactive wizards like `AXIS_TWIST_COMPENSATION_CALIBRATE` that require user input and never return on their own).

### Common patterns

```bash
# Send G-code and wait for completion
bypass curl -s -X POST http://klipper.i.kwasek.org:7125/printer/gcode/script \
  -H 'Content-Type: application/json' -d '{"script": "G28"}'

# Fire-and-forget (interactive commands that need user input)
bypass curl -s -X POST http://klipper.i.kwasek.org:7125/printer/gcode/script \
  -H 'Content-Type: application/json' -d '{"script": "AXIS_TWIST_COMPENSATION_CALIBRATE"}' \
  --max-time 3

# Read position
bypass curl -s "http://klipper.i.kwasek.org:7125/printer/objects/query?toolhead=position"

# Read temperatures
bypass curl -s "http://klipper.i.kwasek.org:7125/printer/objects/query?extruder=temperature,target&heater_bed=temperature,target"

# Read G-code console (last N messages)
bypass curl -s "http://klipper.i.kwasek.org:7125/server/gcode_store?count=30"
```

### Interactive commands (fire-and-forget with --max-time 3)

These commands start a wizard that requires user interaction via the web UI. Use `--max-time 3` to send and move on, then poll `gcode_store` for results:

- `AXIS_TWIST_COMPENSATION_CALIBRATE` - paper test at multiple points
- `PROBE_CALIBRATE` - single-point paper test
- `SCREWS_TILT_CALCULATE` - reports screw adjustments
- `PID_CALIBRATE` - long-running temperature oscillation test

### Safety

- Always lift Z before moving XY (clips are ~1mm tall)
- After MCU shutdown (e.g., verify_heater trip), send `FIRMWARE_RESTART` before any new commands
- `SAVE_CONFIG` auto-restarts Klipper

## Agent Responsibilities

When modifying `klipper/printer.cfg`, the agent must:

1. Validate the change makes sense in context of the Klipper config (cross-reference macros, pin assignments, limits).
2. Run `cd ansible && ansible-playbook deploy.yml --check --diff` to preview the remote diff.
3. After user approval, deploy with `cd ansible && ansible-playbook deploy.yml` and confirm `changed=1`, `failed=0`.

When modifying PrusaSlicer profiles (`print/`, `filament/`, `printer/`):

- Symlinks from `~/.config/PrusaSlicer/` (Linux) or `%APPDATA%\PrusaSlicer` (Windows) to this repo are already in place. Editing files here takes effect immediately.
- If PrusaSlicer is running, it must be restarted to pick up changes.
- No remote deployment is needed - changes are local only.

## Commits

- English commit messages, single-line, concise.
- Feature branches + PRs against main.
- Group related profile changes (e.g., tuning a material across print + filament profiles) into single commits.
