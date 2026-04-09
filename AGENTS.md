# AGENTS.md

## Purpose

Personal PrusaSlicer + Klipper configuration for a Creality Ender-3 with BLTouch. No source code, no build system, no CI - this is a dotfiles-style repo of INI profiles and Klipper firmware config, symlinked into `~/.config/PrusaSlicer/` (Linux) or `%APPDATA%\PrusaSlicer` (Windows). See `README.md` for installation.

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
