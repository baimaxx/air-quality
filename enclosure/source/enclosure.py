#!/usr/bin/env python3
"""Parametric enclosure for Waveshare ESP32-S3-Touch-LCD-2.8B.

Units: mm. Coordinate system follows Waveshare's official STEP model:
LCD faces +Z, USB is at the bottom (-Y), BOOT/RESET/TF/PWR are on +X.

v3.4 (JLC spec 27832 audit: no local thinning, thinner walls):
  Checked against the OFFICIAL jlc-3dp.cn design spec (27832), not the
  loose "wall > 0.8 mm" shorthand used earlier. Official SLA/resin numbers:
    - "推荐模型壁厚 2MM"; size-graded table: 50x50 mm -> 1.0 mm,
      100x100 mm -> 1.5 mm (our 56.9 x 74.8 mm case falls between).
    - Bosses / locators / clips / fasteners: minimum wall > 1.5 mm.
    - Fragile, overhanging structures: >= 2 mm recommended.
    - Hole dia vs depth (resin): phi 1.0 -> H 1-3, phi 1.5 -> H 1.5-4.5,
      phi 2.0 -> H 2-6 mm, i.e. H <= 3 x phi.
    - Hollow pins: wall > 2 mm.  Minimum drain hole 2.5 mm.
    - Assembly clearance (resin): 0.2 mm/side.  Hole tolerance +/- 0.3 mm,
      resin holes shrink up to 0.3 mm.  Accuracy +/- 0.2 mm under 100 mm.
    - Spliced parts: connecting bar wall > 1.5 mm, < 10 parts per file,
      2+ parts billed +0.5 CNY each; "one file one part" strongly advised.
  Consequences applied here:
    * The 14x22x1.2 mm rear recess is REMOVED. A phi 2.4 mm hole through a
      2.6 mm floor gives H/phi = 1.08, far below the 3x limit, so thinning
      was never needed for printability -- it only served CO2 diffusion and
      created the weakest, most post-processing-prone area of the part.
      The back is now a flat, uniform 2.0 mm plate.
    * wall 2.2 -> 1.8 mm, floor 2.6 -> 2.0 mm (still above the graded
      recommendation, and above the 1.5 mm fastener minimum).
      base_bottom -22.8 -> -22.2 so floor_top stays at -20.2: every boss,
      button, port, slider and sprue keeps its Z geometry. Total thickness
      24.1 -> 23.5 mm. Inner cavity grows 0.4 mm/side, which WIDENS the
      glass support ledge from 1.0 to 1.4 mm.
    * Counterbore 1.2 -> 1.0 mm to leave 1.0 mm of straight wall.
    * Vent holes 2.4 -> 2.5 mm = official minimum drain-hole diameter;
      H/phi = 0.8. Resin shrink leaves 2.2 mm, still > 2 mm.
    * Sprues 1.0 -> 1.6 mm to satisfy the spliced-part connecting-bar rule
      (cut with flush pliers rather than snapped by hand). NOTE: our one
      connected STL is still ONE 款 / one free slot, but JLC may bill
      +0.5 CNY per spliced part (2 parts = +1 CNY); see the PDF.
    * Thin ring bosses stay OD 5.0 / ID 2.8 (wall 1.1 mm). The spec's
      "hollow pin wall > 2 mm" targets locating pins; ours are short
      compression-only clamp spacers, and OD 6.8 would put the annular
      contact face outside the copper standoff's r=1.25..2.75 metal face.
      Documented as a conscious, justified deviation in audit_report.json.

v3.3 (one print slot): base + captured PWR slider are ONE connected STL.
  The slider is rotated flat and "parked" in the empty cavity, joined to the
  floor by two 1.0 mm breakaway sprues. After printing, snap the sprues,
  lift the slider out and load it into the PWR guide from inside as before.
  JLC free prints count "款" per uploaded model file and auto-detect parts
  inside a file, so a single connected body guarantees only one slot is used.
  The parked island sits 0.6 mm above the floor in an open pocket (no sealed
  cavity), its outline/bbox/volume are unchanged, and the sprue stubs land
  between the two fork tabs so they never affect switch grip.
  deliver: stl/base.stl only. reference/slider_standalone.stl is a spare.

v3.2 (narrow bezel + thin bosses + round-hole ventilation):
  * Front bezel: outline 66.0 x 86.0 -> 56.4 x 74.8, so the visible rim
    around the 52.9 x 71.3 glass is 1.75 mm per side (was 6.65 / 7.05).
    outer_r = pocket_r + bezel = 3.3 + 1.45 => the top lip is concentric
    with the glass pocket, so the 1.45 mm lip has constant corner width.
    The inner cavity corner is concentric too (r = 2.55).
  * Thin ring screw bosses restored under the four board standoffs:
    OD 5.0 / ID 2.8, OD 6.0 x 1.0 mm root flare, top at z = -10.2,
    i.e. 0.2 mm clear of the official copper standoff face (z = -10.0).
    The annular top (r 1.4..2.5) lands entirely inside the standoff's
    metal end face (r 1.25..2.75), so the screw's clamp load goes
    screw head -> floor -> boss -> copper standoff -> screw thread and
    never passes through the glass. The 0.2 mm cold gap means the glass
    is never pre-loaded by a shrunk/oversized printed boss.
  * Rear 16 x 10 mm sensor window replaced by a round-hole array: a
    14 x 22 x 1.2 mm recess thins the floor locally from 2.6 to 1.4 mm,
    then 4 x 6 = 24 holes of 2.4 mm are drilled through that thin wall.
    The left wall gets a mirrored 8-hole array (new); the right wall
    keeps its 8 holes. Three-face cross-ventilation, ~180 mm2 total.
    All internal ribs / baffles are gone.
  * Ports, flexure buttons and the captured PWR slider are re-referenced
    to the new right wall (x = 28.2); the button plungers got shorter
    because the wall now sits only ~2 mm from the board switches.

v3.1 (clean interior): removed bosses/ribs, floor 2.2 -> 2.6, no cover.
v3.0: verified against official 2024-10-31 STEP; rear screws into the
board's female standoffs; small LiPo + 10x20 mm SCD41 carrier; captured
PWR slider instead of an integral flexure.

Requires CadQuery 2.8: python3 enclosure.py
"""
from pathlib import Path
import json
import cadquery as cq

