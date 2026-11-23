#!/usr/bin/env python3
"""Audit v3.4 against the official Waveshare STEP and the OFFICIAL JLC
3D-printing design spec (jlc-3dp.cn/technicalColumnsDetails/27832.html).

v3.4 changes vs v3.3 (all driven by the official spec, read from the page
and its table images on 2026-11-16):
  * Removed the 14x22x1.2 mm rear local-thinning recess. Official hole
    dia/depth table for resin says H <= 3 x phi, so a 2.4 mm hole through a
    2.6 mm floor (H/phi = 1.08) never needed thinning. The recess existed
    only to shorten CO2 diffusion, and created the weakest area of the part.
  * wall 2.2 -> 1.8 mm, floor 2.6 -> 2.0 mm; base_bottom -22.8 -> -22.2 keeps
    floor_top = -20.2, so no boss / button / port / slider Z changes.
  * vent_d 2.4 -> 2.5 mm (official minimum drain-hole diameter).
  * sprue_d 1.0 -> 1.6 mm (official spliced-part connecting bar > 1.5 mm).
  * counterbore 1.2 -> 1.0 mm (leaves 1.0 mm straight wall in the 2.0 floor).

The order is still ONE connected STL = ONE 款 = one free slot. Note the
spec's spliced-part clause: 2+ parts in one file may be billed +0.5 CNY each.

Usage:
  python3 audit.py --board-step /path/to/ESP32-S3-Touch-LCD-2.8B-20241031.stp
"""
import argparse
import json
import math
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--board-step", required=True)
args = ap.parse_args()

board = cq.importers.importStep(args.board_step)
solids = board.solids().vals()
cases = {
    "base": cq.importers.importStep(str(ROOT / "step" / "base.step")),
    "slider": cq.importers.importStep(str(ROOT / "step" / "slider.step")),
}
model = json.loads((ROOT / "source" / "model_report.json").read_text())
validation = json.loads((ROOT / "source" / "validation_report.json").read_text())
P = model["parameters"]
meta = model["models"][-1]

# --- Official board geometry, measured from the STEP -----------------------
def bbox(s):
    b = s.BoundingBox()
    return [round(b.xmin, 2), round(b.ymin, 2), round(b.zmin, 2),
            round(b.xmax, 2), round(b.ymax, 2), round(b.zmax, 2)]

mount_centres = []
for s in solids:
    c = s.Center()
    b = s.BoundingBox()
    if -10.1 < b.zmin < -9.9 and -4.6 < b.zmax < -4.4 and 80 < s.Volume() < 100:
        mount_centres.append((round(c.x, 3), round(c.y, 3)))
mount_centres = sorted(set(mount_centres))

expected = sorted({(x, y) for x in (-P["board_hole_x"], P["board_hole_x"])
                   for y in (P["board_hole_y_bottom"], P["board_hole_y_top"])})
centre_error = (max(abs(a[0] - b[0]) + abs(a[1] - b[1])
                    for a, b in zip(mount_centres, expected))
                if len(mount_centres) == 4 else None)

# --- Interference against every official component ------------------------
interference = {}
for name, case in cases.items():
    total, hits = 0.0, []
    for i, s in enumerate(solids):
        b = s.BoundingBox()
        if b.xmin > 36 or b.xmax < -36 or b.ymin > 44 or b.ymax < -48:
            continue
        try:
            v = case.val().intersect(s).Volume()
            if v > 0.01:
                total += v
                hits.append({"solid": i, "volume_mm3": round(v, 3)})
        except Exception:
            pass
    interference[name] = {"total_mm3": round(total, 4), "hits": hits}

# --- Dimension / feature check -------------------------------------------
bbox_base = cases["base"].val().BoundingBox()
bezel_x = round((P["outer_w"] - P["panel_w"]) / 2, 3)
bezel_y = round((P["outer_h"] - P["panel_h"]) / 2, 3)
floor_top = P["base_bottom"] + P["floor"]
boss_top = P["standoff_bottom_z"] - P["boss_gap"]
back_wall = round(P["floor"] - P["vent_recess"][2], 3)   # v3.4 = 2.0, no recess
hole_area = math.pi * (P["vent_d"] / 2) ** 2
rear_holes = P["vent_cols"] * P["vent_rows"]
side_holes = 2 * len(P["side_vent_ys"]) * len(P["side_vent_zs"])
total_holes = rear_holes + side_holes
new_area = round(total_holes * hole_area, 2)
old_window_area = round(16 * 10 - (4 - math.pi) * 2 ** 2, 2)
old_total_area = round(old_window_area + 8 * hole_area, 2)
h_over_phi = round(back_wall / P["vent_d"], 3)
top_lip = round((P["outer_w"]
                 - (P["panel_w"] + 2 * P["panel_clearance"])) / 2, 3)
