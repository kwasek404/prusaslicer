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
| rotation_distance | **22.566** | printer.cfg [extruder] |
| pressure_advance (ASA) | **0.68** (via M221 in filament gcode) | filament gcode |
| extrusion_multiplier (ASA) | **0.96** (via M221 S96 in filament gcode) | filament gcode |
| retract_length (ASA) | **2.28mm** (via SET_RETRACTION in filament gcode) | filament gcode |
| retract_speed / unretract_speed | **40 / 40 mm/s** (via SET_RETRACTION in filament gcode) | filament gcode |
| max_accel | **1000** (reverted from 3000 due to ringing, awaits input shaper calibration) | printer.cfg [printer] |
| input_shaper | **DISABLED** (no accelerometer, stale values after hardware changes) | printer.cfg [input_shaper] |
| square_corner_velocity | **5** | printer.cfg [printer] |
| skew_correction | XY=-0.20°, XZ=0.16°, YZ=-0.89° (my_skew_profile) | printer.cfg [skew_correction] |
| hotend PID | **Kp=22.659 Ki=0.763 Kd=168.241** | printer.cfg [extruder] |
| bed PID | **Kp=67.102 Ki=1.761 Kd=639.148** | printer.cfg [heater_bed] |
| z_offset | **2.416** | printer.cfg [bltouch] |
| axis_twist_comp X | 10 pts, range 0.146mm | printer.cfg [axis_twist_compensation] |
| axis_twist_comp Y | 10 pts, range 0.036mm | printer.cfg [axis_twist_compensation] |
| bed_mesh probe_count | **10x10** (adaptive per print) | printer.cfg [bed_mesh] |
| horizontal_move_z | **5** | printer.cfg [bed_mesh] |
| first_layer_height | **0.1** | print profiles |
| print_speed (ASA) | **60 mm/s** (uniform for all wall/infill types) | print profile (0.4mm nozzle) |
| fan_speed (ASA) | **15%** constant (unchanged, confirmed optimal) | filament profile |

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

4. The mesh is **10x10** (100 points) with adaptive mesh scaling per-print area. Stale bed_mesh profiles should not be saved in SAVE_CONFIG - adaptive mesh runs fresh each print.

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

> **New rotation_distance**: **22.566**

### 2.2 First Layer Calibration (Z Offset / Squish)

Printed with ASA at full operating temps.

