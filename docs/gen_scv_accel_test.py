#!/usr/bin/env python3
"""Generate SCV/acceleration hybrid test G-code for ASA calibration.

5 hollow cube towers, each at a different square_corner_velocity (1/3/5/7/9 mm/s).
Acceleration increases with Z height in 6 bands (500/1000/1500/2000/2500/3000 mm/s^2).
Print speed: 60 mm/s (calibrated). 2 perimeters, inner-first, no infill.

Evaluate: ringing/ghosting on corners (SCV effect) and flat walls (accel effect).
Find the highest SCV and accel that produce acceptable quality.

Height: 36mm (6 bands of 6mm), layer height: 0.3mm.
PA=0.68, EM=0.96, retract 2.28mm@40mm/s, fan 15%.
"""

import math

layer_height = 0.3
line_width = 0.45
filament_d = 1.75
nozzle_temp = 265
bed_temp_first = 120
bed_temp_rest = 95
pressure_advance = 0.68
em_pct = 96
fan_pct = 15

cube_size = 20.0
n_perimeters = 2
total_height = 36.0
band_height = 6.0

speed_print = 60
speed_first = 20
speed_travel = 200

retract_length = 2.28
retract_speed = 40

scv_values = [1, 3, 5, 7, 9]
accel_values = [500, 1000, 1500, 2000, 2500, 3000]

n_towers = len(scv_values)
n_bands = len(accel_values)
n_layers = int(total_height / layer_height)
layers_per_band = int(band_height / layer_height)

bed_x_min = 4
bed_x_max = 222
bed_y_center = 116.0

total_x_needed = n_towers * cube_size
gap = (bed_x_max - bed_x_min - total_x_needed) / (n_towers - 1)

tower_centers = []
for i in range(n_towers):
    cx = bed_x_min + cube_size / 2 + i * (cube_size + gap)
    tower_centers.append((cx, bed_y_center))

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area

fan_s = int(round(fan_pct * 255 / 100))

min_x = int(tower_centers[0][0] - cube_size / 2)
max_x = int(tower_centers[-1][0] + cube_size / 2)
min_y = int(bed_y_center - cube_size / 2)
max_y = int(bed_y_center + cube_size / 2)

lines = []
lines.append("; SCV/Acceleration Hybrid Test - ASA")
lines.append(f"; {n_towers} towers, SCV values: {', '.join(str(v) for v in scv_values)} mm/s")
lines.append(f"; Accel bands: {', '.join(str(v) for v in accel_values)} mm/s^2")
lines.append(f"; Band height: {band_height}mm, total height: {total_height}mm")
lines.append(f"; Each tower: {cube_size}x{cube_size}mm hollow cube, {n_perimeters} perimeters")
lines.append(f"; Print speed: {speed_print} mm/s, PA={pressure_advance}, EM={em_pct}%")
lines.append(f"; Read result: band_index = floor(Z / {band_height})")
for i, a in enumerate(accel_values):
    z_lo = i * band_height
    z_hi = (i + 1) * band_height
    lines.append(f";   Z {z_lo:.0f}-{z_hi:.0f}mm: accel={a}")
lines.append("")

lines.append(f"SET_PRESSURE_ADVANCE ADVANCE={pressure_advance}")
lines.append(f"M221 S{em_pct}")
lines.append(f"SET_RETRACTION RETRACT_LENGTH={retract_length} RETRACT_SPEED={retract_speed} UNRETRACT_SPEED={retract_speed}")
lines.append("")

lines.append("M190 S0")
lines.append("M104 S0")
lines.append(f"START_PRINT_STAGE_ONE BED_TEMP={bed_temp_first}")
lines.append("G4 P60000")
lines.append(f"START_PRINT_STAGE_TWO_04 EXTRUDER_TEMP={nozzle_temp} MESH_AREA_START_X={min_x} MESH_AREA_START_Y={min_y} MESH_AREA_END_X={max_x} MESH_AREA_END_Y={max_y}")
lines.append("")
lines.append("M83")
lines.append("G21")
lines.append("G90")
lines.append("")