P = {
    # Enclosure: total thickness = split_z - base_bottom = 23.5 mm (v3.4)
    "outer_w": 56.4,
    "outer_h": 74.8,
    "outer_center_y": -2.0,
    "outer_r": 4.75,          # = pocket_r + bezel -> constant-width top lip
    # v3.4: official spec 27832 graded table says 50x50 mm resin -> 1.0 mm,
    # 100x100 mm -> 1.5 mm; fastener/locator/clip structures -> >1.5 mm.
    # 1.8 / 2.0 mm stays conservative while removing 0.4/0.6 mm of bulk.
    "wall": 1.8,
    "floor": 2.0,
    # Keep floor_top = base_bottom + floor = -20.2 exactly as v3.3, so all
    # bosses, buttons, ports and the parked slider keep their Z geometry.
    "base_bottom": -22.2,
    "split_z": 1.3,
    # Official panel (touch glass) -- front face is glass, no screw holes
    "panel_w": 52.90,
    "panel_h": 71.30,
    "panel_center_y": -2.0,
    "panel_clearance": 0.30,
    "pocket_r": 3.3,
    # Official board standoff centres (M2/M2.5 female thread, opens at -Z)
    "board_hole_x": 20.45,
    "board_hole_y_top": 27.35,
    "board_hole_y_bottom": -32.35,
    "standoff_bottom_z": -10.0,  # official board standoff face (opens toward -Z)
    # v3.2: thin ring bosses. OD 5.0 < standoff OD 5.5; ID 2.8 > bore 2.5.
    "boss_od": 5.0,
    "boss_id": 2.8,
    "boss_root_d": 6.0,
    "boss_root_h": 1.0,
    "boss_gap": 0.2,             # cold clearance, glass is never pre-loaded
    "screw_clearance_d": 2.8,    # M2/M2.5 + shrink/fit allowance
    "screw_head_d": 5.2,         # rear counterbore
    # v3.4: 1.0 mm counterbore leaves 1.0 mm straight wall in the 2.0 mm floor
    "screw_head_depth": 1.0,
    # Payload (edit these to match the real parts). No printed retaining ribs:
    # the cell and the SCD41 carrier are held with thin foam / double-sided tape.
    "battery_max": [28.0, 22.0, 5.0],
    "battery_center": [8.0, 8.0],
    "sensor_max": [10.0, 20.0, 10.0],   # SCD41 carrier, incl. sensor height
    "sensor_center": [5.0, -25.0],
    # v3.4: NO local thinning. The back is a flat 2.0 mm plate. A 2.5 mm
    # hole through 2.0 mm gives H/phi = 0.8 (spec allows H <= 3 x phi), so
    # the v3.2 recess was never needed for printability. "vent_recess" is
    # kept as the nominal vent FIELD (for documentation), depth = 0.
    "vent_recess": [16.0, 22.0, 0.0],   # w, h, depth (0 = no cut)
    "vent_cols": 4,
    "vent_rows": 6,
    "vent_pitch_x": 3.5,         # 1.0 mm land between 2.5 mm holes
    "vent_pitch_y": 3.5,
    "vent_d": 2.5,               # = official minimum drain-hole diameter
    "side_vent_ys": (-32.0, -27.0, -22.0, -17.0),
    "side_vent_zs": (-18.0, -14.5),
    "key_proud": 0.5,            # button cap projection beyond the side wall
    # v3.3: park the slider inside the tub so the order is one connected STL.
    "park_center": [4.5, 5.0],   # XY centre of the parked (flat) slider
    "park_gap": 0.6,             # open gap above the floor; resin can drain
    # v3.4: spec 27832 says spliced-part connecting bars must be > 1.5 mm.
    # 1.6 mm is cut with flush pliers instead of snapped by hand.
    "sprue_d": 1.6,
    "sprue_positions": [(2.5, 5.5), (6.5, 5.5)],  # between the fork tabs
    "sprue_embed": 0.30,         # bite into the parked slider body
}

