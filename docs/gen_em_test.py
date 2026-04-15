#!/usr/bin/env python3
"""Generate extrusion multiplier test G-code for ASA calibration.

5 cubes 30x30x3mm with EM values: 0.90, 0.93, 0.96, 0.99, 1.02.
2 perimeters, solid monotonic line infill, 10 layers at 0.3mm.
Tick marks on front face for identification (1-5 ticks).
M221 switched per-cube within each layer.

Speeds: perim 30, solid_infill 20, top_solid 15, first_layer 15, travel 200 mm/s.
Fan: 15% (M106 S38) from layer 1, off on first layer.
PA=0.68, firmware retraction G10/G11.
"""

import math

layer_height = 0.3
line_width = 0.45
filament_d = 1.75
nozzle_temp = 265
bed_temp_first = 120
bed_temp_rest = 95
n_layers = 10
cube_size = 30.0
n_perimeters = 2
pressure_advance = 0.68
fan_pct = 15

speed_perim = 30
speed_infill = 20
speed_top = 15
speed_first = 15
speed_travel = 200

em_values = [0.90, 0.93, 0.96, 0.99, 1.02]
n_cubes = len(em_values)

cube_spacing = (222 - 4 - cube_size) / (n_cubes - 1)
cube_centers = []
for i in range(n_cubes):
    cx = 4 + cube_size / 2 + i * cube_spacing
    cy = 115.0
    cube_centers.append((cx, cy))

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area

fan_s = int(round(fan_pct * 255 / 100))

min_x = int(cube_centers[0][0] - cube_size / 2)
max_x = int(cube_centers[-1][0] + cube_size / 2)
min_y = int(cube_centers[0][1] - cube_size / 2)
max_y = int(cube_centers[0][1] + cube_size / 2)

lines = []
lines.append("; Extrusion Multiplier Test - ASA")
lines.append(f"; {n_cubes} cubes, EM values: {', '.join(f'{v:.2f}' for v in em_values)}")
lines.append(f"; {cube_size}x{cube_size}x{n_layers * layer_height:.1f}mm, {n_perimeters} perimeters, solid infill")
lines.append(f"; Layer height: {layer_height}mm, Line width: {line_width}mm")
lines.append(f"; Tick marks on front face: 1 tick = EM {em_values[0]:.2f}, 5 ticks = EM {em_values[-1]:.2f}")
lines.append(f"; PA={pressure_advance}, Fan={fan_pct}%, Firmware retraction")
lines.append("")

lines.append(f"SET_PRESSURE_ADVANCE ADVANCE={pressure_advance}")
lines.append("SET_RETRACTION RETRACT_LENGTH=3.5")
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


def extrude_line(x0, y0, x1, y1, speed_mm_s, is_first):
    dist = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    e = round(dist * e_per_mm, 4)
    f = int(speed_first * 60 if is_first else speed_mm_s * 60)
    return f"G1 X{x1:.3f} Y{y1:.3f} E{e} F{f}"


def draw_perimeters(cx, cy, is_first):
    result = []
    half = cube_size / 2
    for p in range(n_perimeters):
        offset = p * line_width
        x0 = cx - half + offset
        y0 = cy - half + offset
        x1 = cx + half - offset
        y1 = cy + half - offset

        if p == 0:
            result.append("G10")
            result.append(f"G1 X{x0:.3f} Y{y0:.3f} F{int(speed_travel * 60)}")
            result.append("G11")
        else:
            result.append(f"G1 X{x0:.3f} Y{y0:.3f} F{int(speed_travel * 60)}")

        result.append(extrude_line(x0, y0, x1, y0, speed_perim, is_first))
        result.append(extrude_line(x1, y0, x1, y1, speed_perim, is_first))
        result.append(extrude_line(x1, y1, x0, y1, speed_perim, is_first))
        result.append(extrude_line(x0, y1, x0, y0, speed_perim, is_first))
    return result


