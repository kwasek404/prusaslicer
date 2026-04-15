#!/usr/bin/env python3
"""Generate pressure advance calibration tower G-code for ASA.

Square tower 60x60mm, 50mm tall, 0.3mm layers.
PA increases linearly with height: 0.0 at Z=0 to 1.0 at Z=50.
SET_PRESSURE_ADVANCE issued at each layer.
2 perimeters (outer + inner) at 80mm/s to make PA effects visible.

Result: inspect tower for cleanest corners. PA = Z_best * (1.0 / 50).
With 0.020 PA/mm, Z=34mm => PA=0.68.
"""

import math

layer_height = 0.3
line_width = 0.45
filament_d = 1.75
nozzle_temp = 265
bed_temp_first = 120
bed_temp_rest = 95
total_height = 50.0
tower_size = 60.0
n_perimeters = 2
pa_start = 0.0
pa_end = 1.0
speed_perim = 80
speed_first = 15
speed_travel = 200
fan_pct = 15

cx = 115.0
cy = 115.0

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area

n_layers = int(total_height / layer_height)
pa_per_layer = (pa_end - pa_start) / n_layers

fan_s = int(round(fan_pct * 255 / 100))

half = tower_size / 2
min_x = int(cx - half)
max_x = int(cx + half)
min_y = int(cy - half)
max_y = int(cy + half)

lines = []
lines.append("; Pressure Advance Calibration Tower - ASA")
lines.append(f"; {tower_size}x{tower_size}mm, {total_height}mm tall, {n_perimeters} perimeters")
lines.append(f"; PA range: {pa_start} to {pa_end} (linear with height)")
lines.append(f"; PA per mm: {(pa_end - pa_start) / total_height:.4f}")
lines.append(f"; Layer height: {layer_height}mm, Line width: {line_width}mm")
lines.append(f"; Perimeter speed: {speed_perim}mm/s (to make PA visible)")
lines.append(f"; Read result: PA = Z_mm * {(pa_end - pa_start) / total_height:.4f}")
lines.append("")

lines.append(f"SET_PRESSURE_ADVANCE ADVANCE={pa_start}")
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

for layer_num in range(n_layers):
    z = round((layer_num + 1) * layer_height, 3)
    is_first = (layer_num == 0)
    pa = round(pa_start + layer_num * pa_per_layer, 4)

    lines.append(f"; Layer {layer_num}, Z={z:.3f}, PA={pa:.4f}")
    lines.append(f"G1 Z{z:.3f} F300")
    lines.append(f"SET_PRESSURE_ADVANCE ADVANCE={pa:.4f}")

    if layer_num == 1:
        lines.append(f"M140 S{bed_temp_rest}")
        lines.append(f"M106 S{fan_s}")

    f_print = int(speed_first * 60 if is_first else speed_perim * 60)

    for p in range(n_perimeters):
        offset = p * line_width
        x0 = cx - half + offset
        y0 = cy - half + offset
        x1 = cx + half - offset
        y1 = cy + half - offset

        side_x = x1 - x0
        side_y = y1 - y0
        e_x = round(side_x * e_per_mm, 4)
        e_y = round(side_y * e_per_mm, 4)

        lines.append("G10")
        lines.append(f"G1 X{x0:.3f} Y{y0:.3f} F{int(speed_travel * 60)}")
        lines.append("G11")

        lines.append(f"G1 X{x1:.3f} Y{y0:.3f} E{e_x} F{f_print}")
        lines.append(f"G1 X{x1:.3f} Y{y1:.3f} E{e_y} F{f_print}")
        lines.append(f"G1 X{x0:.3f} Y{y1:.3f} E{e_x} F{f_print}")
        lines.append(f"G1 X{x0:.3f} Y{y0:.3f} E{e_y} F{f_print}")

lines.append("")
lines.append("G1 Z150 F600")
lines.append("END_PRINT")

with open("/tmp/square_tower_pa.gcode", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} lines, {n_layers} layers")
print(f"PA range: {pa_start} to {pa_end}, step per layer: {pa_per_layer:.4f}")
print(f"Tower center: X={cx}, Y={cy}")
print(f"Mesh area: X={min_x}-{max_x}, Y={min_y}-{max_y}")