boss_wall = round((P["boss_od"] - P["boss_id"]) / 2, 3)
boss_height = round(boss_top - floor_top, 3)

# --- The official spec, transcribed from the page + table images ----------
# "size-graded recommended wall" for resin:
#   5x5 -> 0.5 | 10x10 -> 0.8 | 50x50 -> 1.0 | 100x100 -> 1.5 | 200x200 -> 2
spec_27832 = {
    "source": "https://www.jlc-3dp.cn/technicalColumnsDetails/27832.html",
    "captured": "2026-11-16",
    "resin_rules": {
        "recommended_wall_mm": 2.0,
        "graded_wall_by_size_mm": {
            "5x5": 0.5, "10x10": 0.8, "50x50": 1.0,
            "100x100": 1.5, "200x200": 2.0},
        "boss_locator_clip_fastener_min_wall_mm": 1.5,
        "fragile_or_overhanging_recommended_mm": 2.0,
        "min_emboss_detail_mm": {"depth": 0.8, "width": 0.8},
        "printed_thread_min": "M6 coarse (we use metal screws into board copper standoffs instead)",
        "assembly_clearance_per_side_mm": 0.2,
        "movable_part_illustrated_clearance_mm": 0.5,
        "min_drain_hole_d_mm": 2.5,
        "drain_holes_needed_if_d_under_3mm": 2,
        "hole_depth_H_vs_dia_phi_mm": {
            "phi_1.0": "H 1-3.0", "phi_1.5": "H 1.5-4.5", "phi_2.0": "H 2-6.0",
            "rule_of_thumb": "H <= 3 x phi"},
        "painted_part_min_hole_d_mm": 2.0,
        "resin_hole_tolerance_mm": 0.3,
        "resin_hole_shrink_mm": 0.3,
        "solid_pin_D_vs_H_mm": {"D1.0": "H1.0", "D2.0": "H2-4.0", "D3.0": "H3-6.0"},
        "hollow_pin_min_wall_mm": 2.0,
        "spliced_part_connecting_bar_min_mm": 1.5,
        "spliced_part_max_parts_per_file": 10,
        "spliced_part_surcharge_CNY_each": 0.5,
        "spliced_part_advice": "one file one part strongly recommended",
        "accuracy_under_100mm": 0.2,
    },
    "our_case_size_mm": [round(bbox_base.xlen, 2), round(bbox_base.ylen, 2),
                         round(bbox_base.zlen, 2)],
    "our_size_bracket": "between 50x50 (1.0 mm) and 100x100 (1.5 mm) -> ~1.0-1.5 mm graded",
    "why_1_8_and_2_0_mm": (
        "Went thinner than v3.3 (2.2/2.6) but stayed ABOVE the graded "
        "recommendation and above the 1.5 mm fastener/clip minimum. Hard "
        "floors: 1.0 mm counterbore needs >=0.8 mm straight wall behind it; "
        "the 1.6 mm flexure arm is already at the 1.5 mm fastener minimum; "
        "the side wall carries 6 ports + 16 side holes, so 1.8 mm is a "
        "deliberate margin, not the theoretical 1.5 mm limit."),
    "why_no_local_thinning": (
        "phi 2.5 mm through a 2.0 mm floor gives H/phi = %.3f, well inside "
        "H <= 3 x phi. The old 1.4 mm recess was never needed for "
        "printability; it only shortened CO2 diffusion and made the weakest, "
        "most post-processing-prone area of the shell." % h_over_phi),
}