**Preparation**: Create a test gcode in PrusaSlicer:
- Single-layer square patches, scattered across the bed (at least 5: center, four quadrants). Use patches from [Ellis test_prints](https://github.com/AndrewEllis93/Print-Tuning-Guide/tree/main/test_prints).
- First layer height: **0.1mm** (matches our print profiles), line width: **120%** (= 0.48mm with 0.4mm nozzle).
- Bed temp: 95C, nozzle: 265C. No skirt/brim.
- Alternatively, use a dedicated first layer test model or a Python-generated G-code (see `docs/`).

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

> **New z_offset**: **2.416** (adjusted -0.05 from initial PROBE_CALIBRATE value of 2.466)

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

> **New pressure_advance**: **0.68**

**After calibration**: Update `filament/ABS ASA @ENDER3.ini` - add/change `SET_PRESSURE_ADVANCE ADVANCE=<new_value>` in `start_filament_gcode`.

> **New pressure_advance**: **0.68** (Z=34mm on PA tower, PA per mm = 0.020)

See: [Ellis PA Guide](https://ellis3dp.com/Print-Tuning-Guide/articles/pressure_linear_advance/pattern_method.html) for visual examples.

### 2.4 Extrusion Multiplier (Flow Rate)

Calibrate AFTER pressure advance - PA affects flow perception.

**Method**: Python-generated G-code with 5 cubes in one print, M221 switching per-cube within each layer. This avoids PrusaSlicer's limitation of one EM per print. Generator: `docs/gen_em_test.py`.

**Test cube settings**:
- Size: 30 x 30 x 3 mm (10 layers at 0.3mm)
- 2 perimeters, solid monotonic line infill
- Tick marks on front face for identification (1 tick = lowest EM, 5 ticks = highest)
- EM values: 0.90, 0.93, 0.96, 0.99, 1.02
- M221 S<pct> switches flow per-cube within each layer
- PA=0.68, firmware retraction G10/G11
- Fan: 15% from layer 1

**Evaluation**:

1. Compare the **center** of the top surface (ignore edges near perimeters):
   - **EM too low**: Gaps between top lines, rough/textured surface, can see infill through the top.
   - **EM too high**: Lines pile up, top surface bulges, slight ridges where lines overlap excessively.
   - **Correct**: Smooth top, lines merge together with no gaps but no excess material.
2. **When in doubt, go slightly higher** - gaps in the top surface are worse than slight over-extrusion for part strength.

**Pass**: Top surface of the cube is smooth with no gaps. Edges are clean. Walls are straight (no bulging).

> **New extrusion_multiplier**: **0.96** (M221 S96, cube 3 with 3 tick marks)

**After calibration**: Add `M221 S96` to `start_filament_gcode` in `filament/ABS ASA @ENDER3.ini`. Keep PrusaSlicer's `extrusion_multiplier = 1` (Klipper-first principle - runtime override via G-code).

### 2.5 PA/EM Iteration

PA and EM interact. After setting EM, reprint the PA test:

1. Print a 20mm cube with the new EM value.
2. Check corners - if PA needs tweaking, adjust by +/- 0.02.
3. Reprint the EM cube with the adjusted PA.
4. One iteration is usually enough. Stop when both look good.

**Pass**: Cube has sharp corners AND smooth top surface simultaneously.

---

## Phase 3: Retraction and Cooling

Retraction must be calibrated BEFORE cooling - stringing from bad retraction would corrupt the speed/fan test results. Cooling test comes after, once clean travel moves are confirmed.

### 3.1 Retraction Matrix Test (Length x Speed)

Calibrate AFTER pressure advance - proper PA dramatically reduces needed retraction.

**Current settings**: 3.5mm @ 40/40 mm/s (firmware retraction in Klipper).

**Expected outcome**: With proper PA (0.68), bowden systems typically need 1-4mm retraction.

**Method**: Python-generated G-code with 6 column-pair towers in one print. Each tower has a different retract speed (20/30/40/50/60/70 mm/s). Retract length increases with height via `SET_RETRACTION` per layer (1.0mm at bottom to 5.0mm at top). Generator: `docs/gen_retraction_test.py`.

**Test design**:
- 6 column-pair towers (two 8x8mm columns 6mm apart - gap shows stringing)
- Retract speeds: 20, 30, 40, 50, 60, 70 mm/s
- Retract length: increases with Z from 1.0 to 5.0mm
- Height: 50mm at 0.3mm layers
- PA=0.68, EM=0.96 (M221 S96), fan 15%
- Each tower clearly labeled with speed value

**Evaluation**:

1. For each tower (speed), find the Z height where stringing disappears.
2. Read the retract length at that Z: `retract_length = 1.0 + (Z / 50) * 4.0`
3. Choose the lowest speed that gives clean results (lower speed = less filament grinding).
4. Pick retract length **1 step above** minimum clean value for safety margin.
5. If stringing persists at all lengths, check:
   - Bowden tube fitting: push the tube in and out. If it moves > 0.5mm, the collet is worn.
   - Hotend assembly: is the bowden tube seated against the nozzle? Any gap = stringing.

**Pass**: No visible stringing between columns at the chosen retraction length/speed.

> **New retract_length**: **2.28mm** (Z=16mm on tower 3, formula: 1.0 + (16/50) * 4.0)
> **New retract_speed**: **40 mm/s** (tower 3)
> **New unretract_speed**: **40 mm/s** (same as retract)

**After calibration**: Update `filament/ABS ASA @ENDER3.ini` - adjust `SET_RETRACTION RETRACT_LENGTH=<new>` in `start_filament_gcode`. If speed changes, add `RETRACT_SPEED=<s> UNRETRACT_SPEED=<s>`.

### 3.2 Cooling Test (Speed/Fan Matrix)

ASA is sensitive to cooling - too much causes layer delamination, too little causes drooping overhangs.

**Current settings**: 15% constant fan, dynamic fan speeds disabled, overhang fan 100/75/50/25%.

**Method**: Python-generated G-code with 4 hollow square towers at different print speeds (20/40/60/80 mm/s). Fan decreases with height in 5mm bands: 100% -> 80% -> 60% -> 40% -> 20% -> 10% -> 0%. Generator: `docs/gen_speed_fan_test.py`. Result: 28 combinations in one print.

**Evaluation**:

1. For each speed, find the minimum fan % that still gives acceptable detail (clean overhangs, no drooping).
2. Check layer adhesion at each fan level - try to break the part with your hands. If layers separate easily, fan is too high.
3. In the **heated chamber** (45-60C ambient), ASA may tolerate less cooling than in open air.
4. Goal: minimum fan % for maximum layer adhesion, accepting slower speeds if needed.

**ASA guideline**: 15-30% fan is typical. Above 30% risks delamination. The heated chamber helps maintain layer adhesion even with moderate cooling.

**Pass**: Overhangs clean to 45 degrees at chosen speed/fan combo. Part does not delaminate when bent.

> **Fan speed sweet spot**: **15%** constant (current setting confirmed - best balance of adhesion vs overhang quality in heated chamber)
> **Optimal print speed**: **60 mm/s** (tower 3 - clean overhangs, no deformation/cracking; tower 1 at 20mm/s and tower 4 at 80mm/s showed deformation and cracks)

**After calibration**: Updated `print/0.1 mm NORMAL (0.4 mm nozzle) @CREALITY - Kopiuj.ini` - all speed settings (perimeter, external_perimeter, infill, solid_infill, top_solid_infill, bridge, gap_fill, small_perimeter, support_material, overhang) set to **60 mm/s**. Dynamic overhang speeds disabled. Fan settings unchanged in filament profile.

---

## Phase 4: Advanced

Input shaper disabled (no accelerometer available, values stale after hardware changes). Testing SCV and acceleration visually, then skew correction.

### 4.0 Disable Input Shaper

Old values (mzv, X=35.9 Hz, Y=50.7 Hz) potentially wrong after hardware changes. No ADXL345 accelerometer available to recalibrate.

1. Comment out `[input_shaper]` section in printer.cfg.
2. Deploy and restart Klipper.

> **Status**: DONE - input shaper section commented out, Klipper restarted.

### 4.1 SCV/Acceleration Hybrid Test

Combined test: 5 hollow cube towers, each at a different `square_corner_velocity`, with acceleration increasing in bands with Z height. Print speed stays at 60 mm/s (calibrated value) to isolate motion parameters.

**Test layout** (`docs/gen_scv_accel_test.py`):
- 5 towers at SCV = 1 / 3 / 5 / 7 / 9 mm/s
- 6 acceleration bands (6mm each, 36mm total height): 500 / 1000 / 1500 / 2000 / 2500 / 3000 mm/s^2
- 20x20mm hollow cubes, 2 perimeters, no infill
- Seam on back face (Y+), ticks on front face for tower ID

**Klipper commands used per object/layer**:
```
SET_VELOCITY_LIMIT SQUARE_CORNER_VELOCITY=<val>   ; per tower
SET_VELOCITY_LIMIT ACCEL=<val>                     ; per Z band
```

**Evaluation criteria**:
- **Corners**: ringing/ghosting pattern after sharp turns (SCV effect)
- **Flat walls**: ripples/waves from acceleration/deceleration (accel effect)
- Find the highest SCV and accel with acceptable surface quality
- Compare towers at same height to isolate SCV effect
- Compare bands within a tower to isolate accel effect

**Reading results**:
- Tower number (front ticks): 1=SCV1, 2=SCV3, 3=SCV5, 4=SCV7, 5=SCV9
- Band index = floor(Z / 6mm): 0=500, 1=1000, 2=1500, 3=2000, 4=2500, 5=3000 mm/s^2

> **Best SCV**: **5** (tower 3 - best corner quality, Klipper default)
> **Best max_accel**: **3000** (clean even at highest band; limited only by lack of input shaper)

### 4.2 Skew Correction

Use the official Klipper calibration model ([thing:2972743](https://www.thingiverse.com/thing:2972743)) - 3 rectangles (XY, XZ, YZ planes) in one print. Print through PrusaSlicer with standard profiles as a full integration test.

**Before printing**: temporarily add `\nSET_SKEW CLEAR=1` to the end of `start_gcode` in the printer INI (PrusaSlicer), so old skew correction does not corrupt the calibration measurement. Remove after.

1. Slice and print the model.
2. For each plane, measure with calipers (inner-to-outer corner technique, 2-3x average):
   - AC (diagonal)
   - BD (diagonal)
   - AD (reference side)
3. Apply correction and save:
   ```
   SET_SKEW XY=<AC>,<BD>,<AD> XZ=<AC>,<BD>,<AD> YZ=<AC>,<BD>,<AD>
   SKEW_PROFILE SAVE=my_skew_profile
   SAVE_CONFIG
   ```
4. Remove the temporary `SET_SKEW CLEAR=1` from printer INI.

Ref: [Klipper skew correction docs](https://www.klipper3d.org/Skew_Correction.html)

> **XY measurements**: AC=140.5, BD=141.0, AD=99.8 -> skew **-0.20°**
> **XZ measurements**: AC=141.7, BD=141.3, AD=99.8 -> skew **0.16°**
> **YZ measurements**: AC=140.1, BD=142.3, AD=99.5 -> skew **-0.89°** (large, confirmed: old bent Ender frame, Y-axis lacks side bracing)
> **Skew correction applied**: YES (profile `my_skew_profile`)
>
> **Verification re-print** (same model, after correction):
> - XY: AC=140.7, BD=140.8, AD=99.4 -> |AC-BD| = 0.1 mm (from 0.5)
> - XZ: AC=141.3, BD=141.4, AD=99.8 -> |AC-BD| = 0.1 mm (from 0.4)
> - YZ: AC=141.3, BD=141.2, AD=99.5 -> |AC-BD| = 0.1 mm (from 2.2)
> All planes corrected to within measurement noise (~0.1 mm with calipers). Skew calibration complete.

---

## Results Summary

Fill in after completing each phase:

| Parameter | Old Value | New Value | Changed? |
|---|---|---|---|
| rotation_distance | 22.98 | **22.566** | YES |
| z_offset | 0.186 | **2.416** | YES |
| pressure_advance (ASA) | 0.0 | **0.68** | YES |
| extrusion_multiplier (ASA) | 1.0 | **0.96** (M221 S96) | YES |
| retract_length (ASA) | 3.5 | **2.28** | YES |
| retract_speed (ASA) | 40 | **40** (confirmed) | YES |
| fan_speed (ASA) | 15% | **15%** (confirmed) | YES |
| print_speed (ASA) | 15-30 mixed | **60** (uniform) | YES |
| hotend PID (Kp/Ki/Kd) | 21.5/1.1/109 | **22.7/0.8/168** | YES |
| bed PID (Kp/Ki/Kd) | 54.0/0.8/948 | **67.1/1.8/639** | YES |
| axis_twist X | (none) | **10 pts, 0.146mm range** | YES |
| axis_twist Y | (none) | **10 pts, 0.036mm range** | YES |
| bed_mesh probe_count | 50x50 | **10x10** | YES |
| horizontal_move_z | 1 | **5** | YES |
| first_layer_height | 0.2 | **0.1** | YES |
| input_shaper X/Y | 35.9/50.7 mzv | **DISABLED** | YES |
| square_corner_velocity | 6 (default) | **5** | YES |
| skew_correction | (none) | **XY=-0.20°, XZ=0.16°, YZ=-0.89°** | YES |
| max_accel | 1000 | **1000** (tested 3000, reverted due to ringing) | NO |

## Files to Update After Calibration

1. **`klipper/printer.cfg`** (deploy via Ansible after changes):
   - `[extruder]` rotation_distance
   - `[extruder]` PID values (auto-saved by SAVE_CONFIG)
   - `[heater_bed]` PID values (auto-saved by SAVE_CONFIG)
   - `[bltouch]` z_offset (auto-saved by Z_OFFSET_APPLY_PROBE + SAVE_CONFIG)
   - `[printer]` max_accel (if changed)
   - `[input_shaper]` values (if changed, auto-saved by SAVE_CONFIG)

2. **`filament/ABS ASA @ENDER3.ini`**:
   - `start_filament_gcode`: `SET_PRESSURE_ADVANCE ADVANCE=<new>`
   - `start_filament_gcode`: `SET_RETRACTION RETRACT_LENGTH=<new>` (+ speeds if changed)
   - `start_filament_gcode`: `M221 S<pct>` for extrusion multiplier (keep `extrusion_multiplier = 1` in INI - Klipper-first principle)
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

# Extrusion multiplier (Klipper-first - use M221 instead of slicer setting)
M221 S<pct>                            # e.g., M221 S96 = 0.96 EM

# Retraction
SET_RETRACTION RETRACT_LENGTH=<len> RETRACT_SPEED=<spd> UNRETRACT_SPEED=<spd>

# Input shaper and accel
SHAPER_CALIBRATE
SET_VELOCITY_LIMIT ACCEL=<val>

# Fetch config after remote changes
cd ~/repo/github.com/kwasek404/prusaslicer/ansible && ansible-playbook fetch.yml
```
