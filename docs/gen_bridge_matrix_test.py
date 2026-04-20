#!/usr/bin/env python3
"""Bridge speed/flow matrix calibration test for ASA on Klipper Ender-3.

5x5 matrix:
  rows (Y, front to back): bridge_flow_ratio = [0.7, 0.8, 0.9, 1.0, 1.1]
  cols (X, left to right): bridge_speed = [20, 30, 40, 50, 60] mm/s

Each cell:
  - Two rectangular towers (4 x 10 mm footprint, 8 mm tall)
  - Bottom 2 layers solid (adhesion), middle 76 layers hollow with 2 perimeters,
    top 2 layers solid (bridge anchor)
  - Bridge: 25 parallel lines spanning the 30 mm air gap between towers
  - Bridge layer at z = 8.4 mm (tower top + 0.4 mm thick bridge height)

Constants for all cells:
  - extruder 265 C, bed 120 C first layer / 95 C rest
  - fan 15% constant from layer 0
  - pressure_advance 0.68, M221 S96 (extrusion multiplier 0.96)
  - firmware retraction 2.28 mm at 40 mm/s
  - max_accel 1000, square_corner_velocity 5
  - skew correction loaded automatically by START_PRINT_STAGE_TWO_04

Output: /tmp/bridge_matrix_test.gcode
"""

import math

# === Geometry ===
TOWER_X = 4.0
TOWER_Y = 10.0
BRIDGE_X = 30.0
TOWER_H = 8.0
LAYER_H = 0.1
N_LAYERS = int(round(TOWER_H / LAYER_H))  # 80
N_BOTTOM_SOLID = 2
N_TOP_SOLID = 2
NOZZLE = 0.4
LINE_W = 0.4
FILAMENT_D = 1.75
BRIDGE_H = 0.4  # thick bridge layer thickness = nozzle diameter

GAP_X = 6.0
GAP_Y = 6.0
N = 5
CELL_X = TOWER_X * 2 + BRIDGE_X  # 38
CELL_Y = TOWER_Y                  # 10
PITCH_X = CELL_X + GAP_X          # 44
PITCH_Y = CELL_Y + GAP_Y          # 16
TOTAL_X = N * CELL_X + (N - 1) * GAP_X  # 214
TOTAL_Y = N * CELL_Y + (N - 1) * GAP_Y  # 74

# Bed printable area for nozzle: X 4..222, Y 7..226
ORIGIN_X = 4 + (218 - TOTAL_X) / 2  # 6.0
ORIGIN_Y = 7 + (219 - TOTAL_Y) / 2  # 79.5

flow_ratios = [0.7, 0.8, 0.9, 1.0, 1.1]
speeds_mms = [20, 30, 40, 50, 60]

# === Speeds ===
PERIM_S = 60
INFILL_S = 60
FIRST_LAYER_S = 20
TRAVEL_S = 200


def f(s):
    """Convert mm/s to mm/min."""
    return int(s * 60)


# === Extrusion ===
def e_normal(length, line_w=LINE_W, layer_h=LAYER_H, flow=1.0):
    cs = line_w * layer_h
    return (cs * length * flow) / (math.pi * (FILAMENT_D / 2) ** 2)


def e_bridge(length, flow=1.0):
    cs = math.pi * (NOZZLE / 2) ** 2
    return (cs * length * flow) / (math.pi * (FILAMENT_D / 2) ** 2)


# === Output buffer ===
gcode = []


def emit(s=""):
    gcode.append(s)


# === Header ===
emit("; Bridge speed/flow calibration matrix 5x5")
emit("; ASA, Ender-3 BLTouch, Klipper")
emit(";")
emit("; Matrix layout (looking at bed from above, front = Y_min):")
emit(";")
emit(";   ROWS (front -> back, increasing Y): bridge_flow_ratio")
for i, fr in enumerate(flow_ratios):
    cy = ORIGIN_Y + i * PITCH_Y
    emit(f";     row {i} (Y={cy:.1f} mm): flow_ratio = {fr}")
