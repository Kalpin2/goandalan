"""Anonymized 9:16 Vertical Reels Generator (1080x1920 H.264 MP4 + Cover + Beat Script) for @goandalan.

Uses the exact same `typography_intelligence_library` (12 visual styles + 4-layer typography)
and `copy_intelligence_library` (V1-V6 voice + HOOK-* patterns + hard guardrails) as carousels.
"""

from __future__ import annotations

import asyncio
import html
import json
import math
import os
import re
import shutil
import struct
import subprocess
import threading
import wave
from pathlib import Path
from typing import Any

from PIL import Image

import database as db
import demo_generator as dg
from config import settings
from creative_agent import (
    CreativeDirector,
    VisualDesigner,
    draft_recycled_caption,
    resolve_style_key,
)
from creative_agent.carousel_planner import BANNED_SALES_CTAS, CASUAL_SLANG_PATTERN, select_caption_voice
from reels_capture import CaptureConfig, capture_site
from reels_compose import SceneComposer
from reels_motion import motion_profile_for
from reels_plates import render_plate_set
from reels_qa import build_reels_qa

REELS_WIDTH = 1080
REELS_HEIGHT = 1920
REELS_FPS = 30
REELS_TARGET_DURATION = max(8.0, min(12.0, float(os.getenv("REELS_DURATION_SEC", "10.0"))))
AUDIO_SAMPLE_RATE = 44100

VALID_AUDIO_MODES = ("voiceover_and_music", "voiceover_only", "music_only", "silent")

AUDIO_MODE_OPTIONS: dict[str, dict[str, str]] = {
    "voiceover_and_music": {
        "label": "Voiceover + Musik (Rekomendasi)",
        "desc": "Narator Bahasa Indonesia neural membacakan hook & ringkasan, diiringi musik ambient lo-fi pelan yang ramah IG.",
    },
    "voiceover_only": {
        "label": "Voiceover Saja (Narator ID)",
        "desc": "Suara narator Bahasa Indonesia jernih tanpa musik background — cocok jika ingin menumpuk lagu trending IG.",
    },
    "music_only": {
        "label": "Musik Instrumental Saja",
        "desc": "Musik latar ambient lo-fi royalty-free lembut tanpa suara narator, fokus pada teks layar & scroll antarmuka.",
    },
    "silent": {
        "label": "Tanpa Audio (Siap Musik IG)",
        "desc": "Video senyap (track AAC kosong yang aman untuk Instagram) agar bebas dipasangi musik langsung di aplikasi Instagram Reels.",
    },
}

REELS_SEQUENCE_PRESETS: dict[str, dict[str, Any]] = {
    "scroll_reveal_showcase": {
        "label": "Scroll Reveal Showcase",
        "description": "Hook tipografi kinetik → reveal hero → scroll mobile terkontrol → demo fitur nyata (tab/CTA asli) → penutup netral.",
        "beat1_kicker": "WEBSITE CONCEPT · REELS",
        "beat2_kicker": "MOBILE EXPERIENCE SCROLL",
        "beat3_kicker": "DESKTOP & MOBILE PAIRING",
    },
    "before_after_ux": {
        "label": "Before / After UX Clarity",
        "description": "Masalah UX umum → ilustrasi sebelum → wipe ke website asli → interaksi nyata → penutup netral.",
        "beat1_kicker": "UX CLARITY REFRAME",
        "beat2_kicker": "STRUKTUR BARU DI LAYAR HP",
        "beat3_kicker": "INTERAKSI & KETERBACAAN",
    },
    "kinetic_editorial": {
        "label": "Kinetic Editorial Poster",
        "description": "Pembuka tipografi raksasa → satu wawasan desain → 3 detail UI nyata → ritme scroll → pernyataan penutup.",
        "beat1_kicker": "EDITORIAL TYPE DIRECTION",
        "beat2_kicker": "INTERFACE WALKTHROUGH",
        "beat3_kicker": "ACTUAL WEBSITE PREVIEW",
    },
}


def _esc(val: Any) -> str:
    return html.escape(str(val or ""), quote=True)


def _ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def _capture_reels_source_screenshots(html_path: Path, out_dir: Path, cfg: CaptureConfig | None = None) -> dict[str, Any]:
    """Compat wrapper: real mobile/desktop capture via the reusable `reels_capture.capture_site` module."""
    cap = capture_site(html_path, out_dir, cfg or CaptureConfig())
    return {
        "desktop_png": cap["desktop_png"],
        "mobile_tall_png": cap["mobile_tall_png"],
        "facts": cap["facts"],
        "capture": cap,
    }


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, Path):
        return obj.name
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