ROOT = Path(__file__).resolve().parents[1]


def rr(w, h, r, z0, z1, cx=0.0, cy=0.0):
    """Rounded-rectangle prism in XY, extruded along Z."""
    sketch = cq.Sketch().rect(w, h).vertices().fillet(r)
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy)
            .placeSketch(sketch).extrude(z1 - z0))


def box_at(dx, dy, dz, cx, cy, cz):
    return cq.Workplane("XY").box(dx, dy, dz).translate((cx, cy, cz))


def cyl_at(d, z0, z1, x, y):
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .circle(d / 2).extrude(z1 - z0))


def rr_y(w, h, r, cx, cz, y0, y1):
    """Rounded rectangle in XZ, extruded along Y (bottom ports)."""
    cy = (y0 + y1) / 2
    depth = y1 - y0
    shape = None
    if w - 2 * r > 1e-6:
        shape = box_at(w - 2 * r, depth, h, cx, cy, cz)
    if h - 2 * r > 1e-6:
        middle = box_at(w, depth, h - 2 * r, cx, cy, cz)
        shape = middle if shape is None else shape.union(middle)
    for dx in (-(w / 2 - r), w / 2 - r):
        for dz in (-(h / 2 - r), h / 2 - r):
            cyl = cq.Solid.makeCylinder(
                r, depth, cq.Vector(cx + dx, y0, cz + dz), cq.Vector(0, 1, 0))
            rounded = cq.Workplane(obj=cyl)
            shape = rounded if shape is None else shape.union(rounded)
    return shape


def rr_x(w, h, r, cy, cz, x0, x1):
    """Rounded rectangle in YZ, extruded along X (right-side ports)."""
    cx = (x0 + x1) / 2
    depth = x1 - x0
    shape = None
    if w - 2 * r > 1e-6:
        shape = box_at(depth, w - 2 * r, h, cx, cy, cz)
    if h - 2 * r > 1e-6:
        middle = box_at(depth, w, h - 2 * r, cx, cy, cz)
        shape = middle if shape is None else shape.union(middle)
    for dy in (-(w / 2 - r), w / 2 - r):
        for dz in (-(h / 2 - r), h / 2 - r):
            cyl = cq.Solid.makeCylinder(
                r, depth, cq.Vector(x0, cy + dy, cz + dz), cq.Vector(1, 0, 0))
            rounded = cq.Workplane(obj=cyl)
            shape = rounded if shape is None else shape.union(rounded)
    return shape


def board_mount_points():
    return [(x, y) for x in (-P["board_hole_x"], P["board_hole_x"])
            for y in (P["board_hole_y_bottom"], P["board_hole_y_top"])]