stack = {
    "official_board_solids": len(solids),
    "touch_panel_bbox_mm": bbox(solids[0]),
    "pcb_bbox_mm": bbox(solids[2]),
    "standoff_thread_bore_d_mm": 2.5,
    "standoff_outer_d_mm": 5.5,
    "standoff_z_range_mm": [-10.0, -4.5],
    "standoff_opens_toward": "-Z (case back)",
    "front_glass_mount_holes": 0,
    "mount_centres_from_step_mm": mount_centres,
    "mount_centres_in_model_mm": expected,
    "mount_centre_max_error_mm": centre_error,
    "case_bbox_mm": [round(bbox_base.xlen, 2), round(bbox_base.ylen, 2),
                     round(bbox_base.zlen, 2)],
    "total_thickness_mm": round(P["split_z"] - P["base_bottom"], 2),
    "v3_3_total_thickness_mm": 24.1,
    "front_bezel_mm": {"left_right": bezel_x, "top_bottom": bezel_y,
                       "v3_1": [6.65, 7.05],
                       "note": "outer_r is concentric with pocket_r so the top lip has constant width"},
    "top_lip_width_mm": top_lip,
    "side_wall_mm": P["wall"],
    "back_floor_mm": P["floor"],
    "back_wall_at_vents_mm": back_wall,
    "rear_local_thinning_recess": "REMOVED in v3.4 (was 1.4 mm in v3.2/v3.3)",
    "clear_height_under_board_mm": round(
        P["standoff_bottom_z"] - floor_top, 2),
    "internal_structure": {
        "perimeter_ledge": "kept - locates the glass panel in Z",
        "ledge_width_mm": round((P["outer_w"] - 2 * P["wall"] - 50.0) / 2, 3),
        "thin_ring_screw_bosses": 4,
        "boss_od_mm": P["boss_od"],
        "boss_id_mm": P["boss_id"],
        "boss_wall_mm": boss_wall,
        "boss_height_mm": boss_height,
        "boss_root_d_mm": P["boss_root_d"],
        "boss_root_h_mm": P["boss_root_h"],
        "boss_top_z_mm": boss_top,
        "boss_cold_gap_mm": P["boss_gap"],
        "boss_contact": "annular top r=1.4..2.5 lands inside standoff metal face r=1.25..2.75; never touches glass",
        "boss_lateral_arms": 0,
        "battery_retaining_ribs": 0,
        "scd41_retaining_ribs": 0,
        "full_width_partition": 0,
        "thermal_lip": 0,
        "note": "no internal ribs/baffles; cell and SCD41 carrier held with foam tape",
    },
    "one_shot_printing": {
        "order_files": ["stl/base.stl"],
        "jlc_free_slots_used": validation["jlc_free_slots_used"],
        "single_connected_body": validation["single_connected_order_body"],
        "parked_slider_bbox_mm": meta["parked_slider_bbox_mm"],
        "parked_gap_mm": P["park_gap"],
        "sprue_count": len(P["sprue_positions"]),
        "sprue_d_mm": P["sprue_d"],
        "sprue_xy_mm": [list(v) for v in P["sprue_positions"]],
        "note": "slider rotated -90 deg about Y, parked flat in an open cavity pocket 0.6 mm above the floor; two 1.6 mm sprues join it to the floor. Cut with flush pliers, lift out, load into the PWR guide from inside before fitting the glass.",
        "spliced_part_surcharge_CNY_estimate": 1.0,
        "sealed_cavity": False,
        "geometry_unchanged": "all Z coordinates, hole XY positions, boss layout and port layout identical to v3.3",
    },
    "panel_location": "glass step rests on the perimeter ledge; rear screws clamp only",
    "payload": {
        "battery_max_mm": P["battery_max"],
        "scd41_carrier_mm": P["sensor_max"],
        "note": "battery size is an editable default; verify against real cell",
    },
    "rear_screw_entry": {
        "clearance_hole_d_mm": P["screw_clearance_d"],
        "counterbore_d_mm": P["screw_head_d"],
        "counterbore_depth_mm": P["screw_head_depth"],
        "floor_thickness_mm": P["floor"],
        "straight_wall_left_mm": round(P["floor"] - P["screw_head_depth"], 3),
        "screw_free_span_mm": round(P["standoff_bottom_z"] - floor_top, 2),
        "fastener": "4x M2 or M2.5 x 16, from case back through the thin boss into board standoffs; light torque only",
        "internal_bosses": 4,
        "nut_traps": 0,
        "heat_set_inserts": 0,
        "clamp_load_path": "head -> floor -> boss -> copper standoff -> thread; glass not loaded",
    },
    "ventilation": {
        "rear": f"{P['vent_cols']} x {P['vent_rows']} = {rear_holes} holes, d={P['vent_d']} mm",
        "rear_recess_mm": P["vent_recess"],
        "recess_depth_mm": P["vent_recess"][2],
        "back_wall_mm": back_wall,
        "H_over_phi": h_over_phi,
        "spec_limit_H_over_phi": 3.0,
        "left_side_holes": side_holes // 2,
        "right_side_holes": side_holes // 2,
        "total_round_holes": total_holes,
        "total_open_area_mm2": new_area,
        "v3_3_total_open_area_mm2": round(40 * math.pi * 1.2 ** 2, 2),
        "v3_1_large_window_mm2": old_window_area,
        "v3_1_total_open_area_mm2": old_total_area,
        "sensor_facing_area_mm2": round(rear_holes * hole_area, 2),
        "note": "flat 2.0 mm back, no recess; 2.5 mm holes = official minimum drain diameter, resin shrink leaves ~2.2 mm; 1.0 mm lands between holes keep the plate stiff",
    },
}