emit(";")
emit(";   COLS (left -> right, increasing X): bridge_speed mm/s")
for i, sp in enumerate(speeds_mms):
    cx = ORIGIN_X + i * PITCH_X
    emit(f";     col {i} (X={cx:.1f} mm): speed = {sp} mm/s")
emit(";")
emit(f"; Cell footprint: tower(4) + bridge(30) + tower(4) = {CELL_X} mm X, {CELL_Y} mm Y")
emit(f"; Total bed footprint: {TOTAL_X} x {TOTAL_Y} mm, origin ({ORIGIN_X}, {ORIGIN_Y})")
emit(f"; Tower {TOWER_H} mm tall, hollow w/ 2 perimeters,"
     f" {N_BOTTOM_SOLID} solid bottom + {N_TOP_SOLID} solid top layers")
emit(f"; Bridge: 25 parallel lines, layer thickness {BRIDGE_H} mm at z={TOWER_H + BRIDGE_H:.1f}")
emit(";")
emit("; Constants: temp 265C, bed 120/95C, fan 15%, PA=0.68, EM=0.96")
emit("")

# === Start print ===
emit("M190 S0")
emit("M104 S0")
emit("START_PRINT_STAGE_ONE BED_TEMP=120")
emit("G4 P60000")
mesh_xmin = ORIGIN_X
mesh_ymin = ORIGIN_Y
mesh_xmax = ORIGIN_X + TOTAL_X
mesh_ymax = ORIGIN_Y + TOTAL_Y
emit(
    f"START_PRINT_STAGE_TWO_04 EXTRUDER_TEMP=265"
    f" MESH_AREA_START_X={mesh_xmin:.2f} MESH_AREA_START_Y={mesh_ymin:.2f}"
    f" MESH_AREA_END_X={mesh_xmax:.2f} MESH_AREA_END_Y={mesh_ymax:.2f}"
)
emit("SET_PRESSURE_ADVANCE ADVANCE=0.68")
emit("SET_RETRACTION RETRACT_LENGTH=2.28 RETRACT_SPEED=40 UNRETRACT_SPEED=40")
emit("M221 S96")
emit("M106 S38 ; fan 15%")
emit("G92 E0")
emit("M83 ; relative E")
emit("")


# === Cell coords ===
def tower_corners(row, col, side):
    """Return (x_min, y_min, x_max, y_max) for left (side=0) or right (side=1) tower."""
    cx = ORIGIN_X + col * PITCH_X
    cy = ORIGIN_Y + row * PITCH_Y
    if side == 0:
        return cx, cy, cx + TOWER_X, cy + TOWER_Y
    return cx + TOWER_X + BRIDGE_X, cy, cx + CELL_X, cy + TOWER_Y