def make_base():
    w, h, cy = P["outer_w"], P["outer_h"], P["outer_center_y"]
    z0, z1 = P["base_bottom"], P["split_z"]
    inner_w, inner_h = w - 2 * P["wall"], h - 2 * P["wall"]
    inner_r = P["pocket_r"] - (P["wall"] - (w - P["panel_w"]
                                            - 2 * P["panel_clearance"]) / 2)
    floor_top = z0 + P["floor"]
    right_x = w / 2
    ymin = cy - h / 2

    # One-piece open tub. The glass panel drops into the top recess and forms
    # the visible top face; no separate cover is printed.
    base = rr(w, h, P["outer_r"], z0, z1, cy=cy)
    base = base.cut(rr(inner_w, inner_h, inner_r, floor_top, 0.0, cy=cy))
    pocket_w = P["panel_w"] + 2 * P["panel_clearance"]
    pocket_h = P["panel_h"] + 2 * P["panel_clearance"]
    base = base.cut(rr(pocket_w, pocket_h, P["pocket_r"], -0.1, z1 + 0.2,
                       cy=P["panel_center_y"]))

    # Panel support ledge -- the only internal locating feature. The
    # 52.9 x 71.3 glass rests on this perimeter ring while the smaller LCD
    # rear passes through its 50 x 69 mm aperture.
    ledge = rr(inner_w, inner_h, inner_r, -2.0, 0.0, cy=cy)
    ledge = ledge.cut(rr(50.0, 69.0, 2.0, -2.2, 0.2, cy=-2.0))
    base = base.union(ledge)

    # v3.2: thin ring screw bosses. Annular top lands on the metal end face
    # of the board's copper standoff only -- never on the glass or the PCB
    # laminate. 0.2 mm cold gap prevents pre-load from SLA shrink.
    boss_top = P["standoff_bottom_z"] - P["boss_gap"]
    for x, y in board_mount_points():
        base = base.union(cyl_at(P["boss_root_d"], floor_top,
                                 floor_top + P["boss_root_h"], x, y))
        base = base.union(cyl_at(P["boss_od"], floor_top, boss_top, x, y))
        base = base.cut(cyl_at(P["boss_id"], z0 - 0.5, boss_top + 0.5, x, y))
        base = base.cut(cyl_at(P["screw_head_d"], z0 - 0.5,
                               z0 + P["screw_head_depth"], x, y))

    # v3.2: no battery cradle, no SCD41 ribs, no full-width partition, no
    # thermal lip. Cell and carrier are held with foam / double-sided tape.

    # Bottom side: rounded USB-C, UART and I2C openings. All internal corners
    # are radiused; cutting solids pass fully through the wall.
    for x, width, height, z, radius in [
        (0.0, 13.0, 7.0, -7.0, 3.0),
        (-12.65, 9.5, 6.0, -7.4, 2.8),
        (12.65, 9.5, 6.0, -7.4, 2.8),
    ]:
        base = base.cut(rr_y(width, height, radius, x, z,
                             ymin - 3.5, ymin + 3.5))

    # Right side: compact rounded TF opening.
    base = base.cut(rr_x(14.0, 3.2, 1.5, -6.85, -3.9,
                         right_x - 3.5, right_x + 3.5))

    def x_hole(d, y, z, x0=23.0, x1=31.5):
        return (cq.Workplane("YZ").workplane(offset=x0)
                .center(y, z).circle(d / 2).extrude(x1 - x0))

    def x_slot_y(length, height, y, z, x0=24.5, x1=31.5):
        return rr_x(length, height, height / 2, y, z, x0, x1)

    def x_slot_z(length, width, y, z, x0=24.5, x1=31.5):
        return rr_x(width, length, width / 2, y, z, x0, x1)

    # BOOT/RESET: long cantilever arms with rounded U slots and raised,
    # fully radiused finger pads. L/h = 9.5/1.6 = 5.9 (>5), slot ends are
    # round, and the plunger stops 0.18 mm short of the board switch.
    # Slot tops stop at z = -0.30 (not 0.0): a coplanar slot top and ledge
    # top creates a T-junction / non-manifold edge in the exported mesh.
    for y in (6.45, 16.30):
        base = base.cut(x_slot_z(10.3, 1.6, y - 3.8, -5.45))
        base = base.cut(x_slot_z(10.3, 1.6, y + 3.8, -5.45))
        base = base.cut(x_slot_y(9.2, 1.6, y, -10.60))
        # Open inner relief leaves a 1.6 mm thick, ~9.5 mm long arm.
        base = base.cut(box_at(1.2, 6.2, 9.45, 26.0, y, -5.075))
        base = base.union(x_hole(3.2, y, -6.7, 23.95, 26.8))
        base = base.union(rr_x(7.0, 7.0, 3.0, y, -6.7,
                               right_x - 0.2, right_x + P["key_proud"]))

    # PWR: 12 x 5 mm rounded window for a separate captured slider
    # (OpenAT Design Guide: switch body ~5 mm from wall, 12x5 opening for a
    # bare toggle). The slider body is taller than the window, so it is
    # retained behind the wall.
    base = base.cut(rr_x(12.0, 5.0, 1.5, -24.65, -7.0,
                         right_x - 2.7, right_x + 0.8))

    # RTC / system battery connectors face inward: no side holes.
    # IPEX1 is unused: rear wall kept closed apart from the header and vents.

    # Rear 2x12 female header access.
    base = base.cut(rr(11.0, 34.0, 1.5, z0 - 0.5, floor_top + 0.5,
                       cx=-17.65, cy=6.90))

    # v3.4 SCD41 ventilation: NO recess, NO local thinning. The back is a
    # uniform 2.0 mm plate; 4 x 6 = 24 holes of 2.5 mm go straight through
    # it. H/phi = 0.8, far inside the spec's 3 x phi limit, and 2.5 mm is
    # the official minimum drain-hole diameter (resin shrink leaves 2.2 mm).
    # 1.0 mm lands between holes keep the flat plate stiff in post-processing.
    rw, rh, rd = P["vent_recess"]
    scx, scy = P["sensor_center"]
    if rd > 0:
        base = base.cut(rr(rw, rh, 2.0, z0 - 0.5, z0 + rd, cx=scx, cy=scy))
    nc, nr = P["vent_cols"], P["vent_rows"]
    for i in range(nc):
        for j in range(nr):
            hx = scx + (i - (nc - 1) / 2) * P["vent_pitch_x"]
            hy = scy + (j - (nr - 1) / 2) * P["vent_pitch_y"]
            base = base.cut(cyl_at(P["vent_d"], z0 - 0.5,
                                   floor_top + 0.5, hx, hy))

    # Cross-ventilation on BOTH side walls, still inside the sensor bay
    # height. The left array is new in v3.2.
    for y in P["side_vent_ys"]:
        for z in P["side_vent_zs"]:
            base = base.cut(x_hole(P["vent_d"], y, z,
                                   right_x - 3.0, right_x + 3.0))
            base = base.cut(x_hole(P["vent_d"], y, z,
                                   -right_x - 3.0, -right_x + 3.0))

    return base.clean()


