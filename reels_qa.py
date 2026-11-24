"""Automated QC for generated Reels (ffprobe/ffmpeg + plate DOM audit + guardrails)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from reels_motion import GRID_CROP_4x5, MIN_FONT_PX, REELS_H, REELS_W, SAFE_ZONE


def _run(cmd: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def probe_media(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    info: dict[str, Any] = {"ok": False}
    if not ffprobe or not path.exists():
        return info
    r = _run([ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)])
    if r.returncode != 0:
        info["error"] = r.stderr[-200:]
        return info
    data = json.loads(r.stdout or "{}")
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    num, _, den = str(v.get("avg_frame_rate", "0/1")).partition("/")
    fps = (float(num) / float(den or 1)) if float(den or 1) else 0.0
    info.update(
        ok=True,
        width=v.get("width"), height=v.get("height"), codec=v.get("codec_name"), pix_fmt=v.get("pix_fmt"),
        fps=round(fps, 2), frames=int(v.get("nb_read_frames") or 0),
        duration=float(data.get("format", {}).get("duration") or v.get("duration") or 0),
        video_duration=float(v.get("duration") or 0),
        has_audio=bool(a), audio_codec=a.get("codec_name"), audio_rate=int(a.get("sample_rate") or 0),
        audio_duration=float(a.get("duration") or 0), audio_channels=a.get("channels"),
    )
    return info


def detect_black_freeze(path: Path) -> dict[str, list[dict[str, float]]]:
    ffmpeg = shutil.which("ffmpeg")
    out: dict[str, list[dict[str, float]]] = {"black": [], "freeze": []}
    if not ffmpeg or not path.exists():
        return out
    r = _run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-vf",
              "blackdetect=d=0.10:pix_th=0.04:pic_th=0.99,freezedetect=n=-60dB:d=1.2", "-an", "-f", "null", "-"], timeout=120)
    log = r.stderr
    for m in re.finditer(r"black_start:([\d.]+)\s+black_end:([\d.]+)", log):
        out["black"].append({"start": float(m.group(1)), "end": float(m.group(2))})
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
    durs = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", log)]
    for s, d in zip(starts, durs):
        out["freeze"].append({"start": s, "duration": d})
    return out


def sample_frames(path: Path, rate: float = 2.0) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    stats: dict[str, Any] = {"samples": 0, "min_luma": None, "max_luma": None, "dup_ratio": None, "max_jump": None}
    if not ffmpeg or not path.exists():
        return stats
    with tempfile.TemporaryDirectory() as td:
        r = _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={rate},scale=216:384", f"{td}/f_%03d.png"])
        files = sorted(Path(td).glob("f_*.png"))
        lumas, diffs = [], []
        prev = None
        for f in files:
            im = Image.open(f).convert("L")
            lumas.append(ImageStat.Stat(im).mean[0])
            if prev is not None:
                diffs.append(ImageStat.Stat(ImageChops.difference(prev, im)).mean[0])
            prev = im
        if lumas:
            stats.update(samples=len(lumas), min_luma=round(min(lumas), 1), max_luma=round(max(lumas), 1))
        if diffs:
            stats.update(dup_ratio=round(sum(1 for d in diffs if d < 0.15) / len(diffs), 2), max_jump=round(max(diffs), 1))
    return stats


def build_reels_qa(
    *,
    mp4_path: Path,
    cover_path: Path,
    video_meta: dict[str, Any],
    capture: dict[str, Any],
    plate_audit: dict[str, Any],
    caption_text: str,
    on_screen_texts: list[str],
    lead: dict[str, Any],
    guardrail: dict[str, Any],
    target_range: tuple[float, float] = (8.0, 12.5),
    leak_checker: Any = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    pm = probe_media(mp4_path) if video_meta.get("encoded_mp4") else {"ok": False}
    if pm.get("ok"):
        dur = pm["duration"]
        add("reels_video_9x16",
            pm["width"] == REELS_W and pm["height"] == REELS_H and pm["codec"] == "h264" and pm["pix_fmt"] == "yuv420p",
            f"{pm['width']}x{pm['height']} {pm['codec']}/{pm['pix_fmt']} {pm['fps']}fps {dur:.2f}s {mp4_path.stat().st_size // 1024}KB")
        add("duration_target", target_range[0] <= dur <= target_range[1], f"{dur:.2f}s (target {target_range[0]}–{target_range[1]}s)")
        add("fps_ok", pm["fps"] in (30.0, 60.0) or abs(pm["fps"] - 30) < 0.5 or abs(pm["fps"] - 60) < 0.5, f"{pm['fps']} fps")
        exp_frames = int(round(pm["video_duration"] * pm["fps"])) if pm["fps"] else 0
        add("frame_count_consistent", abs(pm["frames"] - exp_frames) <= 2, f"{pm['frames']} frame (expected ≈{exp_frames})")
        sync = abs(pm["audio_duration"] - pm["video_duration"]) if pm["has_audio"] else 99
        add("audio_stream_aac", pm["has_audio"] and pm["audio_codec"] == "aac" and pm["audio_rate"] == 44100,
            f"{pm.get('audio_codec')} {pm.get('audio_rate')}Hz ch={pm.get('audio_channels')}" if pm["has_audio"] else "tidak ada stream audio")
        add("audio_video_sync", sync <= 0.35, f"|audio−video|={sync:.2f}s")
        bf = detect_black_freeze(mp4_path)
        add("no_black_frames", not bf["black"], f"{len(bf['black'])} segmen hitam" if bf["black"] else "0 segmen hitam")
        long_freeze = [f for f in bf["freeze"] if f["duration"] > 2.2]
        add("no_long_freeze", not long_freeze, f"{len(long_freeze)} freeze >2.2s" if long_freeze else "tidak ada freeze panjang")
        fs = sample_frames(mp4_path)
        add("frame_luma_ok", (fs["min_luma"] or 0) >= 6, f"min luma {fs['min_luma']} (n={fs['samples']}), maks lompatan {fs['max_jump']}")
    else:
        add("reels_video_9x16", False, "reels.mp4 tidak ter-encode / ffprobe tidak tersedia")

    # cover (also safe for the 4:5 grid crop)
    cover_ok = False
    if cover_path.exists():
        im = Image.open(cover_path)
        cover_ok = im.size == (REELS_W, REELS_H)
        cb = plate_audit.get("cover_boxes", [])
        outside = [b for b in cb if b["t"] < GRID_CROP_4x5["top"] - 2 or b["b"] > GRID_CROP_4x5["bottom"] + 2]
        add("reels_cover_9x16", cover_ok, f"{im.size[0]}x{im.size[1]}")
        add("cover_grid_crop_safe", cover_ok and not outside, "semua teks cover berada dalam crop tengah 4:5" if not outside else f"{len(outside)} teks di luar crop 4:5")
    else:
        add("reels_cover_9x16", False, "cover_reels.png tidak ada")

    viol = plate_audit.get("violations", [])
    add("ig_safe_zones", not viol,
        f"semua teks di dalam safe zone x{SAFE_ZONE['left']}–{SAFE_ZONE['right']}, y{SAFE_ZONE['top']}–{SAFE_ZONE['bottom']}" if not viol
        else f"{len(viol)} teks keluar safe zone: {viol[0]['plate']}/{viol[0]['text']!r}")
    add("text_clipping", not viol, f"{plate_audit.get('boxes', 0)} kotak teks diaudit, 0 terpotong" if not viol else "ada teks terpotong/keluar batas")
    mf = plate_audit.get("min_font_px", 0)
    add("mobile_readability", mf >= MIN_FONT_PX - 0.5, f"font minimum {mf}px (lantai {MIN_FONT_PX}px)")

    cta = capture.get("cta")
    tabs = capture.get("tabs")
    add("cta_visibility", bool(cta or tabs), "interaksi nyata: " + ("tab" if tabs else "tombol CTA asli") if (cta or tabs) else "tidak ada CTA/tab terdeteksi di DOM (fallback scroll)")
    ir = capture.get("image_report", {}) or {}
    broken = ir.get("broken", 0)
    add("website_authenticity",
        bool(capture.get("facts", {}).get("headline")) and capture.get("page_height_css", 0) >= 844 and broken == 0 and capture.get("source_kind") in {"file", "url"},
        f"headline DOM terbaca, tinggi halaman {capture.get('page_height_css')}px, gambar rusak={broken}, sumber={capture.get('source_kind')}")
    if broken:
        warnings.append(f"{broken} gambar rusak pada halaman sumber.")

    add("showcase_guardrails", guardrail["passed"], guardrail["detail"])
    if leak_checker is not None:
        leak = leak_checker(lead, caption_text, "", on_screen_texts)
        add("anonymization_leak", bool(leak.get("passed")), "0 kebocoran (nama/WA/alamat) di caption & teks layar" if leak.get("passed") else f"{len(leak.get('leaks', []))} kebocoran!")

    passed = sum(1 for c in checks if c["passed"])
    return {
        "status": "PASS" if all(c["passed"] for c in checks) else "NEEDS_REVISION",
        "score": int(round(100 * passed / max(1, len(checks)))),
        "passed_checks": passed,
        "total_checks": len(checks),
        "checks": checks,
        "warnings": warnings,
        "revisions": [c["name"] for c in checks if not c["passed"]],
        "metrics": {"media": pm, "plates_audit_boxes": plate_audit.get("boxes", 0), "min_font_px": mf},
    }