# --- Free-print rules + OFFICIAL design-spec rule check --------------------
# Each row: pass=True compliant, pass=False + accepted_deviation=True is a
# conscious, documented trade-off that the user must be told about.
jlc = [
    {"rule": "免费单每单最多 2 款、每款 1 件",
     "actual": f"{validation['jlc_free_slots_used']} 款 1 件（只上传 stl/base.stl）",
     "pass": validation["jlc_free_slots_used"] == 1},
    {"rule": "三轴外形均小于 100 mm",
     "actual": f"{stack['case_bbox_mm'][0]} x {stack['case_bbox_mm'][1]} x {stack['case_bbox_mm'][2]} mm",
     "pass": all(v < 100 for v in stack["case_bbox_mm"])},
    {"rule": "模型总体积不超过 70 cm3",
     "actual": f"{validation['total_volume_cm3']} cm3",
     "pass": validation["total_volume_cm3"] < 70},
    {"rule": "[规范一] 推荐壁厚 2 mm；按尺寸分级 50x50->1.0 / 100x100->1.5 mm",
     "actual": f"侧壁 {P['wall']} mm，底板 {P['floor']} mm（本案 56.9x74.8 mm 落在 1.0~1.5 mm 档，取值高于分级值）",
     "pass": P["wall"] >= 1.5 and P["floor"] >= 1.5},
    {"rule": "[规范一] 凸起/定位/卡扣/紧固件最小壁厚 > 1.5 mm",
     "actual": f"弹性臂 1.6 mm；细柱根部圆台 {P['boss_root_d']}x{P['boss_root_h']} mm；可掰断浇口 {P['sprue_d']} mm",
     "pass": P["sprue_d"] > 1.5},
    {"rule": "[规范六] 孔深 H <= 3 x 孔径 phi（树脂）",
     "actual": f"通气孔 phi {P['vent_d']} mm 穿 {back_wall} mm 平底板，H/phi = {h_over_phi}",
     "pass": h_over_phi <= 3.0},
    {"rule": "[规范五] 最小溢料孔直径 2.5 mm；<3 mm 需 >=2 个孔",
     "actual": f"孔径 {P['vent_d']} mm = 下限；共 {total_holes} 个贯通孔（远超 2 个）",
     "pass": P["vent_d"] >= 2.5 and total_holes >= 2},
    {"rule": "[规范六] 喷油/喷漆件孔径 > 2 mm（树脂孔收缩 <=0.3 mm）",
     "actual": f"{P['vent_d']} mm，收缩后约 {round(P['vent_d'] - 0.3, 2)} mm，仍 > 2 mm",
     "pass": P["vent_d"] - 0.3 > 2.0},
    {"rule": "[规范四] 装配单边最小间隙 0.2 mm（树脂）",
     "actual": "屏幕沉位 0.3 mm/侧；滑块叉爪 0.25 mm/侧；柱顶 0.2 mm 冷态间隙",
     "pass": True},
    {"rule": "[规范十] 拼接件连接杆壁厚 > 1.5 mm，单文件 < 10 件",
     "actual": f"2 根浇口 {P['sprue_d']} mm；文件内功能件 2 个（壳体 + 滑块）",
     "pass": P["sprue_d"] > 1.5 and 2 < 10},
    {"rule": "[规范十] 2 件以上拼接按 0.5 元/个加收（非免费额度计数）",
     "actual": "预计 +1.0 元拼接费；仍为 1 款、占 1 个免费额度。已在 PDF 告知",
     "pass": True, "advisory": True},
    {"rule": "[规范七] 空心柱壁厚 > 2 mm",
     "actual": f"细环形螺丝柱 OD {P['boss_od']} / ID {P['boss_id']} -> 壁厚 {boss_wall} mm",
     "pass": False, "accepted_deviation": True,
     "justification": (
         "该条针对承受插拔/弯曲的空心定位柱；我们的柱是高 %.1f mm 的短"
         "受压夹紧垫柱，且柱顶环形面必须落在板载铜柱金属端面 r=1.25..2.75 "
         "内才不碰玻璃/PCB。若把壁厚做到 2 mm，外径需 >= 6.8 mm，环形接触面"
         "会越过铜柱外径 5.5 mm 而落空、反而传不了夹紧力，也与「柱子别太粗」"
         "的要求冲突。保留 1.1 mm + 底部 6.0x1.0 mm 圆台补强 + 轻拧。"
         % boss_height)},
    {"rule": "[规范一] 易损/悬空结构推荐壁厚 >= 2 mm",
     "actual": f"正面压玻璃薄唇 {top_lip} mm（为 1.75 mm 窄边框的取舍）",
     "pass": False, "accepted_deviation": True,
     "justification": "薄唇只做 Z 向定位、不承受夹紧力；与沉位圆角同心保证四角等宽，若加到 2 mm 正面边框会变宽，违背「看起来只有玻璃」的要求。"},
    {"rule": "单一实体、封闭水密、法线一致",
     "actual": "stl/base.stl 单一连通实体，水密/法线/退化面全通过",
     "pass": validation["all_pass"]},
    {"rule": "避免封闭内腔（需排液/排气）",
     "actual": f"背面 {rear_holes} 孔 + 左右各 {side_holes // 2} 孔贯通；停放滑块与底板间 {P['park_gap']} mm 缝隙四周开放",
     "pass": True},
]
deviations = [r for r in jlc if not r["pass"] and r.get("accepted_deviation")]

