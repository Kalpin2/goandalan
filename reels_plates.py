"""HTML/CSS plate renderer for the @goandalan Reels engine (Playwright).

Renders 1080x1920 plates strictly inside the Instagram Reels safe zone, using the exact palette /
font pairing from the typography_intelligence art direction. Plates that carry kinetic typography or
staggered tiles also export a `base` (animated items hidden) and a transparent `layer` (only the
animated items) so the composer can animate them frame by frame with real easing.
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from reels_motion import MIN_FONT_PX, PHONE, REELS_H, REELS_W, SAFE_ZONE

PLATE_SETS: dict[str, list[str]] = {
    "scroll_reveal_showcase": ["hook", "phone_hero", "phone_scroll", "phone_feature", "outro"],
    "before_after_ux": ["hook", "problem", "before", "phone_after", "phone_feature", "outro"],
    "kinetic_editorial": ["hook", "insight", "details", "phone_rhythm", "outro"],
}

_AUDIT_JS = """
() => {
  const out = [];
  document.querySelectorAll('.plate').forEach(pl => {
    const pr = pl.getBoundingClientRect();
    const walker = document.createTreeWalker(pl, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const t = n.textContent.trim(); if (!t) continue;
      const el = n.parentElement; const cs = getComputedStyle(el);
      if (cs.display === 'none') continue;
      const range = document.createRange(); range.selectNodeContents(n);
      const r = range.getBoundingClientRect(); if (r.width === 0) continue;
      out.push({ plate: pl.id.replace('plate-', ''), text: t.slice(0, 40), l: r.left - pr.left, t: r.top - pr.top,
                 r: r.right - pr.left, b: r.bottom - pr.top, fs: parseFloat(cs.fontSize), illus: !!el.closest('.illus') });
    }
  });
  return out;
}
"""

_ITEMS_JS = """
() => {
  const out = {};
  document.querySelectorAll('.plate').forEach(pl => {
    const pr = pl.getBoundingClientRect();
    const items = Array.from(pl.querySelectorAll('.rv')).map(e => {
      const r = e.getBoundingClientRect();
      return { text: (e.innerText || '').trim().slice(0, 30), x: r.left - pr.left, y: r.top - pr.top, w: r.width, h: r.height,
               kind: e.classList.contains('w') ? 'word' : 'tile' };
    });
    if (items.length) out[pl.id.replace('plate-', '')] = items;
  });
  return out;
}
"""


def _esc(v: Any) -> str:
    return html.escape(str(v or ""), quote=True)


def _words(text: str) -> str:
    return " ".join(f'<span class="w rv">{_esc(w)}</span>' for w in str(text or "").split())


def _clip(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def _title_size(text: str, scale: float, big: bool = True) -> int:
    n = len(text or "")
    base = (96 if n <= 34 else 84 if n <= 52 else 74 if n <= 72 else 66 if n <= 92 else 58) if big else (84 if n <= 38 else 74 if n <= 58 else 64)
    return max(56, int(base * scale))


def render_plate_set(
    *,
    out_dir: Path,
    sequence_key: str,
    brand_name: str,
    industry: str,
    city: str,
    domain: str,
    hook_headline: str,
    sub_hook: str,
    insight_text: str,
    closing_text: str,
    problem_text: str,
    feature_title: str,
    art_dir: dict[str, Any],
    desktop_png: Path,
    mobile_tall_png: Path,
    page_height_css: float,
    section_tops: list[float],
    handle: str,
    title_scale: float = 1.0,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    td = art_dir.get("typography_direction") or {}
    pal = art_dir["palette"]
    poster = td.get("poster_palette") or {
        "poster_bg": pal["accent"], "poster_ink": "#FFFFFF", "poster_accent": pal["ink"],
        "poster_secondary_bg": pal["ink"], "poster_secondary_ink": pal["bg"], "poster_highlight": pal["accent_2"],
    }
    fonts = art_dir["fonts"]
    primary_ad = td.get("primary_art_direction") or art_dir.get("primary_style") or "Editorial"
    names = PLATE_SETS.get(sequence_key, PLATE_SETS["scroll_reveal_showcase"])

    desk_uri = desktop_png.resolve().as_uri()
    tall_uri = mobile_tall_png.resolve().as_uri()
    S = SAFE_ZONE
    pad_r = REELS_W - S["right"]
    pad_b = REELS_H - S["bottom"]

    # crop offsets (css px) for the "details" modular tiles: top / mid / lower sections
    tops = [t for t in sorted(section_tops or []) if t > 200]
    H = max(float(page_height_css or 2400), 1200.0)
    mid = tops[len(tops) // 3] if len(tops) >= 3 else H * 0.38
    low = tops[(2 * len(tops)) // 3] if len(tops) >= 3 and tops[(2 * len(tops)) // 3] > mid + 300 else H * 0.70
    crops = [0.0, float(mid), float(low)]
    crop_labels = ["01 · Tampilan Awal", "02 · Layanan", "03 · Kontak"]

    brand_s, city_s = _clip(brand_name, 22), _clip(city or industry, 22)
    ind_s = _clip(industry, 20)

    def bar(cls: str, left: str, right: str) -> str:
        return f'<div class="bar {cls}"><span class="bl">{_esc(left)}</span><span class="br">{_esc(right)}</span></div>'

    sub_spacer = '<div class="sub-spacer"></div>'
    sections: dict[str, str] = {}

    hook_size = _title_size(hook_headline, title_scale)
    sections["hook"] = f"""
  <section id="plate-hook" class="plate p-hook">
    {bar('top', brand_s, city_s)}
    <div class="mid">
      <div class="step-pill">01 / 05 · KONSEP WEBSITE {_esc(ind_s.upper())}</div>
      <h1 class="hook-title" style="font-size:{hook_size}px">{_words(hook_headline)}</h1>
      <p class="hook-sub">{_esc(_clip(sub_hook, 110))}</p>
      <div class="hook-peek"><img src="{_esc(desk_uri)}" alt="Preview website" /></div>
    </div>
    {sub_spacer}
  </section>"""

    def phone_plate(pid: str, step_tag: str, title: str, inner_slot: str = "") -> str:
        return f"""
  <section id="plate-{pid}" class="plate p-phone">
    {bar('top', step_tag, brand_s)}
    <div class="phone-title">{_esc(_clip(title, 34))}</div>
    <div class="phone-frame"><div class="phone-notch"></div><div class="phone-slot">{inner_slot}</div></div>
  </section>"""

    sections["phone_hero"] = phone_plate("phone_hero", "02 / 05 · TAMPILAN AWAL", "3 detik pertama langsung jelas.")
    sections["phone_scroll"] = phone_plate("phone_scroll", "03 / 05 · LAYANAN & INFO", "Info & layanan rapi tanpa PDF.")
    sections["phone_after"] = phone_plate("phone_after", "03 / 05 · SESUDAH (BARU)", "Rapi, terbaca, siap dihubungi.")
    sections["phone_rhythm"] = phone_plate("phone_rhythm", "04 / 05 · PENGALAMAN HP", "Nyaman dibaca satu tangan.")
    sections["phone_feature"] = phone_plate("phone_feature", "04 / 05 · AKSI NYATA", feature_title)

    prob_size = _title_size(problem_text, title_scale, big=False)
    sections["problem"] = f"""
  <section id="plate-problem" class="plate p-hook">
    {bar('top', '01 / 05 · MASALAH UMUM', ind_s)}
    <div class="mid">
      <div class="step-pill">MASALAH DI LAYAR HP</div>
      <h1 class="hook-title" style="font-size:{prob_size}px">{_words(problem_text)}</h1>
      <p class="hook-sub">Ilustrasi kendala umum yang sering membuat calon pelanggan ragu sebelum menghubungi.</p>
    </div>
    {sub_spacer}
  </section>"""

    wire = """
      <div class="illus">
        <div class="i-nav"><i></i><i></i><i></i><i></i><i></i><i></i></div>
        <div class="i-banner"><b></b><b></b></div>
        <div class="i-btns"><span>MENU</span><span>INFO</span><span>PROMO!!</span><span>KLIK</span></div>
        <div class="i-lines"><u></u><u></u><u></u><u></u><u></u><u></u><u></u><u></u></div>
        <div class="i-btns"><span>KLIK</span><span>INFO</span></div>
        <div class="i-lines"><u></u><u></u><u></u><u></u><u></u><u></u></div>
      </div>"""
    sections["before"] = f"""
  <section id="plate-before" class="plate p-before">
    {bar('top', '02 / 05 · SEBELUM', 'ilustrasi umum')}
    <div class="phone-title">Tampilan lama: padat &amp; bingung.</div>
    <div class="phone-frame"><div class="phone-notch"></div><div class="phone-slot">{wire}</div></div>
  </section>"""

    ins_size = _title_size(insight_text, title_scale, big=False)
    sections["insight"] = f"""
  <section id="plate-insight" class="plate p-phone" style="justify-content:space-between">
    {bar('top', '02 / 05 · SOLUSI UTAMA', brand_s)}
    <div class="mid">
      <div class="step-pill">FOKUS PENGALAMAN PENGGUNA</div>
      <h1 class="hook-title" style="font-size:{ins_size}px">{_words(insight_text)}</h1>
      <p class="hook-sub">Dirancang supaya calon pelanggan menemukan info inti dalam hitungan detik di HP.</p>
    </div>
    {sub_spacer}
  </section>"""

    tiles = ""
    for i, (cy, lab) in enumerate(zip(crops, crop_labels)):
        scale_w = 440
        pos_y = int(round(cy * scale_w / 390.0))
        tiles += (
            f'<div class="tile rv t{i}" style="background-image:url(\'{_esc(tall_uri)}\');'
            f'background-size:{scale_w}px auto;background-position:0 -{pos_y}px"><em>{_esc(lab)}</em></div>'
        )
    sections["details"] = f"""
  <section id="plate-details" class="plate p-reveal">
    {bar('top', '03 / 05 · BAGIAN PENTING', brand_s)}
    <div class="det-head">Tiga layar paling penting.</div>
    <div class="det-grid">{tiles}</div>
  </section>"""

    clo_size = _title_size(closing_text, title_scale, big=False)
    is_dm_cta = "dm kata konsep" in (closing_text or "").lower()
    outro_sub = (
        f"Ingin melihat contoh konsep website rapi untuk usaha {ind_s.lower()} kamu? Kirim pesan sekarang."
        if is_dm_cta
        else f"Konsep tampilan mobile untuk {brand_s} ({ind_s.lower()}) — jelas, ringan, dan siap dihubungi."
    )
    sections["outro"] = f"""
  <section id="plate-outro" class="plate p-hook p-outro">
    {bar('top', '05 / 05 · RINGKASAN', handle)}
    <div class="mid">
      <span class="outro-tag">{'SIAP COBA KONSEP?' if is_dm_cta else f'WEBSITE CONCEPT · {_esc(handle)}'}</span>
      <h1 class="hook-title" style="font-size:{clo_size}px">{_words(closing_text)}</h1>
      <p class="hook-sub">{_esc(_clip(outro_sub, 118))}</p>
      <div class="outro-foot">GW SAMA ALAN · {_esc(city_s.upper())}</div>
    </div>
    {sub_spacer}
  </section>"""

    body = "\n".join(sections[n] for n in names if n in sections)
    css = f"""
    :root {{
      --bg:{pal['bg']}; --surface:{pal['surface']}; --ink:{pal['ink']}; --muted:{pal['muted']};
      --accent:{pal['accent']}; --accent-2:{pal['accent_2']}; --border:{pal['border']};
      --p1-bg:{poster['poster_bg']}; --p1-ink:{poster['poster_ink']};
      --p2-bg:{poster['poster_secondary_bg']}; --p2-ink:{poster['poster_secondary_ink']}; --p-hi:{poster['poster_highlight']};
      --font-display:{fonts['font_display']}; --font-body:{fonts['font_body']}; --font-mono:{fonts['font_mono']};
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ background:#000; display:flex; flex-direction:column; gap:24px; }}
    .plate {{ width:{REELS_W}px; height:{REELS_H}px; position:relative; overflow:hidden; font-family:var(--font-body);
      display:flex; flex-direction:column; justify-content:space-between;
      padding:{S['top'] + 16}px {pad_r}px {pad_b}px {S['left']}px; }}
    .bar {{ display:flex; justify-content:space-between; align-items:center; gap:20px; font-family:var(--font-mono);
      font-size:{MIN_FONT_PX}px; line-height:1.15; letter-spacing:0.03em; text-transform:uppercase; opacity:.88; white-space:nowrap; }}
    .bar span {{ overflow:hidden; text-overflow:ellipsis; }}
    .bar .bl {{ max-width:56%; }} .bar .br {{ max-width:44%; text-align:right; }}
    .bar.top {{ padding-bottom:14px; border-bottom:1.5px solid color-mix(in srgb, currentColor 28%, transparent); }}
    .bar.bot {{ padding-top:14px; border-top:1.5px solid color-mix(in srgb, currentColor 28%, transparent); }}
    .sub-spacer {{ height:168px; flex-shrink:0; }}
    .outro-foot {{ margin-top:36px; font-family:var(--font-mono); font-size:{MIN_FONT_PX}px; letter-spacing:0.04em; opacity:.78; text-transform:uppercase; }}
    .mid {{ display:flex; flex-direction:column; }}
    .p-hook {{ background:radial-gradient(circle at 80% 18%, color-mix(in srgb, var(--p-hi) 18%, transparent), transparent 55%), var(--p1-bg); color:var(--p1-ink); }}
    .step-pill {{ align-self:flex-start; display:inline-flex; align-items:center; padding:8px 18px; border-radius:999px;
      font-family:var(--font-mono); font-size:{MIN_FONT_PX}px; letter-spacing:.04em; text-transform:uppercase;
      background:color-mix(in srgb, var(--p-hi) 18%, transparent); color:var(--p-hi);
      border:1.5px solid color-mix(in srgb, var(--p-hi) 52%, transparent); margin-bottom:24px; }}
    .hook-title {{ font-family:var(--font-display); font-weight:700; line-height:1.12; letter-spacing:-0.015em; }}
    .hook-title .w {{ display:inline-block; }}
    .hook-sub {{ margin-top:24px; font-size:35px; line-height:1.38; opacity:.92; max-width:860px;
      display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
    .hook-peek {{ margin-top:34px; border-radius:22px; overflow:hidden; height:320px; background:var(--bg);
      border:2px solid color-mix(in srgb, var(--p1-ink) 24%, transparent); box-shadow:0 32px 72px rgba(0,0,0,.42); }}
    .hook-peek img {{ width:100%; height:100%; object-fit:cover; object-position:top center; display:block; }}
    .outro-tag {{ align-self:flex-start; padding:10px 22px; border:2px solid var(--p-hi); border-radius:999px; margin-bottom:28px;
      font-family:var(--font-mono); font-size:{MIN_FONT_PX}px; letter-spacing:.04em; color:var(--p-hi); text-transform:uppercase; }}
    .p-phone {{ background:radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--p-hi) 14%, transparent), transparent 62%), var(--p2-bg);
      color:var(--p2-ink); justify-content:flex-start; }}
    .phone-title {{ margin-top:22px; font-family:var(--font-display); font-size:50px; font-weight:700; line-height:1.14;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .phone-frame {{ position:absolute; left:{PHONE['frame_x']}px; top:{PHONE['frame_y']}px; width:{PHONE['frame_w']}px; height:{PHONE['frame_h']}px;
      border-radius:{PHONE['radius'] + 14}px; background:linear-gradient(180deg, #1E1E24 0%, #101014 100%); padding:16px;
      border:3px solid color-mix(in srgb, var(--p2-ink) 28%, transparent);
      box-shadow:0 38px 88px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,0.06) inset; }}
    .phone-notch {{ position:absolute; top:24px; left:50%; transform:translateX(-50%); width:128px; height:22px;
      border-radius:999px; background:#09090B; z-index:4; border:1px solid rgba(255,255,255,0.08); }}
    .phone-slot {{ width:{PHONE['slot_w']}px; height:{PHONE['slot_h']}px; border-radius:{PHONE['radius']}px; background:#09090b; overflow:hidden; }}
    .p-before {{ background:radial-gradient(circle at 50% 40%, rgba(239,68,68,0.12), transparent 60%), #18181B; color:#F4F4F5; justify-content:flex-start; }}
    .illus {{ width:100%; height:100%; background:#d8d8d8; padding:14px; padding-top:40px; display:flex; flex-direction:column; gap:12px; font-family:Arial,sans-serif; }}
    .i-nav {{ display:flex; gap:6px; }} .i-nav i {{ flex:1; height:26px; background:#9a9a9a; }}
    .i-banner {{ height:190px; background:#b5b5b5; display:flex; gap:8px; padding:8px; }} .i-banner b {{ flex:1; background:#a0a0a0; }}
    .i-btns {{ display:flex; gap:6px; }} .i-btns span {{ flex:1; background:#777; color:#ddd; font-size:20px; text-align:center; padding:8px 2px; }}
    .i-lines {{ display:flex; flex-direction:column; gap:7px; }} .i-lines u {{ height:12px; background:#a9a9a9; display:block; width:100%; }}
    .i-lines u:nth-child(3n) {{ width:72%; }} .i-lines u:nth-child(4n) {{ width:88%; }}
    .p-reveal {{ background:var(--bg); color:var(--ink); justify-content:flex-start; }}
    .det-head {{ margin-top:22px; font-family:var(--font-display); font-size:54px; font-weight:700; line-height:1.12; }}
    .det-grid {{ margin-top:26px; display:grid; grid-template-columns:440px 440px; grid-template-rows:340px 340px; gap:16px; }}
    .tile {{ position:relative; border-radius:22px; overflow:hidden; border:2px solid var(--border); background-repeat:no-repeat; background-color:var(--surface);
      box-shadow:0 22px 48px rgba(0,0,0,.18); }}
    .tile.t0 {{ grid-row:1 / span 2; }}
    .tile em {{ position:absolute; left:14px; bottom:14px; font-style:normal; font-family:var(--font-mono); font-size:{MIN_FONT_PX}px;
      background:var(--ink); color:var(--bg); padding:6px 14px; border-radius:999px; }}
    body.hide-rv .rv {{ visibility:hidden; }}
    body.layer-mode, body.layer-mode .plate {{ background:transparent !important; }}
    body.layer-mode .plate * {{ visibility:hidden !important; }}
    body.layer-mode .rv, body.layer-mode .rv * {{ visibility:visible !important; }}
    """
    html_doc = f"""<!DOCTYPE html><html lang="id"><head><meta charset="UTF-8" />
  <link href="{fonts['fonts_url']}" rel="stylesheet" /><style>{css}</style></head><body>{body}</body></html>"""
    html_path = out_dir / "reels_plates.html"
    html_path.write_text(html_doc, encoding="utf-8")

    paths: dict[str, Path] = {n: out_dir / f"plate_{n}.png" for n in names}
    paths["cover"] = out_dir / "cover_reels.png"
    reveal: dict[str, dict[str, Any]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": REELS_W, "height": REELS_H}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(260)

        items_by_plate = page.evaluate(_ITEMS_JS)
        audit_boxes = page.evaluate(_AUDIT_JS)

        for n in names:
            loc = page.locator(f"#plate-{n}")
            loc.screenshot(path=str(paths[n]))
            if n in items_by_plate:
                base_p, layer_p = out_dir / f"plate_{n}_base.png", out_dir / f"plate_{n}_layer.png"
                page.evaluate("() => document.body.classList.add('hide-rv')")
                loc.screenshot(path=str(base_p))
                page.evaluate("() => document.body.classList.remove('hide-rv'); document.body.classList.add('layer-mode')")
                loc.screenshot(path=str(layer_p), omit_background=True)
                page.evaluate("() => document.body.classList.remove('layer-mode')")
                reveal[n] = {"base": base_p, "layer": layer_p, "items": items_by_plate[n]}
        browser.close()

    shutil.copy2(paths["hook"], paths["cover"])

    violations: list[dict[str, Any]] = []
    min_font = 999.0
    for b in audit_boxes:
        if not b["illus"]:
            min_font = min(min_font, b["fs"])
        if b["l"] < S["left"] - 6 or b["r"] > S["right"] + 6 or b["t"] < S["top"] - 6 or b["b"] > S["bottom"] + 6:
            violations.append({"plate": b["plate"], "text": b["text"], "box": [round(b["l"]), round(b["t"]), round(b["r"]), round(b["b"])]})
    return {
        "paths": paths,
        "reveal": reveal,
        "audit": {
            "boxes": len(audit_boxes),
            "violations": violations,
            "min_font_px": round(min_font if min_font < 999 else 0, 1),
            "safe_zone": S,
            "cover_boxes": [b for b in audit_boxes if b["plate"] == "hook"],
        },
        "html_path": html_path,
    }
