"""Motion, easing, safe-zone and scroll-timing helpers for the @goandalan Reels engine.

Pure-Python (no heavy deps). Concepts (velocity-matched seams, staggered "waterfall" word entry,
slow-fast-slow nudge, one-idea-per-beat pacing) were studied from public motion doctrines
(HyperFrames Apache-2.0 / Herk Edit Kit MIT skill docs) and re-implemented from scratch here;
no external code is copied or executed. See docs/REELS_ENGINE_AUDIT.md.
"""

from __future__ import annotations

import math
from typing import Callable

# ---------------------------------------------------------------------------
# Instagram Reels 1080x1920 safe zones
#   top    : status/profile overlay (~14%)  -> keep clear above y=290 (also the 4:5 grid-crop top = 285)
#   bottom : caption + audio bar (~18%)     -> keep clear below y=1580 (4:5 grid-crop bottom = 1635)
#   right  : like/comment/share rail        -> keep clear right of x=960
# ---------------------------------------------------------------------------
REELS_W = 1080
REELS_H = 1920
SAFE_ZONE = {"left": 64, "right": 960, "top": 290, "bottom": 1580}
GRID_CROP_4x5 = {"top": 285, "bottom": 1635}  # center crop of a 9:16 cover used by the 4:5 / 3:4 profile grid
MIN_FONT_PX = 32

# Phone mock-up geometry (centered on safe box center x=512; bottom y=1386 leaves clean subtitle band y=1416..1558)
PHONE = {
    "frame_x": 228,
    "frame_y": 468,
    "frame_w": 568,
    "frame_h": 918,
    "slot_x": 244,
    "slot_y": 484,
    "slot_w": 536,
    "slot_h": 886,
    "radius": 36,
}


def clamp01(t: float) -> float:
    return 0.0 if t < 0.0 else 1.0 if t > 1.0 else t


def _in_out(power: float) -> Callable[[float], float]:
    def f(t: float) -> float:
        t = clamp01(t)
        return 0.5 * pow(2 * t, power) if t < 0.5 else 1 - 0.5 * pow(2 * (1 - t), power)

    return f


def _out(power: float) -> Callable[[float], float]:
    return lambda t: 1 - pow(1 - clamp01(t), power)


def _out_expo(t: float) -> float:
    t = clamp01(t)
    return 1.0 if t >= 1.0 else 1 - pow(2, -10 * t)


def _out_back(t: float) -> float:
    t = clamp01(t)
    c1, c3 = 1.35, 2.35
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def _in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * clamp01(t)) - 1) / 2


EASINGS: dict[str, Callable[[float], float]] = {
    "linear": clamp01,
    "in_out_sine": _in_out_sine,
    "in_out_cubic": _in_out(3),
    "in_out_quart": _in_out(4),
    "in_out_quint": _in_out(5),
    "out_cubic": _out(3),
    "out_quart": _out(4),  # "power4" style, velocity-matchable
    "out_quint": _out(5),
    "out_expo": _out_expo,
    "out_back": _out_back,
}


def ease(name: str, t: float) -> float:
    return EASINGS.get(name, EASINGS["in_out_cubic"])(t)


def waterfall_progress(index: int, t: float, stagger: float, dur: float, easing: str = "out_quart", start: float = 0.04) -> float:
    """Staggered cascade entry: item `index` starts at start+index*stagger and eases over `dur` seconds."""
    return ease(easing, (t - start - index * stagger) / max(dur, 1e-6))


def nudge_curve(t: float) -> float:
    """Slow-fast-slow 3-phase travel (10 / 65 / 25 split of time, 10% / 80% / 10% of distance)."""
    t = clamp01(t)
    if t < 0.10:
        return 0.10 * pow(t / 0.10, 2)
    if t < 0.75:
        return 0.10 + 0.80 * _in_out_sine((t - 0.10) / 0.65)
    return 0.90 + 0.10 * _out(3)((t - 0.75) / 0.25)