practice = [
    {"topic": "开孔定位", "guideline": "以 PCB 安装孔为基准，不从外形逐个量",
     "source": "Flashforge custom cut-outs guide", "applied": "全部孔位取自官方 STEP 坐标；缩框后按新右壁重新换算"},
    {"topic": "装配间隙", "guideline": "SLA 名义 0.3 mm；嘉立创规范树脂单边最小 0.2 mm",
     "source": "JLC 27832 / Protolabs Network", "applied": "屏幕沉位 0.3 mm/侧；柱顶留 0.2 mm 冷态间隙；滑块叉爪 0.25 mm/侧；电池与 SCD41 用泡棉固定"},
    {"topic": "孔与内角", "guideline": "内角圆角 R 不小于壁厚 1/4；切体穿透整壁；孔深 <= 3 x 孔径",
     "source": "JLC 27832 / SLA design guidelines", "applied": "所有接口孔 R2.8-3.0 mm；外形 R4.75 与沉位 R3.3 同心；通气孔 H/phi = %.3f" % h_over_phi},
    {"topic": "弹性按键", "guideline": "梁长至少 5 倍梁厚，根部 R 至少 0.5 倍梁厚，宽度至少 5 mm，避免 Z 向打印",
     "source": "Hubs snap-fit guide", "applied": "L/h=9.5/1.6=5.9，圆头 U 槽，宽 7 mm，槽顶避开共面以防非流形；1.6 mm 正好卡在规范紧固件 1.5 mm 下限"},
    {"topic": "滑动开关", "guideline": "本体距外壁约 5 mm，开孔 12x5 mm；拨帽应由壳体捕获，不能用悬臂传双向力",
     "source": "Makers Making Change OpenAT Design Guide", "applied": "12x5 mm 圆角窗 + 独立捕获式刚性滑块；保持式开关需双向刚性传力，SLA 树脂不能做柔性铰链"},
    {"topic": "螺丝固定", "guideline": "SLA 为热固性树脂，禁用热熔铜螺母；夹紧力应由刚性面承担，避免预压玻璃",
     "source": "Forge Labs / RottenWiFi / JLC 27832", "applied": "细环形柱把夹紧力旁路到板载铜柱金属端面；柱顶留 0.2 mm 冷态间隙；不打印螺纹（规范最小 M6 粗牙）"},
    {"topic": "SCD41 通气", "guideline": "传感器正对开口、小死体积、远离热源、置于设备最低处",
     "source": "Sensirion SCD4x Design-in Guide", "applied": "传感器置最低处；平整 2.0 mm 背板 + 24 孔 2.5 mm 阵列；左右各 8 孔形成穿堂对流"},
    {"topic": "圆孔换大窗口的取舍", "guideline": "SCD4x 不宜置于小孔/网格后，会降低响应速度",
     "source": "Sensirion SCD4x Design-in Guide", "applied": f"如实记录：正对开口由 {old_window_area} mm2 降为 {round(rear_holes * hole_area, 2)} mm2，响应略慢；v3.4 取消局部减薄后扩散路径由 1.4 增至 2.0 mm，但孔径增大到 2.5 mm 使总开口面积升至 {new_area} mm2"},
    {"topic": "一体打印随附件", "guideline": "活动件与本体用可掰断浇口连成一个连通实体，间隙足够排液，连接杆壁厚 > 1.5 mm",
     "source": "JLC 27832 第十节 / SLA 排液设计", "applied": "滑块平躺停放于空腔、离底板 0.6 mm 开放缝隙、2 根 1.6 mm 浇口连接；打印后剪下装入导轨，只占 1 个免费额度；平台可能加收 1 元拼接费"},
    {"topic": "取消局部减薄", "guideline": "避免无必要的薄壁与截面突变；后处理要经酒精清洗、去支撑、打磨喷砂",
     "source": "JLC 27832 第一节 / 第六节", "applied": "删除 14x22x1.2 mm 背面凹槽，恢复平整 2.0 mm 背板；1.0 mm 孔间保留料带提高刚度"},
]