_INSIGHTS = [
    "Tipografi besar, info terpenting duluan.",
    "Satu layar, satu keputusan.",
    "Jelas dulu, hias belakangan.",
    "Kontras tegas, kontak mudah dijangkau.",
    "Ritme tenang, informasi tetap terbaca.",
]
_CLOSINGS = [
    "Desain yang terbaca, bukan sekadar tampil.",
    "Detail kecil, kesan yang tenang.",
    "Rapi di layar kecil, jelas di mata.",
    "Informasi tertata, pengunjung betah.",
]


def _pick(seq: list[str], seed: str) -> str:
    return seq[sum(ord(c) for c in seed) % len(seq)]


def _story_texts(*, seq: str, hook: str, display_name: str, industry: str, ux_clean: str, capture: dict[str, Any]) -> dict[str, str]:
    """On-screen story copy per sequence. Anonymized; problems are framed as generic patterns, never as claims about a real business."""
    first = re.split(r"(?<=[.!?])\s+", (ux_clean or "").strip())[0].strip().rstrip(".") if ux_clean else ""
    if first and len(first) <= 58:
        problem = f"Pola umum: {first}."
    else:
        problem = "Pola umum: info penting terkubur di layar HP."
    if capture.get("tabs"):
        feature = "Tab layanan, bisa diklik."
    elif capture.get("cta"):
        feature = "Tombol kontak, nyata."
    else:
        feature = "Info & kontak di bawah."
    if seq == "kinetic_editorial":
        closing = _pick(_CLOSINGS, display_name)
    elif seq == "before_after_ux":
        closing = "Lebih jelas, lebih mudah dihubungi."
    else:
        closing = display_name
    return {"hook": hook, "problem": problem, "insight": _pick(_INSIGHTS, display_name + industry), "closing": closing, "feature": feature}