def make_slider():
    """Separate captured PWR slider. Loaded from inside before the panel.

    The 7 mm tall body cannot pass the 5 mm window, but its 3.2 mm paddle
    can; two fork tabs bracket the factory 1.5 mm switch tab. Sliding
    travel is +/-3 mm (6 mm body in 12 mm slot).
    """
    y, z = -24.65, -7.0
    s = rr_x(6.0, 7.0, 0.8, y, z, 24.9, 25.9)          # captured body
    s = s.union(rr_x(4.0, 3.2, 0.6, y, z, 25.9, 28.7))  # finger paddle
    for gy in (-26.2, -24.65, -23.1):
        s = s.union(rr_x(0.8, 2.4, 0.3, gy, z, 28.7, 28.9))  # grip ribs
    for fy in (-25.5, -21.8):
        s = s.union(box_at(0.8, 1.6, 1.6, 25.25, fy, z))      # fork tabs
    return s.clean()


def make_parked_slider():
    """Rotate the slider -90 deg about Y so its 1 mm-thick body becomes a
    flat 7 x 6 mm plate, then park it in a clear part of the cavity.

    Ry(-90): (x, y, z) -> (-z, y, x). The original 1 mm body thickness
    (x=24.9..25.9) becomes the Z thickness, so the parked island is only
    4.05 mm tall and bridges just a 0.6 mm open gap above the floor.
    """
    s = make_slider().rotate((0, 0, 0), (0, 1, 0), -90)
    b = s.val().BoundingBox()
    floor_top = P["base_bottom"] + P["floor"]
    tz = floor_top + P["park_gap"] + b.zlen / 2
    s = s.translate((P["park_center"][0] - (b.xmin + b.xmax) / 2,
                     P["park_center"][1] - (b.ymin + b.ymax) / 2,
                     tz - (b.zmin + b.zmax) / 2))
    return s.clean()