def perim_rectangle(x_min, y_min, x_max, y_max, speed_s, inset=0.0):
    """Emit moves for one rectangular perimeter loop, inset inward from given bounds."""
    x0, y0 = x_min + inset, y_min + inset
    x1, y1 = x_max - inset, y_max - inset
    emit(f"G1 X{x0:.3f} Y{y0:.3f} F{f(TRAVEL_S)}")
    emit("G11")
    pts = [(x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    cx, cy = x0, y0
    for nx, ny in pts:
        d = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
        e = e_normal(d)
        emit(f"G1 X{nx:.3f} Y{ny:.3f} E{e:.5f} F{f(speed_s)}")
        cx, cy = nx, ny
    emit("G10")


def solid_infill(x_min, y_min, x_max, y_max, speed_s, inset=2 * LINE_W):
    """Rectilinear infill inside the inset bounds."""
    x0, y0 = x_min + inset, y_min + inset
    x1, y1 = x_max - inset, y_max - inset
    if y1 - y0 < LINE_W or x1 - x0 < LINE_W:
        return
    n_lines = max(1, int(round((y1 - y0) / LINE_W)) + 1)
    emit(f"G1 X{x0:.3f} Y{y0:.3f} F{f(TRAVEL_S)}")
    emit("G11")
    for i in range(n_lines):
        y = min(y0 + i * LINE_W, y1)
        if i % 2 == 0:
            xs, xe = x0, x1
        else:
            xs, xe = x1, x0
        if i > 0:
            # short Y travel inside the loop, extrude little
            d = LINE_W
            e = e_normal(d)
            emit(f"G1 X{xs:.3f} Y{y:.3f} E{e:.5f} F{f(speed_s)}")
        d = abs(xe - xs)
        e = e_normal(d)
        emit(f"G1 X{xe:.3f} Y{y:.3f} E{e:.5f} F{f(speed_s)}")
    emit("G10")


def print_tower_layer(x_min, y_min, x_max, y_max, speed_s, solid):
    perim_rectangle(x_min, y_min, x_max, y_max, speed_s, inset=0.0)
    perim_rectangle(x_min, y_min, x_max, y_max, speed_s, inset=LINE_W)
    if solid:
        solid_infill(x_min, y_min, x_max, y_max, speed_s)


# === Tower layers ===
for layer in range(N_LAYERS):
    z = (layer + 1) * LAYER_H
    is_first = layer == 0
    is_solid = layer < N_BOTTOM_SOLID or layer >= N_LAYERS - N_TOP_SOLID
    sp = FIRST_LAYER_S if is_first else PERIM_S
    label = "SOLID" if is_solid else "hollow"
    emit(f"; --- Layer {layer + 1}/{N_LAYERS} z={z:.3f} {label} ---")
    if layer == 1:
        emit("M140 S95 ; drop bed temp after first layer")
    emit(f"G1 Z{z:.3f} F{f(TRAVEL_S)}")
    for row in range(N):
        for col in range(N):
            for side in range(2):
                x0, y0, x1, y1 = tower_corners(row, col, side)
                print_tower_layer(x0, y0, x1, y1, sp, is_solid)

# === Bridge layer ===
bridge_z = TOWER_H + BRIDGE_H
emit("")
emit(f"; ===== BRIDGE LAYER z={bridge_z:.3f} (thick bridge, height {BRIDGE_H} mm) =====")
emit("")
emit(f"G1 Z{bridge_z:.3f} F{f(TRAVEL_S)}")
n_lines = int(round(TOWER_Y / LINE_W))  # 25
margin = (TOWER_Y - (n_lines - 1) * LINE_W) / 2
for row in range(N):
    flow = flow_ratios[row]
    for col in range(N):
        speed_s = speeds_mms[col]
        cx = ORIGIN_X + col * PITCH_X
        cy = ORIGIN_Y + row * PITCH_Y
        emit(f"; Cell row={row} col={col}  flow={flow}  speed={speed_s} mm/s")
        first_y = cy + margin
        emit(f"G1 X{cx:.3f} Y{first_y:.3f} F{f(TRAVEL_S)}")
        emit("G11")
        prev_x, prev_y = cx, first_y
        for i in range(n_lines):
            y = cy + margin + i * LINE_W
            if i % 2 == 0:
                xs, xe = cx, cx + CELL_X
            else:
                xs, xe = cx + CELL_X, cx
            if i > 0:
                d = ((xs - prev_x) ** 2 + (y - prev_y) ** 2) ** 0.5
                e = e_bridge(d, flow=flow)
                emit(f"G1 X{xs:.3f} Y{y:.3f} E{e:.5f} F{f(speed_s)}")
            d = abs(xe - xs)
            e = e_bridge(d, flow=flow)
            emit(f"G1 X{xe:.3f} Y{y:.3f} E{e:.5f} F{f(speed_s)}")
            prev_x, prev_y = xe, y
        emit("G10")
        emit("")

# === End ===
emit("G1 Z150 F600")
emit("END_PRINT")

out_path = "/tmp/bridge_matrix_test.gcode"
with open(out_path, "w") as fp:
    fp.write("\n".join(gcode))
print(f"Wrote {len(gcode)} lines to {out_path}")
print(f"Footprint: {TOTAL_X} mm X x {TOTAL_Y} mm Y, origin ({ORIGIN_X}, {ORIGIN_Y})")
print(f"25 cells, 80 tower layers + 1 bridge layer at z={bridge_z:.1f}")