def _render_reels_plates(
    *,
    out_dir: Path,
    brand_name: str,
    industry: str,
    city: str,
    domain: str,
    sequence_key: str,
    hook_headline: str,
    sub_hook: str,
    ux_note: str,
    creative_note: str,
    art_dir: dict[str, Any],
    desktop_png: Path,
    mobile_tall_png: Path,
    capture: dict[str, Any] | None = None,
    story: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Render plates inside the IG safe zone. Returns the plate-set dict (paths/reveal/audit)."""
    cap = capture or {}
    st = story or _story_texts(seq=sequence_key, hook=hook_headline, display_name=brand_name, industry=industry, ux_clean=ux_note, capture=cap)
    scale = 1.0
    res: dict[str, Any] = {}
    for attempt in range(3):
        res = render_plate_set(
            out_dir=out_dir, sequence_key=sequence_key, brand_name=brand_name, industry=industry, city=city, domain=domain,
            hook_headline=hook_headline, sub_hook=creative_note.strip() or sub_hook, insight_text=st["insight"],
            closing_text=st["closing"], problem_text=st["problem"], feature_title=st["feature"], art_dir=art_dir,
            desktop_png=desktop_png, mobile_tall_png=mobile_tall_png, page_height_css=cap.get("page_height_css", 2400),
            section_tops=cap.get("section_tops", []), handle=f"@{settings.IG_USERNAME}", title_scale=scale,
        )
        if not res["audit"]["violations"]:
            break
        scale *= 0.86  # shrink display type until everything sits inside the safe zone
    res["title_scale"] = scale
    return res


def _synthesize_ambient_music_wav(target_wav: Path, duration_sec: float = 10.5) -> Path:
    """Synthesize warm, mellow royalty-free lo-fi electric-piano ambient instrumental WAV (zero copyright risk)."""
    sr = AUDIO_SAMPLE_RATE
    total_samples = int(sr * max(4.0, duration_sec))
    # Warm lo-fi progression: Fmaj7 -> Em7 -> Dm7 -> Cmaj7
    chords = [
        (174.61, 220.00, 261.63, 329.63),  # Fmaj7
        (164.81, 196.00, 246.94, 293.66),  # Em7
        (146.83, 174.61, 220.00, 261.63),  # Dm7
        (130.81, 164.81, 196.00, 246.94),  # Cmaj7
    ]
    chord_len = max(2.0, duration_sec / len(chords))
    beat_period = 0.625  # ~96 BPM chill lo-fi pulse

    frames = bytearray()
    for i in range(total_samples):
        t = i / float(sr)
        c_idx = min(len(chords) - 1, int(t / chord_len))
        local_t = t - c_idx * chord_len
        # Soft attack & release per chord
        atk = min(1.0, local_t / 0.14)
        rel = min(1.0, max(0.0, (chord_len - local_t) / 0.25))
        chord_env = atk * (0.45 + 0.55 * math.exp(-local_t * 0.48)) * (0.3 + 0.7 * rel)

        # Warm electric piano tones (fundamental + gentle 2nd harmonic)
        val = 0.0
        for f in chords[c_idx]:
            val += 0.15 * math.sin(2.0 * math.pi * f * t)
            val += 0.04 * math.sin(2.0 * math.pi * (f * 2.0) * t)
        val *= chord_env

        # Soft sub-bass root pulse on every 2 beats
        beat_t = t % beat_period
        pulse_env = math.exp(-beat_t * 11.0)
        root_f = chords[c_idx][0] * 0.5
        val += 0.16 * pulse_env * math.sin(2.0 * math.pi * root_f * t)

        # Global smooth fade-in (0.35s) and fade-out (0.8s)
        g_in = min(1.0, t / 0.35)
        g_out = min(1.0, max(0.0, (duration_sec - t) / 0.8))
        sample = max(-0.92, min(0.92, val * g_in * g_out * 0.68))
        pcm = int(sample * 32767)
        frames.extend(struct.pack("<hh", pcm, pcm))

    with wave.open(str(target_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(frames))
    return target_wav


def _probe_audio_duration(audio_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not audio_path.exists():
        return 0.0
    try:
        out = subprocess.check_output(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            text=True,
            timeout=10,
        ).strip()
        return float(out)
    except Exception:
        return 0.0


def _build_proportional_cues(script_text: str, duration_sec: float, delay_sec: float = 0.25) -> list[dict[str, Any]]:
    words = [w for w in re.split(r"\s+", (script_text or "").strip()) if w]
    if not words or duration_sec <= 0.6:
        return []
    chunk_size = 5
    chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
    usable = max(1.0, duration_sec - delay_sec - 0.35)
    weights = [max(1, len(c.split())) for c in chunks]
    total_w = float(sum(weights))
    cues: list[dict[str, Any]] = []
    cur = delay_sec
    for chunk, w in zip(chunks, weights):
        seg = usable * (w / total_w)
        cues.append({"start": round(cur, 3), "end": round(cur + seg, 3), "text": chunk})
        cur += seg
    return cues


def _group_word_boundaries(boundaries: list[dict[str, Any]], delay_sec: float = 0.25, tempo: float = 1.0) -> list[dict[str, Any]]:
    if not boundaries:
        return []
    cues: list[dict[str, Any]] = []
    buf: list[dict[str, Any]] = []
    t_scale = max(0.5, float(tempo or 1.0))

    def _flush() -> None:
        if not buf:
            return
        start_s = delay_sec + (buf[0]["start"] / t_scale)
        end_s = delay_sec + (buf[-1]["end"] / t_scale)
        txt = " ".join(x["text"] for x in buf).strip()
        if txt:
            cues.append({"start": round(start_s, 3), "end": round(max(start_s + 0.25, end_s), 3), "text": txt})
        buf.clear()

    for b in boundaries:
        buf.append(b)
        if len(buf) >= 5 or b["text"].endswith((".", "?", "!", ",")):
            _flush()
    _flush()
    return cues


def _generate_indonesian_voiceover(
    script_text: str,
    target_mp3: Path,
    *,
    is_formal: bool = False,
    voice_override: str = "",
    rate_override: str = "",
    timeout_sec: int = 30,
) -> dict[str, Any]:
    """Generate crisp Indonesian neural voiceover via edge-tts + capture word/phrase timestamps (timeout <= 30s)."""
    clean_script = re.sub(r"\s+", " ", (script_text or "").strip())
    if not clean_script:
        return {"ok": False, "error": "empty_script", "duration_sec": 0.0, "boundaries": []}

    voice_name = voice_override or ("id-ID-GadisNeural" if is_formal else "id-ID-ArdiNeural")
    rate = rate_override or ("+2%" if is_formal else "+5%")

    result_box: dict[str, Any] = {
        "ok": False,
        "error": "",
        "voice": voice_name,
        "rate": rate,
        "duration_sec": 0.0,
        "boundaries": [],
    }

    def _runner() -> None:
        try:
            import edge_tts

            async def _stream_save() -> list[dict[str, Any]]:
                try:
                    comm = edge_tts.Communicate(clean_script, voice=voice_name, rate=rate, boundary="WordBoundary")
                except TypeError:
                    comm = edge_tts.Communicate(clean_script, voice=voice_name, rate=rate)
                bounds: list[dict[str, Any]] = []
                with target_mp3.open("wb") as fh:
                    async for chunk in comm.stream():
                        ctype = chunk.get("type")
                        if ctype == "audio":
                            fh.write(chunk["data"])
                        elif ctype in {"WordBoundary", "SentenceBoundary"}:
                            off_s = float(chunk.get("offset") or 0) / 10_000_000.0
                            dur_s = float(chunk.get("duration") or 0) / 10_000_000.0
                            txt = str(chunk.get("text") or "").strip()
                            if txt:
                                bounds.append({"start": off_s, "end": off_s + max(0.08, dur_s), "text": txt})
                return bounds

            bounds = asyncio.run(_stream_save())
            if target_mp3.exists() and target_mp3.stat().st_size > 1000:
                result_box["ok"] = True
                result_box["duration_sec"] = _probe_audio_duration(target_mp3)
                result_box["boundaries"] = bounds
            else:
                result_box["error"] = "empty_tts_output"
        except Exception as exc:
            result_box["error"] = str(exc)[:180]

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    th.join(timeout=max(5, min(30, int(timeout_sec))))
    if th.is_alive() and not result_box["ok"]:
        result_box["error"] = "edge_tts_timeout"
    return result_box


def _compose_reels_mp4(
    *,
    plates: dict[str, Path],
    mobile_tall_png: Path,
    target_mp4: Path,
    fps: int = REELS_FPS,
    audio_mode: str = "voiceover_and_music",
    voiceover_script: str = "",
    is_formal: bool = False,
    vo_voice_override: str = "",
    vo_rate_override: str = "",
    bgm_path: Path | None = None,
    bgm_track_id: str = "",
    composer: SceneComposer | None = None,
    target_duration: float = REELS_TARGET_DURATION,
    enable_synced_captions: bool = True,
) -> dict[str, Any]:
    """Encode 1080x1920 H.264 yuv420p MP4 (30fps) from scene frames + AAC audio (VO + sidechain-ducked target BGM)."""
    if composer is None:
        raise ValueError("composer (SceneComposer) wajib diberikan.")
    eff_audio = audio_mode if audio_mode in VALID_AUDIO_MODES else "voiceover_and_music"

    vo_mp3 = target_mp4.parent / "voiceover.mp3"
    music_wav = bgm_path if (bgm_path and bgm_path.exists()) else (target_mp4.parent / "ambient_music.wav")
    vo_info: dict[str, Any] = {"ok": False, "duration_sec": 0.0, "voice": "", "boundaries": []}
    audio_note = ""
    if eff_audio in {"voiceover_and_music", "voiceover_only"}:
        vo_info = _generate_indonesian_voiceover(
            voiceover_script,
            vo_mp3,
            is_formal=is_formal,
            voice_override=vo_voice_override,
            rate_override=vo_rate_override,
            timeout_sec=30,
        )
        if not vo_info["ok"]:
            audio_note = f"Voiceover fallback ({vo_info.get('error') or 'offline'})"
            eff_audio = "music_only" if eff_audio == "voiceover_and_music" else "silent"

    target = float(target_duration)
    if vo_info.get("ok"):
        target = max(target, vo_info["duration_sec"] + 1.0)
    target = max(8.0, min(15.0, target))

    plan = composer.build_plan(target)
    total_frames = sum(s["frames"] for s in plan)
    actual_duration = round(total_frames / float(fps), 2)

    if eff_audio in {"voiceover_and_music", "music_only"} and not music_wav.exists():
        _synthesize_ambient_music_wav(music_wav, duration_sec=actual_duration + 0.5)

    tempo = 1.0
    if vo_info.get("ok"):
        tempo = max(1.0, min(1.3, vo_info["duration_sec"] / max(1.0, actual_duration - 0.6)))
    vo_chain = f"aformat=sample_rates={AUDIO_SAMPLE_RATE}:channel_layouts=stereo," + (f"atempo={tempo:.3f}," if tempo > 1.005 else "")

    # Wire synced kinetic captions into SceneComposer inside IG safe zone
    cues: list[dict[str, Any]] = []
    if enable_synced_captions and (voiceover_script or "").strip():
        if vo_info.get("ok") and vo_info.get("boundaries"):
            cues = _group_word_boundaries(vo_info["boundaries"], delay_sec=0.25, tempo=tempo)
        if not cues:
            cues = _build_proportional_cues(voiceover_script, actual_duration, delay_sec=0.25)
        composer.vo_cues = cues

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        seq_dir = target_mp4.parent / "frames_fallback"
        seq_dir.mkdir(parents=True, exist_ok=True)
        for idx, fr in enumerate(composer.iter_frames(plan)):
            if idx % fps == 0:
                fr.save(seq_dir / f"beat_{idx // fps:02d}.png")
        return {
            "encoded_mp4": False, "fallback_frames_dir": str(seq_dir), "duration_sec": actual_duration, "fps": fps,
            "width": REELS_WIDTH, "height": REELS_HEIGHT, "audio_mode": eff_audio, "has_audio": False,
            "audio_note": audio_note, "bgm_track": bgm_track_id, "sidechain_ducked": False,
            "vo_cues_count": len(cues), "plan": plan,
        }

    cmd: list[str] = [
        ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-nostats",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{REELS_WIDTH}x{REELS_HEIGHT}", "-r", str(fps), "-i", "-",
    ]
    has_audio, silent_track, sidechain_ducked = False, False, False
    aac = ["-c:a", "aac", "-b:a", "128k", "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "2", "-t", str(actual_duration)]
    fade_out_st = max(0.2, round(actual_duration - 0.75, 2))
    if eff_audio == "voiceover_and_music" and vo_info.get("ok") and vo_mp3.exists() and music_wav.exists():
        # Pad V/O sidechain to exact actual_duration so BGM swells back smoothly after V/O finishes & A/V sync == 0.00s
        cmd += [
            "-i", str(vo_mp3),
            "-stream_loop", "-1", "-i", str(music_wav),
            "-filter_complex",
            f"[1:a]{vo_chain}adelay=250|250,apad=whole_dur={actual_duration:.2f},atrim=0:{actual_duration:.2f},asetpts=PTS-STARTPTS,volume=1.18,asplit=2[vo_main][vo_sc];"
            f"[2:a]aformat=sample_rates={AUDIO_SAMPLE_RATE}:channel_layouts=stereo,"
            f"atrim=0:{actual_duration:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.25,afade=t=out:st={fade_out_st:.2f}:d=0.70,volume=0.36[bg_raw];"
            "[bg_raw][vo_sc]sidechaincompress=threshold=0.025:ratio=6:attack=25:release=260:makeup=1[bg_ducked];"
            "[vo_main][bg_ducked]amix=inputs=2:duration=longest:dropout_transition=2,alimiter=limit=0.95[aout]",
            "-map", "0:v:0", "-map", "[aout]", *aac,
        ]
        has_audio, sidechain_ducked = True, True
    elif eff_audio == "voiceover_only" and vo_info.get("ok") and vo_mp3.exists():
        cmd += [
            "-i", str(vo_mp3), "-filter_complex",
            f"[1:a]{vo_chain}adelay=250|250,apad=whole_dur={actual_duration:.2f},atrim=0:{actual_duration:.2f},asetpts=PTS-STARTPTS,volume=1.15[aout]",
            "-map", "0:v:0", "-map", "[aout]", *aac,
        ]
        has_audio = True
    elif eff_audio == "music_only" and music_wav.exists():
        cmd += [
            "-stream_loop", "-1", "-i", str(music_wav), "-filter_complex",
            f"[1:a]aformat=sample_rates={AUDIO_SAMPLE_RATE}:channel_layouts=stereo,"
            f"atrim=0:{actual_duration:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.25,afade=t=out:st={fade_out_st:.2f}:d=0.70,volume=0.52[aout]",
            "-map", "0:v:0", "-map", "[aout]", *aac,
        ]
        has_audio = True
    else:
        # silent-safe AAC track: Instagram never rejects it, browsers keep the unmute control, user can still add music in IG
        cmd += [
            "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-map", "0:v:0", "-map", "1:a", "-c:a", "aac", "-b:a", "48k", "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "2", "-t", str(actual_duration),
        ]
        has_audio, silent_track = True, True

    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-preset", "veryfast", "-crf", "20", str(target_mp4)]

    err_log = target_mp4.parent / "ffmpeg_render.log"
    with err_log.open("wb") as err_fh:  # never an unread PIPE (Windows pipe-buffer deadlock)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err_fh)
        assert proc.stdin is not None
        try:
            for frame in composer.iter_frames(plan):
                proc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            pass
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
        proc.wait(timeout=180)
    err_txt = err_log.read_text(encoding="utf-8", errors="replace") if err_log.exists() else ""
    err_log.unlink(missing_ok=True)
    if proc.returncode != 0 or not target_mp4.exists() or target_mp4.stat().st_size < 1000:
        raise RuntimeError(f"FFmpeg gagal merender reels.mp4: {err_txt[-400:]}")

    return {
        "encoded_mp4": True, "path": str(target_mp4), "size_bytes": target_mp4.stat().st_size,
        "duration_sec": actual_duration, "fps": fps, "width": REELS_WIDTH, "height": REELS_HEIGHT,
        "codec": "h264/yuv420p" + ("+aac" if has_audio else ""), "audio_mode": eff_audio, "has_audio": has_audio,
        "silent_audio_track": silent_track, "sidechain_ducked": sidechain_ducked,
        "bgm_track": bgm_track_id, "bgm_file": music_wav.name if music_wav.exists() else "",
        "voiceover_voice": vo_info.get("voice") if vo_info.get("ok") else "",
        "voiceover_tempo": round(tempo, 3), "vo_cues_count": len(cues), "audio_note": audio_note, "plan": plan,
    }


def generate_reels_package_for_lead(
    lead_id: int,
    *,
    anonymize: bool = True,
    art_direction_preset: str | None = None,
    sequence_type: str | None = None,
    voice_id: str | None = None,
    hook_pattern_id: str | None = None,
    audio_mode: str = "voiceover_and_music",
    creative_note: str = "",
    capture_config: CaptureConfig | None = None,
    target_duration: float | None = None,
    motion_intensity: str | None = None,
    vo_script: str = "",
    vo_style: str = "auto",
    bgm_track: str = "auto",
    pain_code: str = "",
    reel_hook_id: str = "",
    attract_cta: bool = False,
) -> dict[str, Any]:
    """Render complete anonymized 9:16 Reels package (`reels.mp4`, `cover_reels.png`, `caption.txt`, `beat_script`, `qa_report.json`)."""
    from creative_agent import reels_intelligence as ri

    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead ID {lead_id} tidak ditemukan.")

    use_anon = True if anonymize else bool(lead.get("is_anonymized"))
    eff_style = art_direction_preset if art_direction_preset and str(art_direction_preset).lower() != "auto" else None
    eff_seq = sequence_type if sequence_type in REELS_SEQUENCE_PRESETS else "scroll_reveal_showcase"
    eff_voice = str(voice_id).strip().upper() if voice_id and str(voice_id).strip().lower() != "auto" else None
    eff_hook = str(hook_pattern_id).strip().upper() if hook_pattern_id and str(hook_pattern_id).strip().lower() != "auto" else None

    demo_style_override = eff_style if eff_style in dg.STYLE_THEMES else None
    concept_res = dg.generate_concept_html_for_lead(lead_id, anonymize=use_anon, force_style=demo_style_override)
    lead = concept_res["lead"]
    demo_style_key = concept_res["design_style"]
    carousel_style_key = resolve_style_key(eff_style or demo_style_key, lead.get("category", ""))

    slug = lead["slug"]
    demo_dir = settings.DEMOS_DIR / slug
    reels_dir = demo_dir / "reels"
    reels_dir.mkdir(parents=True, exist_ok=True)

    full_html = demo_dir / "index.html"
    source_html = full_html if (full_html.exists() and not use_anon) else Path(concept_res["concept_file"])

    display_name = dg.generate_fictional_name(lead) if use_anon else lead["business_name"]
    industry = lead.get("category") or "Bisnis Lokal"
    city = lead.get("city") or settings.DEFAULT_CITY
    domain = f"{db.slugify(display_name)}.id"

    director = CreativeDirector()
    analysis = director.analyze_business(
        {"brand_name": display_name, "industry": industry, "city": city, "project_status": "concept",
         "design_style": carousel_style_key, "domain": domain}
    )
    art_dir = director.build_art_direction(analysis, chosen_style=carousel_style_key)

    cap_pack = _capture_reels_source_screenshots(source_html, reels_dir, capture_config)
    capture = cap_pack["capture"]
    facts = cap_pack["facts"]

    vo_profile = ri.resolve_vo_profile(industry, vo_style=vo_style, brand_name=display_name)
    cap_voice_override = "formal_editorial" if (eff_voice in {"V2", "V4"} or vo_profile["is_formal"]) else None
    recycled_cap = draft_recycled_caption(
        lead={**lead, "is_anonymized": 1, "anonymized_name": display_name},
        art_direction=art_dir, facts=facts, caption_voice_override=cap_voice_override,
        voice_id_override=eff_voice, hook_pattern_id=eff_hook, content_format="reels", creative_note=creative_note,
    )
    caption_text = recycled_cap["caption"]
    hook_first_line = caption_text.splitlines()[0].strip() if caption_text else f"Konsep web {display_name}."
    hook_short = hook_first_line[:104].rsplit(" ", 1)[0] if len(hook_first_line) > 104 else hook_first_line

    sub_hook = f"Eksplorasi tampilan mobile {display_name} ({industry.lower()}) dengan arah {art_dir['primary_style']}."
    try:
        from content_review import _sanitize_ux_flaw_for_brief
        ux_clean = _sanitize_ux_flaw_for_brief(lead, display_name) if (lead.get("ux_flaw") or "").strip() else ""
    except Exception:
        ux_clean = ""

    profile = motion_profile_for(carousel_style_key, industry)
    if motion_intensity and str(motion_intensity).lower() in ("snappy", "refined", "balanced"):
        from reels_motion import MOTION_PROFILES, _FORMAL_CATEGORY_HINTS
        req_intensity = str(motion_intensity).lower()
        if any(h in industry.lower() for h in _FORMAL_CATEGORY_HINTS) and req_intensity != "refined":
            profile = motion_profile_for(carousel_style_key, industry)
        else:
            profile = dict(MOTION_PROFILES[req_intensity])
            profile["name"] = req_intensity

    story = _story_texts(seq=eff_seq, hook=hook_short, display_name=display_name, industry=industry, ux_clean=ux_clean, capture=capture)
    if attract_cta:
        story["closing"] = "DM kata KONSEP"

    plate_set = _render_reels_plates(
        out_dir=reels_dir, brand_name=display_name, industry=industry, city=city, domain=domain, sequence_key=eff_seq,
        hook_headline=hook_short, sub_hook=sub_hook, ux_note=ux_clean, creative_note="", art_dir=art_dir,
        desktop_png=cap_pack["desktop_png"], mobile_tall_png=cap_pack["mobile_tall_png"], capture=capture, story=story,
    )
    plates = plate_set["paths"]

    is_formal_voice = bool(recycled_cap["caption_voice"] == "formal_editorial" or vo_profile["is_formal"])
    if (vo_script or "").strip():
        final_vo_script = re.sub(r"\s+", " ", vo_script.strip())
    else:
        vo_core = hook_short.rstrip(".!? ")
        if attract_cta:
            final_vo_script = (
                f"{vo_core}. Pada konsep halaman mobile {display_name}, layanan utama, jadwal, dan tombol kontak disusun jernih agar pengunjung cepat mengambil keputusan. Ingin melihat konsep versi bisnis Anda? Silakan DM kata KONSEP."
                if is_formal_voice
                else f"{vo_core}. Di konsep tampilan mobile {display_name} ini, menu utama, lokasi, sampai tombol kontak langsung terbaca rapi tanpa ribet. Mau lihat konsep versi bisnis kamu? Langsung DM kata KONSEP."
            )
        else:
            final_vo_script = (
                f"{vo_core}. Eksplorasi tampilan mobile untuk {display_name}, dirancang rapi dan mudah dibaca di layar ponsel."
                if is_formal_voice
                else f"{vo_core}. Ini konsep tampilan mobile untuk {display_name}, rapi dan gampang dibaca di layar HP."
            )
    if is_formal_voice:
        final_vo_script = ri.sanitize_formal_vo_text(final_vo_script)

    bgm_info = ri.select_bgm_track(industry, bgm_track=bgm_track, brand_name=display_name)
    eff_target_dur = float(target_duration or (13.0 if attract_cta else REELS_TARGET_DURATION))

    composer = SceneComposer(
        sequence_key=eff_seq, plates=plates, reveal=plate_set["reveal"], capture=capture, profile=profile, fps=REELS_FPS,
        texts=story,
    )
    mp4_path = reels_dir / "reels.mp4"
    video_meta = _compose_reels_mp4(
        plates=plates, mobile_tall_png=cap_pack["mobile_tall_png"], target_mp4=mp4_path, fps=REELS_FPS,
        audio_mode=audio_mode, voiceover_script=final_vo_script, is_formal=is_formal_voice,
        vo_voice_override=vo_profile["voice"], vo_rate_override=vo_profile["rate"],
        bgm_path=bgm_info["path"], bgm_track_id=bgm_info["id"],
        composer=composer, target_duration=eff_target_dur,
        enable_synced_captions=bool(attract_cta or (vo_script or "").strip()),
    )

    plan = video_meta.pop("plan")
    beat_script: list[dict[str, Any]] = []
    cursor = 0.0
    for idx, sc in enumerate(plan, start=1):
        d = sc["frames"] / float(REELS_FPS)
        trans = {"cut": "Cut langsung", "crossfade": f"Crossfade {profile['fade_s']:.2f}s", "wipe": f"Wipe horizontal {profile['wipe_s']:.2f}s"}[sc["transition"]]
        beat_script.append({
            "beat": idx, "time_range": f"{cursor:.1f}s – {cursor + d:.1f}s", "title": sc["title"], "visual": sc["visual"],
            "on_screen_text": sc["text"], "transition": f"Masuk: {trans}",
        })
        cursor += d

    caption_file = reels_dir / "caption.txt"
    caption_file.write_text(caption_text, encoding="utf-8")

    on_screen_texts = [b["on_screen_text"] for b in beat_script] + [sub_hook]
    expected_voice = select_caption_voice(industry, display_name, override=recycled_cap["caption_voice"])
    voice_ok = not (expected_voice == "formal_editorial" and CASUAL_SLANG_PATTERN.search(caption_text + " " + " ".join(on_screen_texts) + " " + final_vo_script))
    cta_ok = all(b not in (caption_text + " " + " ".join(on_screen_texts)).lower() for b in BANNED_SALES_CTAS)
    alan_count = len(re.findall(r"\balan\b", caption_text, flags=re.IGNORECASE))
    guardrail = {
        "passed": bool(cta_ok and voice_ok and alan_count <= 1 and recycled_cap["validation"]["passed"]),
        "detail": f"sales_cta_free={cta_ok}, voice={recycled_cap['voice']} ({recycled_cap['caption_voice']}), slang_free_formal={voice_ok}, alan={alan_count}",
    }
    try:
        from content_review import check_anonymization_leak as _leak
    except Exception:
        _leak = None

    qa_report = build_reels_qa(
        mp4_path=mp4_path, cover_path=plates["cover"], video_meta=video_meta, capture=capture, plate_audit=plate_set["audit"],
        caption_text=caption_text, on_screen_texts=on_screen_texts, lead=lead, guardrail=guardrail, leak_checker=_leak,
    )
    qa_report["engine"] = {
        "motion_profile": profile["name"],
        "sequence": eff_seq,
        "title_scale": plate_set.get("title_scale", 1.0),
        "vo_style": vo_profile["style"],
        "bgm_track": bgm_info["id"],
        "sidechain_ducked": bool(video_meta.get("sidechain_ducked")),
    }
    (reels_dir / "qa_report.json").write_text(json.dumps(qa_report, indent=2, ensure_ascii=False), encoding="utf-8")

    spec_obj = {
        "content_format": "reels", "brand_name": display_name, "industry": industry, "city": city, "domain": domain,
        "sequence_type": eff_seq, "art_direction_preset": eff_style or "auto", "carousel_style": carousel_style_key,
        "primary_style": art_dir["primary_style"], "voice_id": recycled_cap["voice"], "caption_voice": recycled_cap["caption_voice"],
        "hook_pattern_id": recycled_cap["patterns_used"][0] if recycled_cap.get("patterns_used") else "",
        "pain_code": pain_code, "reel_hook_id": reel_hook_id, "attract_cta": bool(attract_cta),
        "vo_script": final_vo_script, "vo_style": vo_profile["style"], "vo_voice": vo_profile["voice"],
        "bgm_track": bgm_info["id"], "bgm_label": bgm_info["label"],
        "creative_note": creative_note, "motion_profile": profile, "video": video_meta,
        "capture": _jsonable({k: v for k, v in capture.items() if k not in {"facts"}}),
        "cover": str(plates["cover"]), "beat_script": beat_script, "on_screen_texts": on_screen_texts,
        "safe_zone": plate_set["audit"]["safe_zone"],
        "audio_mode": audio_mode, "target_duration": eff_target_dur,
    }
    (reels_dir / "reels_spec.json").write_text(json.dumps(spec_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "lead": lead, "reels_dir": str(reels_dir), "video_path": str(mp4_path) if mp4_path.exists() else "",
        "cover_path": str(plates["cover"]), "caption_file": str(caption_file), "caption": caption_text,
        "vo_script": final_vo_script, "bgm_track": bgm_info["id"], "vo_style": vo_profile["style"],
        "beat_script": beat_script, "qa_report": qa_report, "spec": spec_obj, "on_screen_texts": on_screen_texts,
    }
