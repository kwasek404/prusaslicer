#!/usr/bin/env python3
"""Generate retraction matrix test G-code for ASA calibration.

6 column-pair towers with different retract speeds (20/30/40/50/60/70 mm/s).
Retract length increases with height from 1.0mm to 5.0mm.
Each tower has two 8x8mm columns 6mm apart - stringing visible in the gap.

Height: 50mm, layer height: 0.3mm, 2 perimeters, 15% fan.
PA=0.68, EM=0.96 (M221 S96).

Result: inspect gaps between columns. Find minimum retract length per speed
where stringing disappears. Pick the combination with clean gaps at lowest
retract length and lowest speed (less filament grinding).
"""

import math

layer_height = 0.3
line_width = 0.45
filament_d = 1.75
nozzle_temp = 265
bed_temp_first = 120
bed_temp_rest = 95
total_height = 50.0
pressure_advance = 0.68
em_pct = 96
fan_pct = 15

column_size = 8.0
column_gap = 6.0
n_perimeters = 2

speed_perim = 40
speed_first = 15
speed_travel = 200

retract_length_start = 1.0
retract_length_end = 5.0

retract_speeds = [20, 30, 40, 50, 60, 70]
n_towers = len(retract_speeds)

tower_width = column_size * 2 + column_gap
tower_spacing = (222 - 4 - tower_width) / (n_towers - 1)
tower_centers = []
for i in range(n_towers):
    cx = 4 + tower_width / 2 + i * tower_spacing
    cy = 115.0
    tower_centers.append((cx, cy))

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area

n_layers = int(total_height / layer_height)
fan_s = int(round(fan_pct * 255 / 100))

min_x = int(tower_centers[0][0] - tower_width / 2)
max_x = int(tower_centers[-1][0] + tower_width / 2)
min_y = int(tower_centers[0][1] - column_size / 2)
max_y = int(tower_centers[0][1] + column_size / 2)

lines = []
lines.append("; Retraction Matrix Test - ASA")
lines.append(f"; {n_towers} towers, retract speeds: {', '.join(f'{s}mm/s' for s in retract_speeds)}")
lines.append(f"; Retract length: {retract_length_start}mm (bottom) to {retract_length_end}mm (top)")
lines.append(f"; Each tower: two {column_size}x{column_size}mm columns, {column_gap}mm gap")
lines.append(f"; Height: {total_height}mm ({n_layers} layers at {layer_height}mm)")
lines.append(f"; PA={pressure_advance}, EM={em_pct}%, Fan={fan_pct}%")
lines.append(f"; Read result: retract_length = {retract_length_start} + (Z / {total_height}) * {retract_length_end - retract_length_start}")
lines.append("")

lines.append(f"SET_PRESSURE_ADVANCE ADVANCE={pressure_advance}")
lines.append(f"M221 S{em_pct}")
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


def draw_column(cx, cy, is_first, skip_approach=False, seam_side="left"):
    result = []
    half = column_size / 2
    f_print = int(speed_first * 60 if is_first else speed_perim * 60)

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

        is_first_perim = (p == n_perimeters - 1)

        if seam_side == "left":
            start = (x0, y0)
            path = [(x1, y0, e_x), (x1, y1, e_y), (x0, y1, e_x), (x0, y0, e_y)]
        else:
            start = (x1, y0)
            path = [(x0, y0, e_x), (x0, y1, e_y), (x1, y1, e_x), (x1, y0, e_y)]

        if is_first_perim and not skip_approach:
            result.append("G10")
            result.append(f"G1 X{start[0]:.3f} Y{start[1]:.3f} F{int(speed_travel * 60)}")
            result.append("G11")
        elif not is_first_perim:
            result.append(f"G1 X{start[0]:.3f} Y{start[1]:.3f} F{int(speed_travel * 60)}")

        for px, py, e in path:
            result.append(f"G1 X{px:.3f} Y{py:.3f} E{e} F{f_print}")
    return result


def draw_tick_marks(cx, cy, n_ticks, is_first):
    result = []
    half = column_size / 2
    front_y = cy - half
    tick_len = 2.0
    tick_spacing = 2.0
    total_width = (n_ticks - 1) * tick_spacing
    start_x = cx - total_width / 2

    for t in range(n_ticks):
        tx = start_x + t * tick_spacing
        ty0 = front_y - 0.5
        ty1 = front_y - 0.5 - tick_len
        f = int(speed_first * 60 if is_first else speed_perim * 60)

        result.append("G10")
        result.append(f"G1 X{tx:.3f} Y{ty0:.3f} F{int(speed_travel * 60)}")
        result.append("G11")

        dist = abs(ty1 - ty0)
        e = round(dist * e_per_mm, 4)
        result.append(f"G1 X{tx:.3f} Y{ty1:.3f} E{e} F{f}")
    return result


for layer_num in range(n_layers):
    z = round((layer_num + 1) * layer_height, 3)
    is_first = (layer_num == 0)

    retract_len = round(retract_length_start + (layer_num / n_layers) * (retract_length_end - retract_length_start), 2)

    lines.append(f"; Layer {layer_num}, Z={z:.3f}, retract_length={retract_len}mm")
    lines.append(f"G1 Z{z:.3f} F300")

    if layer_num == 1:
        lines.append(f"M140 S{bed_temp_rest}")
        lines.append(f"M106 S{fan_s}")

    for t_idx in range(n_towers):
        tcx, tcy = tower_centers[t_idx]
        rspeed = retract_speeds[t_idx]

        lines.append(f"SET_RETRACTION RETRACT_LENGTH={retract_len} RETRACT_SPEED={rspeed} UNRETRACT_SPEED={rspeed}")

        col_left_cx = tcx - (column_gap / 2 + column_size / 2)
        col_right_cx = tcx + (column_gap / 2 + column_size / 2)

        lines.extend(draw_column(col_left_cx, tcy, is_first, seam_side="left"))

        half = column_size / 2
        inner_offset = (n_perimeters - 1) * line_width
        detour_y = tcy - half - 3.0
        right_inner_x1 = col_right_cx + half - inner_offset
        right_inner_y0 = tcy - half + inner_offset
        lines.append("G10")
        lines.append(f"G1 Y{detour_y:.3f} F{int(speed_travel * 60)}")
        lines.append(f"G1 X{right_inner_x1:.3f} F{int(speed_travel * 60)}")
        lines.append(f"G1 Y{right_inner_y0:.3f} F{int(speed_travel * 60)}")
        lines.append("G11")

        lines.extend(draw_column(col_right_cx, tcy, is_first, skip_approach=True, seam_side="right"))

        if layer_num <= 2:
            lines.extend(draw_tick_marks(col_left_cx, tcy, t_idx + 1, is_first))

    lines.append("")

lines.append("")
lines.append("G1 Z150 F600")
lines.append("END_PRINT")

output_path = "/tmp/retraction_test.gcode"
with open(output_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} lines, {n_layers} layers, {n_towers} towers")
print(f"Retract speeds: {', '.join(f'{s}mm/s' for s in retract_speeds)}")
print(f"Retract length: {retract_length_start} -> {retract_length_end}mm over {total_height}mm height")
print(f"Tower centers: {', '.join(f'X={c[0]:.1f}' for c in tower_centers)}")
print(f"Mesh area: X={min_x}-{max_x}, Y={min_y}-{max_y}")
print(f"Output: {output_path}")
