"""Scene composer for the @goandalan Reels engine.

Turns captured website material + rendered plates into 1080x1920 frames using real easing:
kinetic word cascades, eased/held mobile scrolling, real tab/CTA interaction demos, wipes and
crossfades. Pillow only (no extra rendering framework); FFmpeg encodes the frames in reels_generator.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from reels_motion import (
    PHONE,
    REELS_H,
    REELS_W,
    SAFE_ZONE,
    build_scroll_plan,
    clamp01,
    ease,
    pick_scroll_stops,
    waterfall_progress,
)

BASE_DURATIONS: dict[str, list[float]] = {
    "scroll_reveal_showcase": [2.6, 1.8, 3.8, 2.2, 1.8],
    "before_after_ux": [2.4, 2.0, 3.6, 2.2, 1.8],
    "kinetic_editorial": [2.2, 2.4, 2.8, 2.6, 1.8],
}

_CAPTION_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


def _load_caption_font(size: int = 34) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for fpath in _CAPTION_FONT_CANDIDATES:
        p = Path(fpath)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _parse_hex_rgb(hex_color: str | None, fallback: tuple[int, int, int] = (129, 140, 248)) -> tuple[int, int, int]:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            pass
    return fallback


def _load(path: Path, mode: str = "RGB") -> Image.Image:
    img = Image.open(path).convert(mode)
    if img.size != (REELS_W, REELS_H):
        img = img.resize((REELS_W, REELS_H), Image.Resampling.LANCZOS)
    return img


class SceneComposer:
    def __init__(
        self,
        *,
        sequence_key: str,
        plates: dict[str, Path],
        reveal: dict[str, dict[str, Any]],
        capture: dict[str, Any],
        profile: dict[str, Any],
        fps: int,
        texts: dict[str, str],
        vo_cues: list[dict[str, Any]] | None = None,
        accent_hex: str | None = None,
    ) -> None:
        self.seq = sequence_key if sequence_key in BASE_DIR_KEYS else "scroll_reveal_showcase"
        self.plates_paths = plates
        self.reveal_meta = reveal
        self.cap = capture
        self.profile = profile
        self.fps = fps
        self.texts = texts
        self.vo_cues = list(vo_cues or [])
        self.accent_rgb = _parse_hex_rgb(accent_hex)
        self._caption_font = _load_caption_font(34)
        self._caption_cache: dict[str, Image.Image] = {}
        self._cache: dict[str, Image.Image] = {}
        self._plans: dict[int, list[float]] = {}

        sw, sh = PHONE["slot_w"], PHONE["slot_h"]
        self.sw, self.sh = sw, sh
        self.css_scale = sw / float(capture["viewport"][0])
        tall = Image.open(capture["mobile_tall_png"]).convert("RGB")
        th = max(sh, int(round(tall.height * (sw / tall.width))))
        self.mob = tall.resize((sw, th), Image.Resampling.LANCZOS)
        self.max_y = max(0, th - sh)
        self.mask = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(self.mask).rounded_rectangle((0, 0, sw - 1, sh - 1), radius=PHONE["radius"], fill=255)

        self.vp_imgs: dict[str, Image.Image] = {}
        for key in ("cta", "tabs"):
            blk = capture.get(key)
            if blk:
                for sub in ("plain", "highlight", "a", "b"):
                    if sub in blk:
                        im = Image.open(blk[sub]).convert("RGB")
                        self.vp_imgs[f"{key}_{sub}"] = im.resize((sw, int(round(im.height * sw / im.width))), Image.Resampling.LANCZOS)

    # ------------------------------------------------------------------ plan
    def build_plan(self, target_s: float) -> list[dict[str, Any]]:
        t = self.texts
        has_tabs, has_cta = bool(self.cap.get("tabs")), bool(self.cap.get("cta"))
        if has_tabs:
            feat_visual = f"Interaksi nyata: berpindah antar tab ({self.cap['tabs'].get('label_a','')} → {self.cap['tabs'].get('label_b','')}) di halaman demo."
        elif has_cta:
            feat_visual = "Tombol kontak/booking asli pada halaman demo disorot dan ditekan."
        else:
            feat_visual = "Scroll ke bagian bawah halaman demo (info & kontak)."
        S = lambda **k: k  # noqa: E731
        if self.seq == "before_after_ux":
            sc = [
                S(kind="reveal", plate="problem", title="Masalah UX umum", visual="Teks kinetik menyorot satu kendala umum di layar HP.", text=t["problem"], transition="cut"),
                S(kind="zoom", plate="before", title="Sebelum: tampilan lama padat", visual="Ilustrasi mobile generik: navigasi padat, tombol bersaing, teks kecil.", text="Tampilan lama: padat & bingung.", transition="slide_up"),
                S(kind="phone", plate="phone_after", mode="hero_scroll", title="Sesudah: halaman konsep nyata", visual="Wipe bersih ke website konsep asli: hero jelas lalu scroll mulus 390×844.", text="Rapi, terbaca, siap dihubungi.", transition="wipe"),
                S(kind="phone", plate="phone_feature", mode="feature", title="Interaksi nyata di HP", visual=feat_visual, text=t["feature"], transition="slide_left"),
                S(kind="reveal", plate="outro", title="Ringkasan & penutup", visual="Pernyataan penutup jelas + konteks konsep.", text=t["closing"], transition="zoom_cross"),
            ]
        elif self.seq == "kinetic_editorial":
            sc = [
                S(kind="reveal", plate="hook", title="Pembuka utama", visual="Kata-kata hook turun bergiliran (waterfall) dengan gerakan halus.", text=t["hook"], transition="cut"),
                S(kind="reveal", plate="insight", title="Solusi utama", visual="Satu fokus pengalaman pengguna disampaikan jelas.", text=t["insight"], transition="slide_up"),
                S(kind="reveal", plate="details", title="Tiga layar terpenting", visual="3 potongan nyata dari halaman demo masuk bergiliran.", text="Tiga layar paling penting.", transition="slide_left"),
                S(kind="phone", plate="phone_rhythm", mode="rhythm", title="Pengalaman scroll di HP", visual="Scroll bergaya slow-fast-slow dengan jeda baca di tiap section.", text="Nyaman dibaca satu tangan.", transition="slide_up"),
                S(kind="reveal", plate="outro", title="Ringkasan & penutup", visual="Kalimat penutup kinetik yang mudah diingat.", text=t["closing"], transition="zoom_cross"),
            ]
        else:
            sc = [
                S(kind="reveal", plate="hook", title="Hook & konteks konsep", visual="Poster tipografi + intip desktop; kata hook masuk bergiliran dengan push-in halus.", text=t["hook"], transition="cut"),
                S(kind="phone", plate="phone_hero", mode="hero", title="Tampilan 3 detik pertama", visual="Hero website demo asli masuk dari bawah (slide-up) di bezel HP.", text="3 detik pertama langsung jelas.", transition="slide_up"),
                S(kind="phone", plate="phone_scroll", mode="scroll", title="Jelajah layanan & info", visual="Scroll asli 390×844 dengan easing dan jeda baca di setiap section penting.", text="Info & layanan rapi tanpa PDF.", transition="slide_left"),
                S(kind="phone", plate="phone_feature", mode="feature", title="Aksi nyata / tombol kontak", visual=feat_visual, text=t["feature"], transition="slide_left"),
                S(kind="reveal", plate="outro", title="Ringkasan & penutup", visual="Ringkasan jelas + identitas konsep.", text=t["closing"], transition="zoom_cross"),
            ]
        base = BASE_DURATIONS[self.seq]
        # Scale proportionally to follow natural V/O duration (supports 8s..45s without rushing!)
        k = max(0.65, min(3.8, target_s / sum(base)))
        for s, d in zip(sc, base):
            s["dur"] = round(d * k, 3)
            s["frames"] = max(8, int(round(s["dur"] * self.fps)))
        return sc

    # ------------------------------------------------------------------ helpers
    def img(self, name: str) -> Image.Image:
        if name not in self._cache:
            self._cache[name] = _load(self.plates_paths[name])
        return self._cache[name]

    def _reveal_sets(self, plate: str) -> tuple[Image.Image, Image.Image, Image.Image]:
        meta = self.reveal_meta[plate]
        kb, kl, kf = f"{plate}__base", f"{plate}__layer", f"{plate}__full"
        if kb not in self._cache:
            self._cache[kb] = _load(meta["base"])
            self._cache[kl] = _load(meta["layer"], "RGBA")
            self._cache[kf] = Image.alpha_composite(self._cache[kb].convert("RGBA"), self._cache[kl]).convert("RGB")
        return self._cache[kb], self._cache[kl], self._cache[kf]

    def _paste_slot(self, bg: Image.Image, content: Image.Image) -> Image.Image:
        frame = bg.copy()
        frame.paste(content, (PHONE["slot_x"], PHONE["slot_y"]), self.mask)
        return frame

    def _slot_crop(self, y: float) -> Image.Image:
        y = max(0.0, min(float(self.max_y), y))
        return self.mob.transform((self.sw, self.sh), Image.Transform.AFFINE, (1, 0, 0, 0, 1, y), resample=Image.Resampling.BILINEAR)

    def _zoom_content(self, src_crop: Image.Image, z: float) -> Image.Image:
        if z <= 1.0005:
            return src_crop
        cw, ch = int(self.sw / z), int(self.sh / z)
        x0 = (self.sw - cw) // 2
        return src_crop.crop((x0, 0, x0 + cw, ch)).resize((self.sw, self.sh), Image.Resampling.BILINEAR)

    def _ken_burns(self, frame: Image.Image, progress: float, max_scale: float = 1.032) -> Image.Image:
        """Gentle continuous camera push-in so poster/outro scenes stay cinematically alive (0 static freeze)."""
        p = ease("in_out_sine", clamp01(progress))
        z = 1.0 + (max_scale - 1.0) * p
        if z <= 1.0005:
            return frame
        cw, ch = int(round(REELS_W / z)), int(round(REELS_H / z))
        x0 = (REELS_W - cw) // 2
        y0 = (REELS_H - ch) // 2
        return frame.crop((x0, y0, x0 + cw, y0 + ch)).resize((REELS_W, REELS_H), Image.Resampling.BILINEAR)

    def _plan_for(self, idx: int, n: int, mode: str) -> list[float]:
        if idx in self._plans:
            return self._plans[idx]
        prof = self.profile
        stops = pick_scroll_stops(self.cap.get("section_tops", []), self.css_scale, self.sh, self.max_y)
        if mode == "hero_scroll":
            hold = int(n * 0.25)
            plan = [min(float(self.max_y), 4.0 * (j / max(1, hold))) for j in range(hold)] + build_scroll_plan(
                n - hold, self.max_y, stops, prof["scroll"], prof["hold_frac"]
            )
        elif mode == "rhythm":
            plan = build_scroll_plan(n, self.max_y, stops, "in_out_quart", 0.36)
        else:
            plan = build_scroll_plan(n, self.max_y, stops, prof["scroll"], prof["hold_frac"])
        self._plans[idx] = plan
        return plan

    # ------------------------------------------------------------------ frame kinds
    def _frame_reveal(self, sc: dict[str, Any], i: int, n: int) -> Image.Image:
        base, layer, full = self._reveal_sets(sc["plate"])
        items = self.reveal_meta[sc["plate"]]["items"]
        P = self.profile
        t = i / float(self.fps)
        last_end = 0.04 + (len(items) - 1) * P["stagger"] + P["text_dur"]
        if t >= last_end and i > 0:
            # Smooth Ken Burns push-in keeps every post-cascade frame visually alive & avoids freeze flags
            tail_p = (t - last_end) / max(0.4, (n / float(self.fps)) - last_end)
            return self._ken_burns(full, tail_p, max_scale=1.030)
        canvas = base.copy()
        for idx, it in enumerate(items):
            easing = P["text"] if it["kind"] == "word" else "out_quart"
            p = waterfall_progress(idx, t, P["stagger"], P["text_dur"] if it["kind"] == "word" else P["text_dur"] * 1.3, easing)
            if p <= 0:
                continue
            pa = clamp01(p * 1.45)
            shift = P["shift_px"] * (0.9 if it["kind"] == "word" else 1.6)
            dy = int(round((1.0 - min(p, 1.12)) * shift))
            pad = 10
            x0, y0 = max(0, int(it["x"]) - pad), max(0, int(it["y"]) - pad)
            x1, y1 = min(REELS_W, int(it["x"] + it["w"]) + pad), min(REELS_H, int(it["y"] + it["h"]) + pad)
            if x1 <= x0 or y1 <= y0:
                continue
            crop = layer.crop((x0, y0, x1, y1))
            alpha = crop.getchannel("A").point(lambda v, a=pa: int(v * a))
            canvas.paste(crop.convert("RGB"), (x0, y0 + dy), alpha)
        return canvas

    def _frame_zoom(self, sc: dict[str, Any], i: int, n: int) -> Image.Image:
        bg = self.img(sc["plate"])
        z = 1.0 + 0.075 * ease("in_out_sine", i / max(1, n - 1))
        region = bg.crop((PHONE["slot_x"], PHONE["slot_y"], PHONE["slot_x"] + self.sw, PHONE["slot_y"] + self.sh))
        cw, ch = int(self.sw / z), int(self.sh / z)
        x0, y0 = (self.sw - cw) // 2, (self.sh - ch) // 2
        zoomed = region.crop((x0, y0, x0 + cw, y0 + ch)).resize((self.sw, self.sh), Image.Resampling.BILINEAR)
        return self._paste_slot(bg, zoomed)

    def _ring(self, content: Image.Image, cx: float, cy: float, p: float) -> Image.Image:
        if p <= 0 or p >= 1:
            return content
        overlay = Image.new("RGBA", content.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        r_rgb = self.accent_rgb
        r1 = 16 + 74 * ease("out_cubic", p)
        a1 = int(245 * (1 - 0.80 * p))
        d.ellipse((cx - r1, cy - r1, cx + r1, cy + r1), outline=(r_rgb[0], r_rgb[1], r_rgb[2], a1), width=7)
        if p > 0.16:
            p2 = (p - 0.16) / 0.84
            r2 = 12 + 54 * ease("out_quart", p2)
            a2 = int(190 * (1 - p2))
            d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=(255, 255, 255, a2), width=4)
        d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=(255, 255, 255, int(a1 * 0.85)))
        return Image.alpha_composite(content.convert("RGBA"), overlay).convert("RGB")

    def _vp_crop(self, key: str, crop_y: float) -> Image.Image:
        im = self.vp_imgs[key]
        y = int(max(0, min(im.height - self.sh, crop_y)))
        return im.crop((0, y, self.sw, y + self.sh))

    def _frame_feature(self, sc: dict[str, Any], i: int, n: int, idx: int) -> Image.Image:
        bg = self.img(sc["plate"])
        t = i / max(1, n - 1)
        k = self.css_scale
        tabs, cta = self.cap.get("tabs"), self.cap.get("cta")
        if tabs and "tabs_a" in self.vp_imgs and tabs.get("bbox_vp"):
            bb = tabs["bbox_vp"]
            cy_s, cx_s = (bb["y"] + bb["h"] / 2) * k, (bb["x"] + bb["w"] / 2) * k
            crop_y = max(0.0, min(self.vp_imgs["tabs_a"].height - self.sh, cy_s - 0.42 * self.sh))
            a_img, b_img = self._vp_crop("tabs_a", crop_y), self._vp_crop("tabs_b", crop_y)
            mix = ease("in_out_sine", (t - 0.48) / 0.14)
            content = Image.blend(a_img, b_img, mix) if mix > 0 else a_img
            content = self._ring(content, cx_s, cy_s - crop_y, (t - 0.28) / 0.30)
            z = 1.0 + 0.025 * ease("in_out_sine", t)
            return self._paste_slot(bg, self._zoom_content(content, z))
        if cta and "cta_plain" in self.vp_imgs and cta.get("bbox_vp"):
            bb = cta["bbox_vp"]
            cy_s, cx_s = (bb["y"] + bb["h"] / 2) * k, (bb["x"] + bb["w"] / 2) * k
            crop_y = max(0.0, min(self.vp_imgs["cta_plain"].height - self.sh, cy_s - 0.5 * self.sh))
            plain, hl = self._vp_crop("cta_plain", crop_y), self._vp_crop("cta_highlight", crop_y)
            w = 1.0 if t > 0.58 else 0.5 - 0.5 * math.cos(2 * math.pi * 1.5 * (t / 0.58))
            content = Image.blend(plain, hl, clamp01(w))
            content = self._ring(content, cx_s, cy_s - crop_y, (t - 0.62) / 0.30)
            z = 1.0 + 0.025 * ease("in_out_sine", t)
            return self._paste_slot(bg, self._zoom_content(content, z))
        plan = build_scroll_plan(n, self.max_y, [], self.profile["scroll"], 0.15)
        y = plan[min(i, len(plan) - 1)]
        return self._paste_slot(bg, self._slot_crop(y))

    def _frame_phone(self, sc: dict[str, Any], i: int, n: int, idx: int) -> Image.Image:
        mode = sc["mode"]
        if mode == "feature":
            return self._frame_feature(sc, i, n, idx)
        bg = self.img(sc["plate"])
        if mode == "hero":
            z = 1.0 + 0.07 * (1.0 - ease("out_quart", i / max(1, n - 1)))
            return self._paste_slot(bg, self._zoom_content(self._slot_crop(0), z))
        plan = self._plan_for(idx, n, mode)
        y = plan[min(i, len(plan) - 1)]
        z = 1.0
        if mode == "hero_scroll":
            hold = int(n * 0.25)
            if i < hold:
                z = 1.0 + 0.045 * (1.0 - ease("out_quart", i / max(1, hold - 1)))
        return self._paste_slot(bg, self._zoom_content(self._slot_crop(y), z) if z > 1 else self._slot_crop(y))

    def _frame(self, sc: dict[str, Any], i: int, idx: int) -> Image.Image:
        n = sc["frames"]
        if sc["kind"] == "reveal":
            return self._frame_reveal(sc, i, n)
        if sc["kind"] == "zoom":
            return self._frame_zoom(sc, i, n)
        return self._frame_phone(sc, i, n, idx)

    # ------------------------------------------------------------------ transitions & overlays
    def _trans_frames(self, kind: str, n_prev: int, phone_to_phone: bool = False) -> int:
        if kind == "cut":
            return 0
        if kind == "wipe":
            s = max(0.32, self.profile["wipe_s"])
        elif kind in {"slide_up", "slide_left"}:
            s = 0.34 if self.profile["name"] != "refined" else 0.42
        elif kind == "zoom_cross":
            s = 0.36
        else:
            s = min(self.profile["fade_s"], 0.18 if phone_to_phone else 0.35)
        return min(max(5, int(round(s * self.fps))), max(5, n_prev // 3))

    def _transition(self, kind: str, a: Image.Image, b: Image.Image, t: float) -> Image.Image:
        if kind == "wipe":
            p = ease("in_out_quart", t)
            x = int(REELS_W * p)
            out = a.copy()
            if x > 0:
                out.paste(b.crop((0, 0, x, REELS_H)), (0, 0))
                if x < REELS_W:
                    d = ImageDraw.Draw(out)
                    d.rectangle((max(0, x - 4), 0, min(REELS_W, x + 4), REELS_H), fill=self.accent_rgb)
            return out

        if kind == "slide_up":
            p = ease("in_out_quint", t)
            dy_in = int(round((1.0 - p) * REELS_H))
            dy_out = int(round(-p * REELS_H * 0.16))
            dim_a = ImageEnhance.Brightness(a).enhance(1.0 - 0.30 * p)
            out = Image.new("RGB", (REELS_W, REELS_H), (10, 10, 12))
            out.paste(dim_a, (0, dy_out))
            out.paste(b, (0, dy_in))
            return out

        if kind == "slide_left":
            p = ease("in_out_quart", t)
            dx_in = int(round((1.0 - p) * REELS_W))
            dx_out = int(round(-p * REELS_W * 0.22))
            dim_a = ImageEnhance.Brightness(a).enhance(1.0 - 0.28 * p)
            out = Image.new("RGB", (REELS_W, REELS_H), (10, 10, 12))
            out.paste(dim_a, (dx_out, 0))
            out.paste(b, (dx_in, 0))
            return out

        if kind == "zoom_cross":
            p = ease("in_out_sine", t)
            zb = self._ken_burns(b, 1.0 - p, max_scale=1.055)
            return Image.blend(a, zb, p)

        return Image.blend(a, b, ease("in_out_sine", t))

    def _draw_progress_bar(self, frame: Image.Image, progress: float) -> Image.Image:
        """Sleek narrative progress bar right above safe zone top bar (x: 64..960, y: 274..280)."""
        x0, x1 = SAFE_ZONE["left"], SAFE_ZONE["right"]
        y0, y1 = SAFE_ZONE["top"] - 14, SAFE_ZONE["top"] - 8
        ov = Image.new("RGBA", (REELS_W, REELS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle((x0, y0, x1, y1), radius=3, fill=(255, 255, 255, 58))
        fill_w = max(8, int(round((x1 - x0) * clamp01(progress))))
        r, g, b = self.accent_rgb
        d.rounded_rectangle((x0, y0, x0 + fill_w, y1), radius=3, fill=(r, g, b, 235))
        return Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")

    def _caption_overlay_for(self, text: str) -> Image.Image:
        if text in self._caption_cache:
            return self._caption_cache[text]
        # Strictly inside IG safe zone (x 64..960, y 1416..1558) — safely below phone bottom (y=1386)
        safe_l = SAFE_ZONE["left"] + 12
        safe_r = SAFE_ZONE["right"] - 12
        max_w = safe_r - safe_l - 52
        overlay = Image.new("RGBA", (REELS_W, REELS_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            bbox = d.textbbox((0, 0), cand, font=self._caption_font)
            if bbox[2] - bbox[0] <= max_w or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
                if len(lines) >= 2:
                    break
        if cur and len(lines) < 2:
            lines.append(cur)

        if lines:
            line_h = 42
            pad_x, pad_y = 26, 15
            widths = [d.textbbox((0, 0), ln, font=self._caption_font)[2] for ln in lines]
            box_w = min(safe_r - safe_l, max(widths) + pad_x * 2)
            box_h = len(lines) * line_h + pad_y * 2
            cx = (safe_l + safe_r) // 2
            x0 = max(safe_l, cx - box_w // 2)
            x1 = min(safe_r, x0 + box_w)
            y1 = SAFE_ZONE["bottom"] - 20  # 1560 <= 1580 safe bottom
            y0 = y1 - box_h

            r, g, b = self.accent_rgb
            d.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=(10, 10, 14, 224), outline=(r, g, b, 155), width=2)
            # Subtle brand accent top pill accent
            d.rounded_rectangle((x0 + 24, y0, x1 - 24, y0 + 4), radius=2, fill=(r, g, b, 240))
            for idx_l, ln in enumerate(lines):
                lw = d.textbbox((0, 0), ln, font=self._caption_font)[2]
                tx = x0 + (x1 - x0 - lw) // 2
                ty = y0 + pad_y + idx_l * line_h
                d.text((tx, ty), ln, font=self._caption_font, fill=(252, 252, 255, 255))

        self._caption_cache[text] = overlay
        return overlay

    def _apply_synced_caption(self, frame: Image.Image, t_sec: float) -> Image.Image:
        if not self.vo_cues:
            return frame
        active = next((c for c in self.vo_cues if c["start"] <= t_sec <= c["end"]), None)
        if not active or not active.get("text"):
            return frame
        ov = self._caption_overlay_for(active["text"])
        return Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")

    def iter_frames(self, plan: list[dict[str, Any]]) -> Iterator[Image.Image]:
        firsts = [self._frame(sc, 0, idx) for idx, sc in enumerate(plan)]
        total_frames = max(1, sum(sc["frames"] for sc in plan))
        global_i = 0
        for idx, sc in enumerate(plan):
            n = sc["frames"]
            nxt = plan[idx + 1] if idx + 1 < len(plan) else None
            tn = self._trans_frames(nxt["transition"], n, sc["kind"] == "phone" and nxt["kind"] == "phone") if nxt else 0
            for i in range(n):
                fr = self._frame(sc, i, idx) if i > 0 else firsts[idx]
                if nxt and tn and i >= n - tn:
                    a = (i - (n - tn) + 1) / float(tn + 1)
                    fr = self._transition(nxt["transition"], fr, firsts[idx + 1], a)
                fr = self._draw_progress_bar(fr, global_i / float(max(1, total_frames - 1)))
                if self.vo_cues:
                    fr = self._apply_synced_caption(fr, global_i / float(self.fps))
                global_i += 1
                yield fr


BASE_DIR_KEYS = set(BASE_DURATIONS)
