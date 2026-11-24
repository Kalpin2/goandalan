"""Scene composer for the @goandalan Reels engine.

Turns captured website material + rendered plates into 1080x1920 frames using real easing:
kinetic word cascades, eased/held mobile scrolling, real tab/CTA interaction demos, wipes and
crossfades. Pillow only (no extra rendering framework); FFmpeg encodes the frames in reels_generator.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageDraw

from reels_motion import (
    PHONE,
    REELS_H,
    REELS_W,
    build_scroll_plan,
    clamp01,
    ease,
    pick_scroll_stops,
    waterfall_progress,
)

BASE_DURATIONS: dict[str, list[float]] = {
    "scroll_reveal_showcase": [2.4, 1.5, 3.2, 1.8, 1.4],
    "before_after_ux": [2.2, 1.8, 2.8, 1.7, 1.4],
    "kinetic_editorial": [2.0, 2.2, 2.4, 2.0, 1.6],
}


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
    ) -> None:
        self.seq = sequence_key if sequence_key in BASE_DIR_KEYS else "scroll_reveal_showcase"
        self.plates_paths = plates
        self.reveal_meta = reveal
        self.cap = capture
        self.profile = profile
        self.fps = fps
        self.texts = texts
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
                S(kind="reveal", plate="problem", title="Masalah UX umum", visual="Teks kinetik menyorot satu masalah UX umum di kategori ini (ilustrasi, bukan klaim tentang bisnis nyata).", text=t["problem"], transition="cut"),
                S(kind="zoom", plate="before", title="Sebelum: pola membingungkan", visual="Ilustrasi mobile generik: navigasi padat, tombol bersaing, teks kecil.", text="Padat, kecil, membingungkan.", transition="crossfade"),
                S(kind="phone", plate="phone_after", mode="hero_scroll", title="Sesudah: halaman demo nyata", visual="Wipe bersih ke website konsep asli: hero jelas lalu scroll mulus 390×844.", text="Struktur baru, info jelas.", transition="wipe"),
                S(kind="phone", plate="phone_feature", mode="feature", title="Interaksi lebih baik", visual=feat_visual, text=t["feature"], transition="crossfade"),
                S(kind="reveal", plate="outro", title="Penutup showcase", visual="Pernyataan penutup netral + tag Website Concept (tanpa CTA iklan jasa).", text=t["closing"], transition="crossfade"),
            ]
        elif self.seq == "kinetic_editorial":
            sc = [
                S(kind="reveal", plate="hook", title="Pembuka tipografi besar", visual="Kata-kata hook turun bergiliran (waterfall) di atas poster tipografi.", text=t["hook"], transition="cut"),
                S(kind="reveal", plate="insight", title="Satu wawasan desain", visual="Satu keputusan desain utama ditulis sebagai pernyataan raksasa.", text=t["insight"], transition="crossfade"),
                S(kind="reveal", plate="details", title="Detail antarmuka nyata", visual="3 potongan nyata dari halaman demo masuk bergiliran (modular grid).", text="Detail antarmuka nyata.", transition="crossfade"),
                S(kind="phone", plate="phone_rhythm", mode="rhythm", title="Ritme gerak", visual="Scroll bergaya slow-fast-slow dengan jeda di tiap section.", text="Satu ide per layar.", transition="crossfade"),
                S(kind="reveal", plate="outro", title="Pernyataan penutup", visual="Kalimat penutup kinetik + tag Website Concept.", text=t["closing"], transition="crossfade"),
            ]
        else:
            sc = [
                S(kind="reveal", plate="hook", title="Hook tipografi kinetik", visual="Poster tipografi + intip desktop; kata hook turun bergiliran.", text=t["hook"], transition="cut"),
                S(kind="phone", plate="phone_hero", mode="hero", title="Reveal hero website", visual="Hero website demo asli di dalam bezel HP dengan push-in halus.", text="Hero yang langsung jelas.", transition="crossfade"),
                S(kind="phone", plate="phone_scroll", mode="scroll", title="Scroll mobile terkontrol", visual="Scroll asli 390×844 dengan easing dan jeda di section penting.", text="Scroll mulus, info terbaca.", transition="crossfade"),
                S(kind="phone", plate="phone_feature", mode="feature", title="Demo fitur / tombol kontak", visual=feat_visual, text=t["feature"], transition="crossfade"),
                S(kind="reveal", plate="outro", title="Penutup showcase", visual="Nama brand fiktif + tag Website Concept (tanpa CTA iklan jasa).", text=t["closing"], transition="crossfade"),
            ]
        base = BASE_DURATIONS[self.seq]
        k = max(0.6, min(1.6, target_s / sum(base)))
        for s, d in zip(sc, base):
            s["dur"] = round(d * k, 3)
            s["frames"] = max(6, int(round(s["dur"] * self.fps)))
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
        if z <= 1.001:
            return src_crop
        cw, ch = int(self.sw / z), int(self.sh / z)
        x0 = (self.sw - cw) // 2
        return src_crop.crop((x0, 0, x0 + cw, ch)).resize((self.sw, self.sh), Image.Resampling.BILINEAR)

    def _plan_for(self, idx: int, n: int, mode: str) -> list[float]:
        if idx in self._plans:
            return self._plans[idx]
        prof = self.profile
        stops = pick_scroll_stops(self.cap.get("section_tops", []), self.css_scale, self.sh, self.max_y)
        if mode == "hero_scroll":
            hold = int(n * 0.30)
            plan = [0.0] * hold + build_scroll_plan(n - hold, self.max_y, stops, prof["scroll"], prof["hold_frac"])
        elif mode == "rhythm":
            plan = build_scroll_plan(n, self.max_y, stops, "in_out_quart", 0.46)
        else:
            plan = build_scroll_plan(n, self.max_y, stops, prof["scroll"], prof["hold_frac"])
        self._plans[idx] = plan
        return plan

    # ------------------------------------------------------------------ frame kinds
    def _frame_reveal(self, sc: dict[str, Any], i: int) -> Image.Image:
        base, layer, full = self._reveal_sets(sc["plate"])
        items = self.reveal_meta[sc["plate"]]["items"]
        P = self.profile
        t = i / float(self.fps)
        last_end = 0.04 + (len(items) - 1) * P["stagger"] + P["text_dur"]
        if t >= last_end and i > 0:
            return full
        canvas = base.copy()
        for idx, it in enumerate(items):
            easing = P["text"] if it["kind"] == "word" else "out_quart"
            p = waterfall_progress(idx, t, P["stagger"], P["text_dur"] if it["kind"] == "word" else P["text_dur"] * 1.3, easing)
            if p <= 0:
                continue
            pa = clamp01(p * 1.4)
            shift = P["shift_px"] * (1.0 if it["kind"] == "word" else 1.8)
            dy = int(round((1.0 - min(p, 1.15)) * shift))
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
        z = 1.0 + 0.06 * ease("out_quart", i / max(1, n - 1))
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
        r = 18 + 78 * ease("out_cubic", p)
        a = int(255 * (1 - 0.75 * p))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 196, 0, a), width=8)
        d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(255, 255, 255, int(a * 0.7)))
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
            mix = ease("in_out_sine", (t - 0.50) / 0.12)
            content = Image.blend(a_img, b_img, mix) if mix > 0 else a_img
            content = self._ring(content, cx_s, cy_s - crop_y, (t - 0.30) / 0.25)
            return self._paste_slot(bg, content)
        if cta and "cta_plain" in self.vp_imgs and cta.get("bbox_vp"):
            bb = cta["bbox_vp"]
            cy_s, cx_s = (bb["y"] + bb["h"] / 2) * k, (bb["x"] + bb["w"] / 2) * k
            crop_y = max(0.0, min(self.vp_imgs["cta_plain"].height - self.sh, cy_s - 0.5 * self.sh))
            plain, hl = self._vp_crop("cta_plain", crop_y), self._vp_crop("cta_highlight", crop_y)
            w = 1.0 if t > 0.62 else 0.5 - 0.5 * math.cos(2 * math.pi * 1.6 * (t / 0.62))
            content = Image.blend(plain, hl, clamp01(w))
            content = self._ring(content, cx_s, cy_s - crop_y, (t - 0.70) / 0.26)
            return self._paste_slot(bg, content)
        plan = build_scroll_plan(n, self.max_y, [], self.profile["scroll"], 0.15)
        y = plan[min(i, len(plan) - 1)]
        return self._paste_slot(bg, self._slot_crop(self.max_y * 0.0 + y))

    def _frame_phone(self, sc: dict[str, Any], i: int, n: int, idx: int) -> Image.Image:
        mode = sc["mode"]
        if mode == "feature":
            return self._frame_feature(sc, i, n, idx)
        bg = self.img(sc["plate"])
        if mode == "hero":
            z = 1.0 + 0.07 * (1.0 - ease("out_quart", i / max(1, n - 1)))  # settles to 1.0 = seamless handoff to scroll
            return self._paste_slot(bg, self._zoom_content(self._slot_crop(0), z))
        plan = self._plan_for(idx, n, mode)
        y = plan[min(i, len(plan) - 1)]
        z = 1.0
        if mode == "hero_scroll":
            hold = int(n * 0.30)
            if i < hold:
                z = 1.0 + 0.04 * (1.0 - ease("out_quart", i / max(1, hold - 1)))
        return self._paste_slot(bg, self._zoom_content(self._slot_crop(y), z) if z > 1 else self._slot_crop(y))

    def _frame(self, sc: dict[str, Any], i: int, idx: int) -> Image.Image:
        n = sc["frames"]
        if sc["kind"] == "reveal":
            return self._frame_reveal(sc, i)
        if sc["kind"] == "zoom":
            return self._frame_zoom(sc, i, n)
        return self._frame_phone(sc, i, n, idx)

    # ------------------------------------------------------------------ transitions & iteration
    def _trans_frames(self, kind: str, n_prev: int, phone_to_phone: bool = False) -> int:
        if kind == "cut":
            return 0
        s = self.profile["wipe_s"] if kind == "wipe" else self.profile["fade_s"]
        if phone_to_phone and kind == "crossfade":
            s = min(s, 0.16)  # keep title double-exposure imperceptible
        return min(max(3, int(round(s * self.fps))), n_prev // 2)

    def _transition(self, kind: str, a: Image.Image, b: Image.Image, t: float) -> Image.Image:
        if kind == "wipe":
            x = int(REELS_W * ease("in_out_quart", t))
            out = a.copy()
            if x > 0:
                out.paste(b.crop((0, 0, x, REELS_H)), (0, 0))
                if x < REELS_W:
                    ImageDraw.Draw(out).rectangle((max(0, x - 3), 0, min(REELS_W, x + 3), REELS_H), fill=(255, 196, 0))
            return out
        return Image.blend(a, b, ease("in_out_sine", t))

    def iter_frames(self, plan: list[dict[str, Any]]) -> Iterator[Image.Image]:
        firsts = [self._frame(sc, 0, idx) for idx, sc in enumerate(plan)]
        for idx, sc in enumerate(plan):
            n = sc["frames"]
            nxt = plan[idx + 1] if idx + 1 < len(plan) else None
            tn = self._trans_frames(nxt["transition"], n, sc["kind"] == "phone" and nxt["kind"] == "phone") if nxt else 0
            for i in range(n):
                fr = self._frame(sc, i, idx) if i > 0 else firsts[idx]
                if nxt and tn and i >= n - tn:
                    a = (i - (n - tn) + 1) / float(tn + 1)
                    fr = self._transition(nxt["transition"], fr, firsts[idx + 1], a)
                yield fr


BASE_DIR_KEYS = set(BASE_DURATIONS)