def draw_infill(cx, cy, layer_num, is_first, is_top):
    result = []
    half = cube_size / 2
    inset = n_perimeters * line_width
    x0 = cx - half + inset
    y0 = cy - half + inset
    x1 = cx + half - inset
    y1 = cy + half - inset

    spd = speed_top if is_top else speed_infill

    if layer_num % 2 == 0:
        y = y0
        direction = 1
        while y <= y1:
            if direction == 1:
                result.append(extrude_line(x0, y, x1, y, spd, is_first))
            else:
                result.append(extrude_line(x1, y, x0, y, spd, is_first))
            y_next = round(y + line_width, 3)
            if y_next <= y1:
                if direction == 1:
                    result.append(f"G1 Y{y_next:.3f} E{round(line_width * e_per_mm, 4)} F{int(spd * 60)}")
                else:
                    result.append(f"G1 Y{y_next:.3f} E{round(line_width * e_per_mm, 4)} F{int(spd * 60)}")
            y = y_next
            direction *= -1
    else:
        x = x0
        direction = 1
        while x <= x1:
            if direction == 1:
                result.append(extrude_line(x, y0, x, y1, spd, is_first))
            else:
                result.append(extrude_line(x, y1, x, y0, spd, is_first))
            x_next = round(x + line_width, 3)
            if x_next <= x1:
                if direction == 1:
                    result.append(f"G1 X{x_next:.3f} E{round(line_width * e_per_mm, 4)} F{int(spd * 60)}")
                else:
                    result.append(f"G1 X{x_next:.3f} E{round(line_width * e_per_mm, 4)} F{int(spd * 60)}")
            x = x_next
            direction *= -1
    return result


def draw_tick_marks(cx, cy, n_ticks, layer_num, is_first):
    result = []
    half = cube_size / 2
    front_y = cy - half
    tick_len = 2.0
    tick_spacing = 3.0
    total_width = (n_ticks - 1) * tick_spacing
    start_x = cx - total_width / 2

    for t in range(n_ticks):
        tx = start_x + t * tick_spacing
        ty0 = front_y - 0.5
        ty1 = front_y - 0.5 - tick_len

        result.append("G10")
        result.append(f"G1 X{tx:.3f} Y{ty0:.3f} F{int(speed_travel * 60)}")
        result.append("G11")
        result.append(extrude_line(tx, ty0, tx, ty1, speed_perim, is_first))
    return result


for layer_num in range(n_layers):
    z = round((layer_num + 1) * layer_height, 3)
    is_first = (layer_num == 0)
    is_top = (layer_num >= n_layers - 3)

    lines.append(f"; Layer {layer_num}, Z={z:.3f}")
    lines.append(f"G1 Z{z:.3f} F300")

    if layer_num == 1:
        lines.append(f"M140 S{bed_temp_rest}")
        lines.append(f"M106 S{fan_s}")

    for cube_idx in range(n_cubes):
        em = em_values[cube_idx]
        cx, cy = cube_centers[cube_idx]
        m221_val = int(round(em * 100))

        lines.append(f"; Cube {cube_idx + 1} ({cube_idx + 1} ticks), EM={em:.2f}")
        lines.append(f"M221 S{m221_val}")

        lines.extend(draw_perimeters(cx, cy, is_first))

        inset = n_perimeters * line_width
        x0 = cx - cube_size / 2 + inset
        y0 = cy - cube_size / 2 + inset
        lines.append(f"G1 X{x0:.3f} Y{y0:.3f} F{int(speed_travel * 60)}")

        lines.extend(draw_infill(cx, cy, layer_num, is_first, is_top))

        if layer_num >= 2 and layer_num <= 4:
            lines.extend(draw_tick_marks(cx, cy, cube_idx + 1, layer_num, is_first))

    lines.append(f"M221 S100")
    lines.append("")

lines.append("")
lines.append("G1 Z150 F600")
lines.append("END_PRINT")

with open("/tmp/em_test.gcode", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} lines, {n_layers} layers, {n_cubes} cubes")
print(f"EM values: {', '.join(f'{v:.2f}' for v in em_values)}")
print(f"Cube centers: {', '.join(f'X={c[0]:.1f}' for c in cube_centers)}")
print(f"Mesh area: X={min_x}-{max_x}, Y={min_y}-{max_y}")