def make_printable():
    """ONE connected solid: tub + parked slider + two breakaway sprues.

    The sprues start 0.2 mm inside the floor and end 0.30 mm inside the
    parked slider, so both ends truly fuse (no coincident-face T-junction).
    The 0.6 mm gap is fully open to the cavity, so uncured resin drains and
    the island never becomes a sealed pocket.
    """
    b = make_base()
    parked = make_parked_slider()
    pb = parked.val().BoundingBox()
    floor_top = P["base_bottom"] + P["floor"]
    for x, y in P["sprue_positions"]:
        b = b.union(cyl_at(P["sprue_d"], floor_top - 0.2,
                           pb.zmin + P["sprue_embed"], x, y))
    return b.union(parked).clean()


def make_park_detail():
    """Preview-only cut-away: a small floor pad + sprues + parked slider,
    so the 0.6 mm open gap and the two breakaway sprues are visible."""
    parked = make_parked_slider()
    pb = parked.val().BoundingBox()
    floor_top = P["base_bottom"] + P["floor"]
    pad = box_at(16.0, 16.0, 1.2, P["park_center"][0], P["park_center"][1],
                 floor_top - 0.6)
    for x, y in P["sprue_positions"]:
        pad = pad.union(cyl_at(P["sprue_d"], floor_top - 0.2,
                               pb.zmin + P["sprue_embed"], x, y))
    return pad.union(parked).clean()


def shape_info(name, model):
    s = model.val()
    b = s.BoundingBox()
    return {
        "name": name,
        "valid_brep": bool(s.isValid()),
        "solid_count": len(model.solids().vals()),
        "bbox_mm": [round(b.xlen, 3), round(b.ylen, 3), round(b.zlen, 3)],
        "volume_mm3": round(s.Volume(), 2),
        "volume_cm3": round(s.Volume() / 1000.0, 3),
    }


def main():
    base = make_base()              # clean tub, for assembly / fit reference
    slider = make_slider()          # slider in its installed position
    printable = make_printable()    # ONE connected solid = the only order file

    stl, step = ROOT / "stl", ROOT / "step"
    ref = ROOT / "reference"
    ref.mkdir(exist_ok=True)

    cq.exporters.export(printable, str(stl / "base.stl"),
                        tolerance=0.04, angularTolerance=0.12)
    cq.exporters.export(printable, str(step / "base.step"))
    cq.exporters.export(slider, str(step / "slider.step"))
    # Reference/spare parts only -- never upload when using the free coupon.
    cq.exporters.export(slider, str(ref / "slider_standalone.stl"),
                        tolerance=0.04, angularTolerance=0.12)
    cq.exporters.export(base, str(ref / "base_clean_reference.stl"),
                        tolerance=0.04, angularTolerance=0.12)
    cq.exporters.export(make_park_detail(),
                        str(ref / "park_detail.stl"),
                        tolerance=0.04, angularTolerance=0.12)
    (stl / "slider.stl").unlink(missing_ok=True)

    assembly = cq.Assembly(name="ESP32_S3_2_8B_Enclosure")
    assembly.add(base, name="base", color=cq.Color(0.25, 0.45, 0.65))
    assembly.add(slider, name="slider", color=cq.Color(0.85, 0.85, 0.88))
    assembly.save(str(step / "enclosure_assembly.step"))

    report = [shape_info("base_printable", printable),
              shape_info("base_clean_reference", base),
              shape_info("slider_installed_reference", slider)]
    pb = make_parked_slider().val().BoundingBox()
    n_solids = len(printable.solids().vals())
    report.append({
        "printable_solid_count": n_solids,
        "printable_single_connected_body": n_solids == 1,
        "sprue_count": len(P["sprue_positions"]),
        "sprue_d_mm": P["sprue_d"],
        "parked_slider_bbox_mm": [round(pb.xlen, 3), round(pb.ylen, 3),
                                  round(pb.zlen, 3)],
        "parked_gap_mm": P["park_gap"],
        "order_files": ["stl/base.stl"],
        "jlc_free_slots_used": 1,
        "combined_volume_cm3": report[0]["volume_cm3"],
    })
    (ROOT / "source" / "model_report.json").write_text(
        json.dumps({"version": "v3.4", "parameters": P, "models": report},
                   indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