MOTION_PROFILES: dict[str, dict] = {
    # snappy / graphic: brutalist, pop, collage, blueprint
    "snappy": {
        "scroll": "in_out_quart", "text": "out_back", "stagger": 0.05, "text_dur": 0.40,
        "fade_s": 0.12, "wipe_s": 0.36, "hold_frac": 0.30, "shift_px": 64, "intensity": "high",
    },
    # refined / quiet: cinematic, editorial, swiss, clinics
    "refined": {
        "scroll": "in_out_sine", "text": "out_quart", "stagger": 0.11, "text_dur": 0.72,
        "fade_s": 0.40, "wipe_s": 0.55, "hold_frac": 0.22, "shift_px": 40, "intensity": "low",
    },
    # balanced / warm: organic, product, digital, data, hybrid
    "balanced": {
        "scroll": "in_out_quint", "text": "out_expo", "stagger": 0.08, "text_dur": 0.56,
        "fade_s": 0.26, "wipe_s": 0.44, "hold_frac": 0.20, "shift_px": 52, "intensity": "medium",
    },
}

_STYLE_TO_PROFILE = {
    "bold_brutalist": "snappy",
    "playful_pop": "snappy",
    "collage_scrapbook": "snappy",
    "technical_blueprint": "snappy",
    "cinematic_premium": "refined",
    "editorial_magazine": "refined",
    "swiss_minimal": "refined",
}
_FORMAL_CATEGORY_HINTS = ("klinik", "clinic", "dokter", "kesehatan", "hukum", "legal", "notaris", "pengacara", "b2b", "konsultan", "arsitek")


def motion_profile_for(style_key: str, category: str = "") -> dict:
    """Return a copy of the motion profile (never overshoots / bouncy easing for formal categories)."""
    name = _STYLE_TO_PROFILE.get(style_key or "", "balanced")
    cat = (category or "").lower()
    if any(h in cat for h in _FORMAL_CATEGORY_HINTS):
        name = "refined"
    prof = dict(MOTION_PROFILES[name])
    prof["name"] = name
    return prof


def build_scroll_plan(n_frames: int, max_y: float, stops: list[float], easing: str = "in_out_quint", hold_frac: float = 0.2) -> list[float]:
    """Per-frame scroll offsets: hold at top -> eased travel -> hold at each stop -> eased travel to bottom -> hold.

    Never linear: every travel segment is eased, with short holds so content is readable on a phone.
    """
    n = max(2, int(n_frames))
    if max_y <= 1:
        return [0.0] * n
    inner = sorted({float(round(s)) for s in stops if 0 < s < max_y})
    if len(inner) > 3:
        pick = [inner[int(round(i * (len(inner) - 1) / 2))] for i in range(3)]
        inner = sorted(set(pick))
    pts = [0.0] + inner + [float(max_y)]
    segs = len(pts) - 1
    hold_each = max(2, int(n * hold_frac / (segs + 1)))
    travel_total = max(segs * 6, n - hold_each * (segs + 1))
    total_dist = sum(pts[i + 1] - pts[i] for i in range(segs)) or 1.0

    ys: list[float] = []
    # Gentle breathing drift during reading holds keeps every frame alive & natural without jarring jumps
    for h_i in range(hold_each):
        ys.append(min(float(max_y), 4.0 * (h_i / max(1, hold_each))))
    for i in range(segs):
        y0, y1 = pts[i], pts[i + 1]
        tf = max(8, int(round(travel_total * (y1 - y0) / total_dist)))
        for j in range(tf):
            ys.append(y0 + (y1 - y0) * ease(easing, (j + 1) / tf))
        drift_dir = 1.0 if y1 < max_y - 8 else -1.0
        for h_i in range(hold_each):
            ys.append(max(0.0, min(float(max_y), y1 + drift_dir * 4.5 * (h_i / max(1, hold_each)))))

    if len(ys) != n:  # resample to exact frame count (nearest, monotonic-safe)
        ys = [ys[min(len(ys) - 1, int(i * len(ys) / n))] for i in range(n)]
    return ys


def pick_scroll_stops(section_tops_css: list[float], css_scale: float, slot_h: float, max_y: float) -> list[float]:
    """Choose up to 3 well-separated section offsets (scaled px) as natural reading stops."""
    stops: list[float] = []
    min_gap = slot_h * 0.45
    for top in sorted(section_tops_css):
        y = top * css_scale
        if y < slot_h * 0.55 or y > max_y - slot_h * 0.15:
            continue
        if stops and y - stops[-1] < min_gap:
            continue
        stops.append(y)
    return stops[:3]
