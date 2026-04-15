#!/usr/bin/env python3
"""Generate speed/cooling matrix test G-code with overhang + bridge geometry.

4 towers at different print speeds (20/40/60/80 mm/s).
Each tower is a square column where each face overhangs at a constant angle:
  +X (right):  0deg from vertical (reference wall, no overhang)
  +Y (back):  20deg from vertical (mild overhang)
  -X (left):  35deg from vertical (moderate overhang)
  -Y (front): 50deg from vertical (aggressive overhang)

Additionally, each tower has a pair of bridge test columns placed behind it
(higher Y). Two 5x5mm pillars 15mm apart, with open bridges every ~5mm.
Bridges are fully visible from the side/below.

Fan decreases with height in 5mm bands: 100% -> 80% -> 60% -> 40% -> 20% -> 10% -> 0%.
Height: 35mm, layer: 0.3mm, 2 perimeters, inner-first.

Result: 4 speeds x 7 fan levels x (4 overhang angles + bridges).
"""

import math

layer_height = 0.3
line_width = 0.45
filament_d = 1.75
nozzle_temp = 265
bed_temp_first = 120
bed_temp_rest = 95
total_height = 35.0
base_size = 20.0
n_perimeters = 2
first_layer_speed = 20
travel_speed = 100

angle_right = 0
angle_top = 20
angle_left = 35
angle_bottom = 50

tan_r = math.tan(math.radians(angle_right))
tan_t = math.tan(math.radians(angle_top))
tan_l = math.tan(math.radians(angle_left))
tan_b = math.tan(math.radians(angle_bottom))

center_y = 65
towers = [
    ("20mm/s", 20, 39, center_y),
    ("40mm/s", 40, 89, center_y),
    ("60mm/s", 60, 139, center_y),
    ("80mm/s", 80, 189, center_y),
]

# Bridge test columns: two 5x5mm pillars per tower, 15mm gap, placed behind tower
pillar_size = 5.0
pillar_gap = 15.0
pillar_y_offset = 35.0  # distance from tower center to first pillar center

fan_bands = [
    (0.0, 100),
    (5.0, 80),
    (10.0, 60),
    (15.0, 40),
    (20.0, 20),
    (25.0, 10),
    (30.0, 0),
]

filament_area = math.pi * (filament_d / 2) ** 2
e_per_mm = (layer_height * line_width) / filament_area
n_layers = int(total_height / layer_height)
half = base_size / 2

bridge_every = round(5.0 / layer_height)
bridge_layers = {n for n in range(bridge_every, n_layers, bridge_every)}


def tower_bounds(cx, cy, layer_n):
    s = layer_n * layer_height
    return (
        cx - half - s * tan_l,
        cy - half - s * tan_b,
        cx + half + s * tan_r,
        cy + half + s * tan_t,
    )


def pillar_positions(cx, cy):
    """Return centers of two bridge pillars for a tower."""
    py = cy + pillar_y_offset
    p1_cx = cx - pillar_gap / 2
    p2_cx = cx + pillar_gap / 2
    return (p1_cx, py), (p2_cx, py)


def e_for(distance):
    return round(abs(distance) * e_per_mm, 4)


def draw_square(lines, x0, y0, x1, y1, f_print, f_travel, n_perim):
    """Draw n perimeters of a rectangle (inner-first)."""
    for p in range(n_perim - 1, -1, -1):
        off = p * line_width
        px0 = x0 + off
        py0 = y0 + off
        px1 = x1 - off
        py1 = y1 - off
        sx = px1 - px0
        sy = py1 - py0
        if sx <= 0 or sy <= 0:
            continue
        if p < n_perim - 1:
            lines.append(f"G1 X{px0:.3f} Y{py0:.3f} F{f_travel}")
        lines.append(f"G1 X{px1:.3f} Y{py0:.3f} E{e_for(sx)} F{f_print}")
        lines.append(f"G1 X{px1:.3f} Y{py1:.3f} E{e_for(sy)} F{f_print}")
        lines.append(f"G1 X{px0:.3f} Y{py1:.3f} E{e_for(sx)} F{f_print}")
        lines.append(f"G1 X{px0:.3f} Y{py0:.3f} E{e_for(sy)} F{f_print}")


# Compute mesh area
top_bounds = [tower_bounds(t[2], t[3], n_layers - 1) for t in towers]
all_pillar_pos = [pillar_positions(t[2], t[3]) for t in towers]

