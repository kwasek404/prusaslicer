# ASA Calibration Guide - Ender-3 / Klipper

Comprehensive step-by-step calibration for ASA filament.
Based on [Ellis' Print Tuning Guide](https://ellis3dp.com/Print-Tuning-Guide/).

**Printer**: Creality Ender-3, Klipper, Creality v4.2.7 board, CRTouch, dual-gear BMG extruder, bowden (~30cm), all-metal hotend, insulated enclosure, glass bed.

**Filament**: ASA - nozzle 265C, bed 95C (first layer 120C), chamber 45-60C.

---

## Before You Start

- All Klipper commands are entered in the **Fluidd/Mainsail console**.
- After each `SAVE_CONFIG`, Klipper restarts automatically.
- Keep the enclosure **closed** during all tests (ASA operating conditions).
- Have calipers, ruler, marker, and tape ready.
- Print a few test objects between phases to verify cumulative progress.

### Current Config Values (for reference)

| Parameter | Current Value | Source |
|---|---|---|
| rotation_distance | 22.98 (commented: 24.61) | printer.cfg [extruder] |
| pressure_advance | 0.1 (default) / **0.0 (ASA override)** | printer.cfg / filament gcode |
| retract_length | 3.5mm | printer.cfg [firmware_retraction] |
| retract_speed / unretract_speed | 40 / 40 mm/s | printer.cfg [firmware_retraction] |
| max_accel | 1000 | printer.cfg [printer] |
| input_shaper | mzv, X=35.9 Hz, Y=50.7 Hz | printer.cfg [input_shaper] |
| hotend PID | Kp=21.527 Ki=1.063 Kd=108.982 | printer.cfg [extruder] |
| bed PID | Kp=54.027 Ki=0.770 Kd=948.182 | printer.cfg [heater_bed] |
| z_offset | 0.186 | printer.cfg [bltouch] |
| extrusion_multiplier | 1.0 | filament profile |

---

## Phase 0: Mechanical Verification

Complete these checks with the printer **cold and powered off** (except where noted).

### 0.1 Synchronize Z Leadscrews

The printer has dual Z leadscrews driven by a single stepper - they drift over time.

1. Home the printer: `G28`
2. Move gantry to Z=150: `G1 Z150 F600`
3. **Disable steppers**: `M84`
4. Measure distance from the top of each Z leadscrew nut to the bottom of the top frame extrusion (both left and right side).
5. If difference > 0.5mm, manually rotate the faster leadscrew coupler to equalize.
6. Re-home after adjustment: `G28`

**Pass**: Left and right measurements differ by less than 0.3mm.

### 0.2 Belt Tension (X and Y)

1. Power off the printer.
2. Pinch each belt in the middle of its run.
3. The belt should feel taut with very little deflection (like a guitar string with a low tone, not floppy).
4. Pluck the belt - listen for a low-pitched twang. If it sounds dead/thuddy, tighten.
5. Tighten via the tensioner screw on each axis if needed.

**Pass**: Both belts feel similar tension. No visible slack when the toolhead moves.

### 0.3 V-Slot Roller Tension

1. With steppers disabled (`M84`), try to wobble the toolhead and bed carriage by hand.
2. There should be **zero play** (no rattling/clicking) but the carriage should still slide smoothly.
3. Adjust eccentric nuts if needed (quarter turns only).

**Pass**: No play on any axis. Carriages glide without excessive resistance.

### 0.4 Mechanical Bed Leveling (Screws Tilt Adjust)

1. Heat bed to operating temp:
   ```
   M140 S95
   ```
2. Wait for thermal expansion to stabilize (~10 min).
3. Run:
   ```
   SCREWS_TILT_ADJUST
   ```
4. Klipper will probe each screw location and report adjustments like:
   ```
   01:20 means 1 full turn and 20 minutes CW
   CW = clockwise (raise), CCW = counter-clockwise (lower)
   ```
5. Adjust screws as instructed. Repeat until all positions report < 0:03 (three "minutes" of rotation).

**Pass**: All screws within 0:03 of the reference screw. Repeat 2-3 times to confirm stability.

---

## Phase 1: Firmware and Thermal Calibration

All steps in this phase run at **ASA operating temperatures** in a **closed enclosure**.

### 1.1 PID Tune Hotend

The hotend PID must be tuned at the actual printing temperature, inside the heated chamber.

1. Close the enclosure. Heat bed to 95C and wait 15 min for chamber to warm.
2. Run:
   ```
   PID_CALIBRATE HEATER=extruder TARGET=265
   ```
3. Wait for completion (~5 min). Do not open the enclosure during the test.
4. Save:
   ```
   SAVE_CONFIG
   ```
5. Klipper restarts. Verify new PID values appear in `printer.cfg` under `[extruder]`.

**Pass**: Temperature graph shows stable 265C with oscillation < 1C after settling.

### 1.2 PID Tune Bed

1. Enclosure still closed, chamber warm.
2. Run:
   ```
   PID_CALIBRATE HEATER=heater_bed TARGET=95
   ```
3. Wait for completion (~10-15 min, bed PID cycles are slower).
4. Save:
   ```
   SAVE_CONFIG
   ```

**Pass**: Bed temperature stable at 95C, oscillation < 1C.

### 1.3 Axis Twist Compensation

Compensates for the known bent X gantry. Must be done at operating temperature (thermal expansion changes the twist).

1. Heat to ASA temps: bed 95C, nozzle 265C. Wait for chamber to stabilize (~15 min).
2. Run:
   ```
   AXIS_TWIST_COMPENSATION_CALIBRATE
   ```
3. Follow the on-screen prompts - Klipper will probe points along the X axis and ask you to baby-step Z at each point using `ACCEPT` or `ADJUSTED` commands.
4. After all points are measured:
   ```
   SAVE_CONFIG
   ```

**Pass**: Compensation values saved. First layer uniformity should improve across the X axis.

### 1.4 Full Bed Mesh

Run after axis twist compensation, at operating temperature.

1. Ensure bed is at 95C and nozzle at a safe probing temp (120-150C to avoid oozing - or use the G29 macro which heats to 115/120).
2. Option A - use the existing G29 macro:
   ```
   G29
   ```
   This heats bed to 115C, nozzle to 120C, homes, runs full mesh, and saves.

3. Option B - manual at ASA temps:
   ```
   G28
   BED_MESH_CALIBRATE
   SAVE_CONFIG
   ```

4. The mesh is 50x50 (2500 points) - this takes ~30-45 minutes. Be patient.

**Pass**: Mesh visualizer (Fluidd/Mainsail) shows a smooth surface without sudden spikes. Adaptive mesh will use a subset during actual prints.

---

## Phase 2: Extrusion Calibration

This is the core of the Ellis Guide. **Order matters** - each step builds on the previous one.

### 2.1 Extruder Calibration (rotation_distance)

Resolves the conflict between 22.98 (active) and 24.61 (commented out).

**WARNING**: This test is done with the **bowden tube disconnected** from the extruder. You are measuring raw extruder output, not through the hotend.

1. Disconnect the bowden tube at the extruder end.
2. Cut the filament flush at the extruder output.
3. Set `max_extrude_only_distance` to 101 in `[extruder]` section and `RESTART`. If testing cold (bowden disconnected), also temporarily set `min_extrude_temp` to 0.
4. Heat nozzle (to allow extrusion command, skip if testing cold):
   ```
   M104 S265
   ```
5. Extrude a tiny bit to engage the motor, then mark the filament 120mm from the extruder body entrance using a marker and calipers.
   ```
   M83
   G1 E1 F60
   ```
6. Extrude 100mm slowly:
   ```
   M83
   G1 E100 F60
   ```
7. Measure the distance from the mark to the extruder entrance. It should be **20mm** if the extruder is perfectly calibrated.
8. Calculate:
   ```
   actual_extrusion = 120 - measured_remaining
   new_rotation_distance = current_rotation_distance * (actual_extrusion / 100)
   ```
   Example: if 23mm remains -> extruded 97mm -> new = 22.98 * (97/100) = 22.29

9. Test without restarting:
   ```
   SET_EXTRUDER_ROTATION_DISTANCE EXTRUDER=extruder DISTANCE=<new_value>
   ```
10. Repeat steps 5-8 until the extruder pushes exactly 100mm (remaining = 20mm). Use the updated rotation_distance for each iteration, not the original.
    - If you get different results on back-to-back tests, you have an **extruder issue** (gear slipping, loose grub screw, etc.).
11. Once dialed in, update `printer.cfg` [extruder] `rotation_distance` and `RESTART`.
12. If you set `min_extrude_temp` to 0 earlier, restore it to its original value.
13. **Reconnect the bowden tube.** Ensure the collet clip is pushed in and the tube is fully seated.

**Pass**: Consecutive tests extruding exactly 100.0mm (+-0.5mm). Record the final rotation_distance value here:

> **New rotation_distance**: _______________

### 2.2 First Layer Calibration (Z Offset / Squish)

Printed with ASA at full operating temps.

**Preparation**: Create a test gcode in PrusaSlicer:
- Single-layer square patches, scattered across the bed (at least 5: center, four quadrants). Use patches from [Ellis test_prints](https://github.com/AndrewEllis93/Print-Tuning-Guide/tree/main/test_prints).
- First layer height: **0.25mm** (thicker = less sensitive, easier to tune), line width: **120%** (= 0.48mm with 0.4mm nozzle).
- Bed temp: 95C, nozzle: 265C. No skirt/brim.
- Alternatively, use a dedicated first layer test model.

**Procedure**:

1. Start the print.
2. During the first layer, use baby-stepping in Fluidd/Mainsail (usually Z offset buttons, +/- 0.01mm or 0.025mm steps).
3. Adjust Z until:

   **Too high (increase squish = lower Z offset)**:
   - Gaps visible between lines
   - Lines are round/cylindrical, not pressed flat
   - Lines peel off easily

   **Too low (decrease squish = raise Z offset)**:
   - Top surface is completely smooth (no individual lines visible)
   - Filament builds up on nozzle
   - Ridges/plowing between lines

   **Correct**:
   - Lines slightly overlap but are individually visible
   - Smooth to the touch, no gaps
   - Lines adhere well, slight resistance when peeling

4. Once dialed in, save the offset:
   ```
   Z_OFFSET_APPLY_PROBE
   SAVE_CONFIG
   ```

5. Print the test again to verify the saved offset.

**Glass bed note**: Glass gives a smooth bottom surface that can mask issues. Focus on line-to-line adhesion and top-surface appearance, not bottom smoothness.

**Pass**: Uniform first layer across the entire bed. Lines visible but no gaps. Consistent adhesion in all areas (including the problem zone from the bent gantry, left side).

> **New z_offset**: _______________

See: [Ellis First Layer Guide](https://ellis3dp.com/Print-Tuning-Guide/articles/first_layer_squish.html) for photo examples.

### 2.3 Pressure Advance Calibration

This is the most critical step for ASA print quality and the primary suspect for the organic support issue.

**Expected range for bowden + ASA**: 0.3 - 0.8 (direct drive would be 0.02-0.12).

1. Go to [Ellis PA Pattern Generator](https://ellis3dp.com/Pressure_Linear_Advance_Tool/).
2. Settings:
   - **Printer**: Bed 235x235, nozzle 0.4mm
   - **Speeds**: Slow 30mm/s, Fast 100mm/s (or your typical infill speed)
   - **Pressure Advance**: Start 0.2, End 1.0, Step 0.02
   - **Hotend**: 265C, Bed 95C
   - **Pattern**: Line (default)
   - **Firmware**: Klipper
3. Generate and download the gcode.
4. **Before printing**, verify PA lines are visible in the gcode preview.
5. Print the pattern.
6. Examine the result:
   - Look at the **corners** of each line.
   - Too little PA: bulging/rounding at corners, material oozes out.
   - Too much PA: gaps/underextrusion at corners, thin lines after direction changes.
   - **Correct PA**: Sharp corners, consistent line width through acceleration/deceleration zones.
7. Read the PA value from the best-looking line.
8. Test it:
   ```
   SET_PRESSURE_ADVANCE ADVANCE=<value>
   ```
9. Print a small test object (20mm cube) and verify corners are clean.
10. If unsure between two values, **pick the higher one** (slight underextrusion at corners is less problematic than ooze for ASA).

**Pass**: Sharp corners on test cube. No bulging at direction changes. No stringing inside the print.

> **New pressure_advance**: _______________

**After calibration**: Update `filament/ABS ASA @ENDER3.ini` - change `SET_PRESSURE_ADVANCE ADVANCE=0.0` to `SET_PRESSURE_ADVANCE ADVANCE=<new_value>` in `start_filament_gcode`.

See: [Ellis PA Guide](https://ellis3dp.com/Print-Tuning-Guide/articles/pressure_linear_advance/pattern_method.html) for visual examples.

### 2.4 Extrusion Multiplier (Flow Rate)

Calibrate AFTER pressure advance - PA affects flow perception.

**Test cube settings in PrusaSlicer**:
- Size: 30 x 30 x 3 mm (just a few layers)
- Infill: 30%, any pattern
- Top solid layers: 10-11 (fills the cube almost entirely with top surface)
- Bottom solid layers: 2
- Top fill pattern: **Monotonic Lines** (important - avoid concentric)
- Top solid infill line width: 100% (= 0.4mm for 0.4mm nozzle)
- No ironing
- Perimeters: 2
- Nozzle: 265C, Bed: 95C

**Procedure**:

1. Print cubes at EM = 0.92, 0.94, 0.96, 0.98 (2% steps). Most filaments fall in the 0.92-0.98 range, but not all - if your best is at the edge, extend the range.
   - In PrusaSlicer you cannot set EM per-object - print one cube at a time, changing Filament Settings -> Filament -> Extrusion multiplier between prints.
2. Compare the **center** of the top surface (ignore edges near perimeters - small areas normally look slightly overextruded):
   - **EM too low**: Gaps between top lines, rough/textured surface, can see infill through the top.
   - **EM too high**: Lines pile up, top surface bulges, slight ridges where lines overlap excessively.
   - **Correct**: Smooth top, lines merge together with no gaps but no excess material.
3. Narrow down: print 0.5% increments around the best value.
4. **When in doubt, go slightly higher** - gaps in the top surface are worse than slight over-extrusion for part strength.

**Pass**: Top surface of the cube is smooth with no gaps. Edges are clean. Walls are straight (no bulging).

> **New extrusion_multiplier**: _______________

**After calibration**: Update `filament/ABS ASA @ENDER3.ini` - change `extrusion_multiplier = 1` to the new value.

### 2.5 PA/EM Iteration

PA and EM interact. After setting EM, reprint the PA test:

1. Print a 20mm cube with the new EM value.
2. Check corners - if PA needs tweaking, adjust by +/- 0.02.
3. Reprint the EM cube with the adjusted PA.
4. One iteration is usually enough. Stop when both look good.

**Pass**: Cube has sharp corners AND smooth top surface simultaneously.

---

## Phase 3: Cooling and Retraction

### 3.1 Cooling Test (ASA-Specific)

ASA is sensitive to cooling - too much causes layer delamination, too little causes drooping overhangs.

**Current settings**: 15% constant fan, dynamic fan speeds disabled, overhang fan 100/75/50/25%.

1. Print an overhang test model (e.g., "All In One Micro" test or a simple overhang fan from 15 to 75 degrees).
2. Print at current settings first (15% fan baseline).
3. If overhangs droop badly at >45 degrees, try increasing fan to 20%, then 25%.
4. Check layer adhesion after each test - try to break the part with your hands. If layers separate easily, fan is too high.
5. In the **heated chamber** (45-60C ambient), ASA may tolerate less cooling than in open air.

**ASA guideline**: 15-30% fan is typical. Above 30% risks delamination. The heated chamber helps maintain layer adhesion even with moderate cooling.

**Pass**: Overhangs clean to 45 degrees, acceptable to 60 degrees. Part does not delaminate when bent.

> **Fan speed sweet spot**: _______________% constant

### 3.2 Retraction Tuning

Calibrate AFTER pressure advance - proper PA dramatically reduces needed retraction.

**Current settings**: 3.5mm @ 40/40 mm/s (firmware retraction in Klipper).

**Expected outcome**: With proper PA, bowden systems typically need 1-4mm retraction. The 3.5mm may already be correct, or it may need to decrease.

**Procedure**:

1. Download or create a retraction tower test model. Options:
   - Use SuperSlicer's built-in retraction tower generator
   - Use any stringing test tower (e.g., two pillars with a bridge)
2. Print settings:
   - Start retraction: 1.0 mm
   - Step: 0.5 mm per section
   - Max retraction: 3.0 mm initially (height=7 in SuperSlicer)
   - Retract/unretract speed: **30 mm/s** to start (Ellis recommends slower speeds)
   - Start temperature: **275C** (10C above normal)
   - Temp decrease: **3x10C** (prints 3 towers: 275, 265, 255)
   - Fan: **80-100%** (small towers need extra cooling to not get melty)
   - Arrange towers **front to back** (hottest at front, coolest at back)
3. SuperSlicer's retraction calibration tool handles the retraction changes automatically per-layer. If using manual gcode, use `SET_RETRACTION RETRACT_LENGTH=<val>` at appropriate layer heights.
4. Find the lowest retraction length where stringing disappears. **Choose 1-2 steps higher** than that value for safety margin.
5. If the hotter towers are much stringier, consider lowering your normal print temperature.
6. If stringing persists at all lengths, check:
   - Bowden tube fitting: push the tube in and out. If it moves > 0.5mm, the collet is worn - replace it.
   - Hotend assembly: is the bowden tube seated against the nozzle? Any gap = stringing.

**Pass**: No visible stringing between pillars at the chosen retraction length. Clean travel moves.

> **New retract_length**: _______________mm
> **New retract_speed**: _______________mm/s
> **New unretract_speed**: _______________mm/s

**After calibration**: Update `filament/ABS ASA @ENDER3.ini` - adjust `SET_RETRACTION RETRACT_LENGTH=<new>` in `start_filament_gcode`. If speed changes, add `RETRACT_SPEED=<s> UNRETRACT_SPEED=<s>`.

---

## Phase 4: Advanced (Optional)

These steps are lower priority. Complete if time permits or if issues persist after Phases 0-3.

### 4.1 Input Shaper Verification

Current: mzv, X=35.9 Hz, Y=50.7 Hz. These may have shifted if belts or rollers were adjusted.

1. Run:
   ```
   SHAPER_CALIBRATE
   ```
2. This takes several minutes - the printer will vibrate at various frequencies.
3. Klipper will recommend shaper type and frequencies.
4. If values changed significantly (>5 Hz), save:
   ```
   SAVE_CONFIG
   ```
5. Klipper will also recommend a `max_accel` value - note it for step 4.2.

> **New shaper values**: X=_______ Hz, Y=_______ Hz, type=_______
> **Recommended max_accel**: _______

### 4.2 Maximum Acceleration Test

Current: 1000 mm/s^2 (very conservative).

1. Note the max_accel recommended by input shaper (step 4.1).
2. Test incrementally:
   ```
   SET_VELOCITY_LIMIT ACCEL=2000
   ```
3. Print a test cube at the new accel. Check for:
   - Ringing/ghosting on surfaces (accel too high)
   - Layer shifts (mechanical limit exceeded)
   - Missed steps (listen for clicking from steppers)
4. Increase in steps: 2000 -> 3000 -> 4000 -> max recommended.
5. Use the highest value that produces clean prints.

**Note**: With A4988 drivers (no StealthChop), you may hear more stepper noise at higher accel. This is normal. Stop only if print quality degrades or steps are lost.

> **New max_accel**: _______

### 4.3 Skew Correction Verification

A skew profile is already saved (`my_skew_profile`). Verify it's still accurate.

1. Print a calibration square (100x100mm, 1-2 layers tall).
2. Measure diagonals with calipers.
3. If diagonals differ by > 0.5mm, recalibrate using the [Klipper skew correction docs](https://www.klipper3d.org/Skew_Correction.html).
4. If diagonals are equal (+/- 0.5mm), the current profile is fine.

---

## Results Summary

Fill in after completing each phase:

| Parameter | Old Value | New Value | Changed? |
|---|---|---|---|
| rotation_distance | 22.98 | | |
| z_offset | 0.186 | | |
| pressure_advance (ASA) | 0.0 | | |
| extrusion_multiplier (ASA) | 1.0 | | |
| retract_length (ASA) | 3.5 | | |
| retract_speed (ASA) | 40 | | |
| fan_speed (ASA) | 15% | | |
| hotend PID (Kp/Ki/Kd) | 21.5/1.1/109 | | |
| bed PID (Kp/Ki/Kd) | 54.0/0.8/948 | | |
| input_shaper X/Y | 35.9/50.7 mzv | | |
| max_accel | 1000 | | |

## Files to Update After Calibration

1. **`klipper/printer.cfg`** (deploy via Ansible after changes):
   - `[extruder]` rotation_distance
   - `[extruder]` PID values (auto-saved by SAVE_CONFIG)
   - `[heater_bed]` PID values (auto-saved by SAVE_CONFIG)
   - `[bltouch]` z_offset (auto-saved by Z_OFFSET_APPLY_PROBE + SAVE_CONFIG)
   - `[printer]` max_accel (if changed)
   - `[input_shaper]` values (if changed, auto-saved by SAVE_CONFIG)

2. **`filament/ABS ASA @ENDER3.ini`**:
   - `extrusion_multiplier` value
   - `start_filament_gcode`: `SET_PRESSURE_ADVANCE ADVANCE=<new>`
   - `start_filament_gcode`: `SET_RETRACTION RETRACT_LENGTH=<new>` (+ speeds if changed)
   - Fan speeds if adjusted

3. **Fetch updated printer.cfg after SAVE_CONFIG changes**:
   ```bash
   cd ansible && ansible-playbook fetch.yml
   ```
   Review with `git diff`, then commit.

---

## Quick Reference - Key Commands

```
# Homing and probing
G28                                    # Home all axes
SCREWS_TILT_ADJUST                     # Bed screw leveling
BED_MESH_CALIBRATE                     # Full bed mesh
AXIS_TWIST_COMPENSATION_CALIBRATE      # X gantry twist compensation
Z_OFFSET_APPLY_PROBE                   # Save baby-stepped Z offset
SAVE_CONFIG                            # Save to printer.cfg and restart

# PID tuning
PID_CALIBRATE HEATER=extruder TARGET=265
PID_CALIBRATE HEATER=heater_bed TARGET=95

# Extrusion testing
G91                                    # Relative positioning
G1 E100 F60                            # Extrude 100mm at 1mm/s
G90                                    # Absolute positioning
SET_EXTRUDER_ROTATION_DISTANCE EXTRUDER=extruder DISTANCE=<val>

# Pressure advance
SET_PRESSURE_ADVANCE ADVANCE=<val>

# Retraction
SET_RETRACTION RETRACT_LENGTH=<len> RETRACT_SPEED=<spd> UNRETRACT_SPEED=<spd>

# Input shaper and accel
SHAPER_CALIBRATE
SET_VELOCITY_LIMIT ACCEL=<val>

# Fetch config after remote changes
cd ~/repo/github.com/kwasek404/prusaslicer/ansible && ansible-playbook fetch.yml
```
