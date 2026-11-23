#!/usr/bin/env python3
"""Validate v3.4 printable meshes. Requires trimesh.

v3.4 delivers ONE STL: the tub, the parked PWR slider and two breakaway
sprues are a single connected body. reference/slider_standalone.stl is a
spare part (checked for quality but NOT an order file) -- uploading it
would consume a second JLC free-print slot. Back is flat (no local
thinning recess); walls 1.8 mm / floor 2.0 mm per JLC spec 27832.
"""
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("base", "stl/base.stl", True),
    ("slider_standalone_spare", "reference/slider_standalone.stl", False),
]
report = []

for name, rel, is_order in CASES:
    path = ROOT / rel
    raw = trimesh.load_mesh(str(path), process=False)
    rv = raw.vertices[raw.faces]
    area = 0.5 * np.linalg.norm(np.cross(rv[:, 1] - rv[:, 0],
                                          rv[:, 2] - rv[:, 0]), axis=1)
    degenerate = int((area < 1e-9).sum())
    # STL stores unshared vertices; merge them before topology checks.
    m = trimesh.load_mesh(str(path), process=True)
    item = {
        "name": name,
        "file": rel,
        "order_file": is_order,
        "vertices": int(len(m.vertices)),
        "faces": int(len(m.faces)),
        "watertight": bool(m.is_watertight),
        "single_body": bool(m.body_count == 1),
        "body_count": int(m.body_count),
        "winding_consistent": bool(m.is_winding_consistent),
        "degenerate_faces": degenerate,
        "volume_cm3": round(float(m.volume) / 1000.0, 3),
        "bbox_mm": [round(float(x), 2) for x in m.extents],
        "pass": bool(m.is_watertight and m.body_count == 1
                     and m.is_winding_consistent and degenerate == 0
                     and m.volume > 0),
    }
    report.append(item)

order = [x for x in report if x["order_file"]]
result = {
    "version": "v3.4",
    "all_pass": all(x["pass"] for x in report),
    "order_file_count": len(order),
    "jlc_free_slots_used": len(order),
    "single_connected_order_body": bool(
        len(order) == 1 and order[0]["body_count"] == 1),
    "total_volume_cm3": round(sum(x["volume_cm3"] for x in order), 3),
    "jlc_free_limit_cm3": 70.0,
    "models": report,
}
(ROOT / "source" / "validation_report.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