mesh_x0 = max(4, int(min(
    min(b[0] for b in top_bounds),
    min(p[0][0] - pillar_size / 2 for p in all_pillar_pos),
)))
mesh_y0 = max(7, int(min(b[1] for b in top_bounds)))
mesh_x1 = min(222, int(max(
    max(b[2] for b in top_bounds),
    max(p[1][0] + pillar_size / 2 for p in all_pillar_pos),
)) + 1)
mesh_y1 = min(226, int(max(
    max(b[3] for b in top_bounds),
    max(p[0][1] + pillar_size / 2 for p in all_pillar_pos),
)) + 1)

travel_y = max(7, mesh_y0 - 3)

G = []

G.append("; Speed/Cooling Overhang + Bridge Matrix Test")
G.append(f"; 4 towers: {', '.join(t[0]+' @ X='+str(t[2]) for t in towers)}")
G.append(f"; Face angles (deg from vertical): +X={angle_right}  +Y={angle_top}"
         f"  -X={angle_left}  -Y={angle_bottom}")
G.append(f"; Bridge pillars: {pillar_size}x{pillar_size}mm, {pillar_gap}mm gap,"
         f" bridges every {bridge_every} layers (~5mm)")
G.append("; Fan bottom->top: 100 / 80 / 60 / 40 / 20 / 10 / 0 %")
G.append(f"; Base {base_size}x{base_size}mm  height {total_height}mm  {n_layers} layers")
G.append(f"; Layer {layer_height}mm  width {line_width}mm  {n_perimeters} perimeters inner-first")
G.append(f"; Travel lane Y={travel_y}")
G.append("")
G.append("SET_PRESSURE_ADVANCE ADVANCE=0.68")
G.append("SET_RETRACTION RETRACT_LENGTH=2.28 RETRACT_SPEED=40 UNRETRACT_SPEED=40")
G.append("M221 S96")
G.append("")
G.append("M190 S0")
G.append("M104 S0")
G.append(f"START_PRINT_STAGE_ONE BED_TEMP={bed_temp_first}")
G.append("G4 P60000")
G.append(f"START_PRINT_STAGE_TWO_04 EXTRUDER_TEMP={nozzle_temp}"
         f" MESH_AREA_START_X={mesh_x0} MESH_AREA_START_Y={mesh_y0}"
         f" MESH_AREA_END_X={mesh_x1} MESH_AREA_END_Y={mesh_y1}")
G.append("")
G.append("M83")
G.append("G21")
G.append("G90")
G.append("")

current_fan = -1
F_travel = int(travel_speed * 60)