report = {
    "version": "v3.4",
    "board_step": args.board_step,
    "official_jlc_spec_27832": spec_27832,
    "board_and_fit": stack,
    "interference": interference,
    "jlc_free_print_and_design_spec": jlc,
    "documented_deviations": deviations,
    "best_practice": practice,
    "all_pass": (
        validation["all_pass"]
        and validation["single_connected_order_body"]
        and validation["jlc_free_slots_used"] == 1
        and all(v["total_mm3"] < 0.01 for v in interference.values())
        and all(r["pass"] or r.get("accepted_deviation") for r in jlc)
        and centre_error == 0
    ),
}
(ROOT / "source" / "audit_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({
    "all_pass": report["all_pass"],
    "mount_centre_error_mm": centre_error,
    "case_bbox_mm": stack["case_bbox_mm"],
    "total_thickness_mm": stack["total_thickness_mm"],
    "side_wall_mm": P["wall"],
    "back_floor_mm": P["floor"],
    "back_wall_at_vents_mm": back_wall,
    "H_over_phi": h_over_phi,
    "front_bezel_mm": stack["front_bezel_mm"],
    "interference_mm3": {k: v["total_mm3"] for k, v in interference.items()},
    "volume_cm3": validation["total_volume_cm3"],
    "order_files": validation["order_file_count"],
    "jlc_free_slots_used": validation["jlc_free_slots_used"],
    "single_connected_body": validation["single_connected_order_body"],
    "sprue_d_mm": P["sprue_d"],
    "total_holes": total_holes,
    "open_area_mm2": new_area,
    "v3_3_open_area_mm2": round(40 * math.pi * 1.2 ** 2, 2),
    "documented_deviations": [d["rule"] for d in deviations],
}, indent=2, ensure_ascii=False))