def draw_cube_perimeters(cx, cy, is_first, seam_side="back"):
    """Draw perimeters for a hollow cube. Inner-first order.

    seam_side="back" places seam at Y+ (back of cube, away from viewer).
    """
    result = []
    half = cube_size / 2
    f_print = int(speed_first * 60 if is_first else speed_print * 60)

    for p in reversed(range(n_perimeters)):
        offset = p * line_width
        x0 = cx - half + offset
        y0 = cy - half + offset
        x1 = cx + half - offset
        y1 = cy + half - offset

        side_x = x1 - x0
        side_y = y1 - y0
        e_x = round(side_x * e_per_mm, 4)
        e_y = round(side_y * e_per_mm, 4)

        is_outermost = (p == 0)

        if seam_side == "back":
            start = (x0, y1)
            path = [
                (x0, y0, e_y),
                (x1, y0, e_x),
                (x1, y1, e_y),
                (x0, y1, e_x),
            ]
        else:
            start = (x0, y0)
            path = [
                (x1, y0, e_x),
                (x1, y1, e_y),
                (x0, y1, e_x),
                (x0, y0, e_y),
            ]

        is_first_perim = (p == n_perimeters - 1)
        if is_first_perim:
            result.append("G10")
            result.append(f"G1 X{start[0]:.3f} Y{start[1]:.3f} F{int(speed_travel * 60)}")
            result.append("G11")
        else:
            result.append(f"G1 X{start[0]:.3f} Y{start[1]:.3f} F{int(speed_travel * 60)}")

        for px, py, e in path:
            result.append(f"G1 X{px:.3f} Y{py:.3f} E{e} F{f_print}")
    return result


def draw_tick_marks(cx, cy, n_ticks, is_first):
    """Draw identification ticks on front (Y-) face of cube."""
    result = []
    half = cube_size / 2
    front_y = cy - half
    tick_len = 2.5
    tick_spacing = 2.5
    total_width = (n_ticks - 1) * tick_spacing
    start_x = cx - total_width / 2

    for t in range(n_ticks):
        tx = start_x + t * tick_spacing
        ty0 = front_y - 0.5
        ty1 = front_y - 0.5 - tick_len
        f = int(speed_first * 60 if is_first else speed_print * 60)

        result.append("G10")
        result.append(f"G1 X{tx:.3f} Y{ty0:.3f} F{int(speed_travel * 60)}")
        result.append("G11")

        dist = abs(ty1 - ty0)
        e = round(dist * e_per_mm, 4)
        result.append(f"G1 X{tx:.3f} Y{ty1:.3f} E{e} F{f}")
    return result


prev_accel = None
for layer_num in range(n_layers):
    z = round((layer_num + 1) * layer_height, 3)
    is_first = (layer_num == 0)
    band_idx = min(layer_num // layers_per_band, n_bands - 1)
    accel = accel_values[band_idx]

    lines.append(f"; Layer {layer_num}, Z={z:.3f}, band={band_idx}, accel={accel}")
    lines.append(f"G1 Z{z:.3f} F300")

    if layer_num == 1:
        lines.append(f"M140 S{bed_temp_rest}")
        lines.append(f"M106 S{fan_s}")

    if accel != prev_accel:
        lines.append(f"SET_VELOCITY_LIMIT ACCEL={accel}")
        prev_accel = accel

    for t_idx in range(n_towers):
        tcx, tcy = tower_centers[t_idx]
        scv = scv_values[t_idx]

        lines.append(f"SET_VELOCITY_LIMIT SQUARE_CORNER_VELOCITY={scv}")
        lines.extend(draw_cube_perimeters(tcx, tcy, is_first))

        if layer_num <= 2:
            lines.extend(draw_tick_marks(tcx, tcy, t_idx + 1, is_first))

    lines.append("")

lines.append("")
lines.append("; Restore defaults")
lines.append("SET_VELOCITY_LIMIT ACCEL=1000 SQUARE_CORNER_VELOCITY=6")
lines.append("G1 Z150 F600")
lines.append("END_PRINT")

output_path = "/tmp/scv_accel_test.gcode"
with open(output_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} lines, {n_layers} layers, {n_towers} towers")
print(f"SCV values: {', '.join(f'{v}mm/s' for v in scv_values)}")
print(f"Accel bands: {', '.join(f'{v}mm/s^2' for v in accel_values)}")
print(f"Tower centers: {', '.join(f'X={c[0]:.1f}' for c in tower_centers)}")
print(f"Mesh area: X={min_x}-{max_x}, Y={min_y}-{max_y}")
print(f"Output: {output_path}")