for layer_num in range(n_layers):
    z = round((layer_num + 1) * layer_height, 3)
    is_first = (layer_num == 0)
    is_bridge = layer_num in bridge_layers

    G.append(f"; --- Layer {layer_num}  Z={z:.3f}"
             f"{'  BRIDGE' if is_bridge else ''} ---")
    G.append(f"G1 Z{z:.3f} F300")

    if layer_num == 1:
        G.append(f"M140 S{bed_temp_rest}")

    if not is_first:
        for band_z, fan_pct in reversed(fan_bands):
            if z >= band_z + layer_height:
                if fan_pct != current_fan:
                    if fan_pct == 0:
                        G.append("M107")
                    else:
                        G.append(f"M106 S{int(round(fan_pct * 255 / 100))}")
                    G.append(f"; === Fan {fan_pct}% (Z >= {band_z}mm) ===")
                    current_fan = fan_pct
                break

    for t_idx, (label, speed, cx, cy) in enumerate(towers):
        spd = first_layer_speed if is_first else speed
        F_print = int(spd * 60)
        x0, y0, x1, y1 = tower_bounds(cx, cy, layer_num)

        # --- Travel to tower via safe lane ---
        G.append("G10")
        inner_x0 = x0 + line_width
        inner_y0 = y0 + line_width
        G.append(f"G1 Y{travel_y:.3f} F{F_travel}")
        G.append(f"G1 X{inner_x0:.3f} F{F_travel}")
        G.append(f"G1 Y{inner_y0:.3f} F{F_travel}")
        G.append("G11")

        # --- Tower perimeters (inner first) ---
        draw_square(G, x0, y0, x1, y1, F_print, F_travel, n_perimeters)

        # --- Tick marks on layers 0-2 (right side, 0deg face) ---
        if layer_num <= 2:
            n_ticks = t_idx + 1
            tick_len = 3.0
            tick_gap = 2.5
            tick_x = x1 + 2
            tick_y0_t = cy - (n_ticks - 1) * tick_gap / 2

            for tick in range(n_ticks):
                ty = tick_y0_t + tick * tick_gap
                G.append("G10")
                G.append(f"G1 X{tick_x:.3f} Y{ty:.3f} F{F_travel}")
                G.append("G11")
                G.append(f"G1 X{tick_x + tick_len:.3f} Y{ty:.3f}"
                         f" E{e_for(tick_len)} F{int(first_layer_speed * 60)}")

        # --- Bridge pillars + bridges ---
        (p1cx, p1cy), (p2cx, p2cy) = pillar_positions(cx, cy)
        ph = pillar_size / 2

        # Pillar 1 (left)
        G.append("G10")
        G.append(f"G1 Y{travel_y:.3f} F{F_travel}")
        G.append(f"G1 X{p1cx - ph + line_width:.3f} F{F_travel}")
        G.append(f"G1 Y{p1cy - ph + line_width:.3f} F{F_travel}")
        G.append("G11")
        draw_square(G, p1cx - ph, p1cy - ph,
                    p1cx + ph, p1cy + ph, F_print, F_travel, n_perimeters)

        # Pillar 2 (right)
        G.append("G10")
        G.append(f"G1 X{p2cx - ph + line_width:.3f} Y{p2cy - ph + line_width:.3f} F{F_travel}")
        G.append("G11")
        draw_square(G, p2cx - ph, p2cy - ph,
                    p2cx + ph, p2cy + ph, F_print, F_travel, n_perimeters)

        # Bridge between pillars (open, visible from below)
        if is_bridge:
            bx0 = p1cx + ph  # right edge of pillar 1
            bx1 = p2cx - ph  # left edge of pillar 2
            by0 = p1cy - ph + line_width
            by1 = p1cy + ph - line_width
            span = bx1 - bx0

            if span > line_width:
                n_lines = max(1, int((by1 - by0) / line_width))
                y_step = (by1 - by0) / n_lines

                G.append(f"; bridge span={span:.1f}mm, {n_lines+1} lines")

                for i in range(n_lines + 1):
                    by = by0 + i * y_step
                    if i % 2 == 0:
                        G.append(f"G1 X{bx0:.3f} Y{by:.3f} F{F_travel}")
                        G.append(f"G1 X{bx1:.3f} Y{by:.3f}"
                                 f" E{e_for(span)} F{F_print}")
                    else:
                        G.append(f"G1 X{bx1:.3f} Y{by:.3f}"
                                 f" E{e_for(y_step)} F{F_print}")
                        G.append(f"G1 X{bx0:.3f} Y{by:.3f}"
                                 f" E{e_for(span)} F{F_print}")

G.append("")
G.append("G1 Z150 F600")
G.append("END_PRINT")

output = "/tmp/speed_fan_test.gcode"
with open(output, "w") as f:
    f.write("\n".join(G) + "\n")

print(f"Generated {len(G)} lines, {n_layers} layers")
print(f"Towers: {', '.join(f'{t[0]} @ X={t[2]}' for t in towers)}")
print(f"Angles from vertical: +X={angle_right} +Y={angle_top}"
      f" -X={angle_left} -Y={angle_bottom}")
print(f"Pillars: {pillar_size}x{pillar_size}mm, gap={pillar_gap}mm,"
      f" Y offset={pillar_y_offset}mm from tower center")
print(f"Bridge layers: {sorted(bridge_layers)}")
print(f"Mesh: X={mesh_x0}-{mesh_x1}  Y={mesh_y0}-{mesh_y1}")
print(f"Fan: {', '.join(f'{b[1]}%@>={b[0]}mm' for b in fan_bands)}")

# Verify bounds
print("\nBounds check:")
for t_idx, (label, speed, cx, cy) in enumerate(towers):
    tb = tower_bounds(cx, cy, n_layers - 1)
    (p1c, _), (p2c, _) = pillar_positions(cx, cy)
    p_y_max = _ + pillar_size / 2
    print(f"  {label}: tower X=[{tb[0]:.1f}, {tb[2]:.1f}] Y=[{tb[1]:.1f}, {tb[3]:.1f}]"
          f"  pillars X=[{p1c - ph:.1f}, {p2c + ph:.1f}] Y_max={p_y_max:.1f}")

print(f"\nOutput: {output}")
