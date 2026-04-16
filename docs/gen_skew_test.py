#!/usr/bin/env python3
"""Generate skew correction test G-code for ASA calibration.

Based on Klipper's skew_correction requirements.
https://www.klipper3d.org/Skew_Correction.html

Thin 140x100mm rectangle, 3 layers tall, single perimeter.
Centered on the bed. Klipper needs 3 measurements:
  - AC (diagonal, front-left to back-right)
  - BD (diagonal, front-right to back-left)
  - AD (side, front-left to back-left)

Corners labeled (looking from front):
  D ---- C
  |      |     140mm wide (X), 100mm tall (Y)
  A ---- B

A = front-left (1 tick)
B = front-right (2 ticks)
C = back-right (3 ticks)
D = back-left (4 ticks)

Ticks are small lines extending outward from each corner.
Different count per corner for identification.

PA=0.68, EM=0.96, retract 2.28mm@40mm/s, fan 15%, accel=3000, SCV=5.
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

rect_w = 140.0
rect_h = 100.0
n_layers = 3
speed_print = 60
speed_first = 20
speed_travel = 200

retract_length = 2.28
retract_speed = 40

bed_x_min = 4
bed_x_max = 222
bed_y_min = 7
bed_y_max = 226

bed_cx = (bed_x_min + bed_x_max) / 2.0
bed_cy = (bed_y_min + bed_y_max) / 2.0

r_x_min = bed_cx - rect_w / 2.0
r_x_max = bed_cx + rect_w / 2.0
r_y_min = bed_cy - rect_h / 2.0
r_y_max = bed_cy + rect_h / 2.0

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area

lines = []


def G(cmd):
    lines.append(cmd)


def extrude_to(x, y, speed, e_state):
    dist = math.sqrt((x - e_state["x"]) ** 2 + (y - e_state["y"]) ** 2)
    e_state["e"] += dist * e_per_mm
    G(f"G1 X{x:.3f} Y{y:.3f} E{e_state['e']:.5f} F{speed * 60}")
    e_state["x"] = x
    e_state["y"] = y


def travel_to(x, y):
    G("G10")
    G(f"G0 X{x:.3f} Y{y:.3f} F{speed_travel * 60}")
    G("G11")


G("; Skew correction test - 140x100mm rectangle, 3 layers")
G(f"; Corners: A({r_x_min:.1f},{r_y_min:.1f}) B({r_x_max:.1f},{r_y_min:.1f}) C({r_x_max:.1f},{r_y_max:.1f}) D({r_x_min:.1f},{r_y_max:.1f})")
G("; Klipper SET_SKEW needs: AC (diagonal), BD (diagonal), AD (left side)")
G("; Corner marks: A=1tick B=2ticks C=3ticks D=4ticks")
G("")
G(f"M140 S{bed_temp_first}")
G(f"M104 S150")
G(f"START_PRINT_STAGE_ONE EXTRUDER_TEMP={nozzle_temp} BED_TEMP={bed_temp_rest} AREA_START={r_x_min:.1f},{r_y_min:.1f} AREA_END={r_x_max:.1f},{r_y_max:.1f}")
G(f"M109 S{nozzle_temp}")
G(f"SET_PRESSURE_ADVANCE ADVANCE={pressure_advance}")
G(f"SET_RETRACTION RETRACT_LENGTH={retract_length} RETRACT_SPEED={retract_speed} UNRETRACT_SPEED={retract_speed}")
G(f"M221 S{em_pct}")
G(f"SET_VELOCITY_LIMIT ACCEL=3000")
G(f"SET_VELOCITY_LIMIT SQUARE_CORNER_VELOCITY=5")
G("SET_SKEW CLEAR=1")
G(f"START_PRINT_STAGE_TWO_04")
G("")

G("G92 E0")

e_state = {"x": 0.0, "y": 0.0, "e": 0.0}

tick_len = 6.0
tick_gap = 3.0
tick_spacing = 3.0

corners = [
    ("A", r_x_min, r_y_min, 0, -1, 1, 1),
    ("B", r_x_max, r_y_min, 0, -1, 2, -1),
    ("C", r_x_max, r_y_max, 0, 1, 3, -1),
    ("D", r_x_min, r_y_max, 0, 1, 4, 1),
]

for layer in range(n_layers):
    z = (layer + 1) * layer_height
    speed = speed_first if layer == 0 else speed_print

    G(f"; Layer {layer}, Z={z:.2f}")
    G(f"G0 Z{z:.3f} F600")

    if layer == 0:
        G(f"M140 S{bed_temp_rest}")
        fan_val = int(255 * fan_pct / 100)
        G(f"M106 S{fan_val}")

    travel_to(r_x_min, r_y_min)
    e_state["x"] = r_x_min
    e_state["y"] = r_y_min

    extrude_to(r_x_max, r_y_min, speed, e_state)
    extrude_to(r_x_max, r_y_max, speed, e_state)
    extrude_to(r_x_min, r_y_max, speed, e_state)
    extrude_to(r_x_min, r_y_min, speed, e_state)

    if layer <= 1:
        for corner_name, cx, cy, dx, dy, n_ticks, x_dir in corners:
            G(f"; Corner {corner_name} - {n_ticks} tick(s)")
            start_x = cx + x_dir * tick_gap
            for t in range(n_ticks):
                tx = start_x + x_dir * t * tick_spacing
                ty = cy + dy * tick_gap
                travel_to(tx, ty)
                e_state["x"] = tx
                e_state["y"] = ty
                extrude_to(tx, ty + dy * tick_len, speed, e_state)

G("")
G("; Print complete")
G("; Measure with calipers:")
G(";   AC = front-left (1 tick) to back-right (3 ticks) - diagonal")
G(";   BD = front-right (2 ticks) to back-left (4 ticks) - diagonal")
G(";   AD = front-left (1 tick) to back-left (4 ticks) - left side")
G("; Then: SET_SKEW XY=<AC>,<BD>,<AD>")
G("G1 Z150 F600")
G("END_PRINT")

output_path = "/tmp/skew_test.gcode"
with open(output_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} lines to {output_path}")
print(f"Rectangle: {rect_w}x{rect_h}mm centered at ({bed_cx:.1f}, {bed_cy:.1f})")
print(f"Corners: A({r_x_min:.1f},{r_y_min:.1f}) B({r_x_max:.1f},{r_y_min:.1f}) C({r_x_max:.1f},{r_y_max:.1f}) D({r_x_min:.1f},{r_y_max:.1f})")
print(f"Layers: {n_layers}, height: {n_layers * layer_height:.1f}mm")
print(f"Corner marks: A=1tick  B=2ticks  C=3ticks  D=4ticks")
print("Measure: AC (diagonal), BD (diagonal), AD (left side)")
print("Then: SET_SKEW XY=<AC>,<BD>,<AD>")
