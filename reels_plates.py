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
    base = (112 if n <= 36 else 96 if n <= 52 else 84 if n <= 68 else 72 if n <= 88 else 64) if big else (92 if n <= 40 else 80 if n <= 60 else 68)
    return max(60, int(base * scale))


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
    content_w = S["right"] - S["left"]

    # crop offsets (css px) for the "details" modular tiles: top / mid / lower sections
    tops = [t for t in sorted(section_tops or []) if t > 200]
    H = max(float(page_height_css or 2400), 1200.0)
    mid = tops[len(tops) // 3] if len(tops) >= 3 else H * 0.38
    low = tops[(2 * len(tops)) // 3] if len(tops) >= 3 and tops[(2 * len(tops)) // 3] > mid + 300 else H * 0.70
    crops = [0.0, float(mid), float(low)]
    crop_labels = ["01 · Hero", "02 · Konten", "03 · Detail"]

    brand_s, city_s = _clip(brand_name, 24), _clip(city or industry, 14)

    def bar(cls: str, left: str, right: str) -> str:
        return f'<div class="bar {cls}"><span class="bl">{_esc(left)}</span><span class="br">{_esc(right)}</span></div>'

    sections: dict[str, str] = {}

    hook_size = _title_size(hook_headline, title_scale)
    sections["hook"] = f"""
  <section id="plate-hook" class="plate p-hook">
    {bar('top', brand_s, city_s)}
    <div class="mid">
      <div class="kicker">WEBSITE CONCEPT · {_esc(_clip(primary_ad, 22))}</div>
      <h1 class="hook-title" style="font-size:{hook_size}px">{_words(hook_headline)}</h1>
      <p class="hook-sub">{_esc(_clip(sub_hook, 96))}</p>
      <div class="hook-peek"><img src="{_esc(desk_uri)}" alt="Website concept" /></div>
    </div>
    {bar('bot', handle, 'konsep fiktif')}
  </section>"""

    def phone_plate(pid: str, kicker: str, title: str, inner_slot: str = "") -> str:
        return f"""
  <section id="plate-{pid}" class="plate p-phone">
    {bar('top', kicker, city_s)}
    <div class="phone-title">{_esc(title)}</div>
    <div class="phone-frame"><div class="phone-slot">{inner_slot}</div></div>
    {bar('bot', handle, 'mobile 390×844')}
  </section>"""

    sections["phone_hero"] = phone_plate("phone_hero", "HERO REVEAL", "Hero yang langsung jelas.")
    sections["phone_scroll"] = phone_plate("phone_scroll", "MOBILE SCROLL", "Scroll mulus, info terbaca.")
    sections["phone_after"] = phone_plate("phone_after", "STRUKTUR BARU", "Struktur baru, info jelas.")
    sections["phone_rhythm"] = phone_plate("phone_rhythm", "RITME MOBILE", "Satu ide per layar.")
    sections["phone_feature"] = phone_plate("phone_feature", "INTERAKSI NYATA", feature_title)

    prob_size = _title_size(problem_text, title_scale, big=False)
    sections["problem"] = f"""
  <section id="plate-problem" class="plate p-hook">
    {bar('top', 'MASALAH UMUM UX', city_s)}
    <div class="mid">
      <div class="kicker">POLA UMUM · {_esc(_clip(industry, 24))}</div>
      <h1 class="hook-title" style="font-size:{prob_size}px">{_words(problem_text)}</h1>
      <p class="hook-sub">Ilustrasi pola umum di kategori ini, bukan situs bisnis nyata.</p>
    </div>
    {bar('bot', handle, 'konsep fiktif')}
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
    {bar('top', 'SEBELUM', 'ilustrasi umum')}
    <div class="phone-title">Padat, kecil, membingungkan.</div>
    <div class="phone-frame"><div class="phone-slot">{wire}</div></div>
    {bar('bot', handle, 'bukan situs nyata')}
  </section>"""

    ins_size = _title_size(insight_text, title_scale, big=False)
    sections["insight"] = f"""
  <section id="plate-insight" class="plate p-phone" style="justify-content:space-between">
    {bar('top', 'SATU KEPUTUSAN DESAIN', city_s)}
    <div class="mid">
      <h1 class="hook-title" style="font-size:{ins_size}px">{_words(insight_text)}</h1>
      <p class="hook-sub">Arah visual {_esc(_clip(primary_ad, 40))}.</p>
    </div>
    {bar('bot', handle, 'konsep fiktif')}
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
    {bar('top', 'DETAIL ANTARMUKA', city_s)}
    <div class="det-head">Detail antarmuka nyata.</div>
    <div class="det-grid">{tiles}</div>
    {bar('bot', handle, 'dari halaman demo')}
  </section>"""

    clo_size = _title_size(closing_text, title_scale, big=False)
    sections["outro"] = f"""
  <section id="plate-outro" class="plate p-hook p-outro">
    {bar('top', 'STUDI KASUS KONSEP FIKTIF', handle)}
    <div class="mid">
      <span class="outro-tag">Website Concept · {_esc(handle)}</span>
      <h1 class="hook-title" style="font-size:{clo_size}px">{_words(closing_text)}</h1>
      <p class="hook-sub">Arah visual {_esc(_clip(primary_ad, 34))} untuk kategori {_esc(_clip(industry.lower(), 30))}. Simpan sebagai referensi tata letak.</p>
    </div>
    {bar('bot', 'GW SAMA ALAN', city_s)}
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
      padding:{S['top']}px {pad_r}px {pad_b}px {S['left']}px; }}
    .bar {{ display:flex; justify-content:space-between; align-items:center; gap:24px; font-family:var(--font-mono);
      font-size:{MIN_FONT_PX}px; line-height:1.1; letter-spacing:0.03em; text-transform:uppercase; opacity:.9; white-space:nowrap; }}
    .bar span {{ overflow:hidden; text-overflow:ellipsis; }}
    .bar .bl {{ max-width:68%; }} .bar .br {{ max-width:38%; text-align:right; }}
    .bar.top {{ padding-bottom:18px; border-bottom:1.5px solid currentColor; }}
    .bar.bot {{ padding-top:18px; border-top:1.5px solid currentColor; }}
    .mid {{ display:flex; flex-direction:column; }}
    .p-hook {{ background:var(--p1-bg); color:var(--p1-ink); }}
    .kicker {{ font-family:var(--font-mono); font-size:{MIN_FONT_PX}px; letter-spacing:.06em; text-transform:uppercase;
      color:var(--p-hi); margin-bottom:26px; }}
    .hook-title {{ font-family:var(--font-display); font-weight:700; line-height:1.0; letter-spacing:-0.02em; }}
    .hook-title .w {{ display:inline-block; }}
    .hook-sub {{ margin-top:30px; font-size:36px; line-height:1.34; opacity:.92; max-width:860px;
      display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
    .hook-peek {{ margin-top:44px; border-radius:22px; overflow:hidden; height:360px; background:var(--bg);
      border:2px solid color-mix(in srgb, var(--p1-ink) 26%, transparent); box-shadow:0 36px 80px rgba(0,0,0,.38); }}
    .hook-peek img {{ width:100%; height:100%; object-fit:cover; object-position:top center; display:block; }}
    .outro-tag {{ align-self:flex-start; padding:12px 24px; border:2px solid var(--p-hi); border-radius:999px; margin-bottom:34px;
      font-family:var(--font-mono); font-size:{MIN_FONT_PX}px; letter-spacing:.04em; color:var(--p-hi); text-transform:uppercase; }}
    .p-phone {{ background:var(--p2-bg); color:var(--p2-ink); justify-content:flex-start; }}
    .p-phone .bar.bot {{ margin-top:auto; }}
    .phone-title {{ margin-top:30px; font-family:var(--font-display); font-size:56px; font-weight:700; line-height:1.1; white-space:nowrap; }}
    .phone-frame {{ position:absolute; left:{PHONE['frame_x']}px; top:{PHONE['frame_y']}px; width:{PHONE['frame_w']}px; height:{PHONE['frame_h']}px;
      border-radius:{PHONE['radius'] + 14}px; background:#141416; padding:16px;
      border:3px solid color-mix(in srgb, var(--p2-ink) 26%, transparent); box-shadow:0 44px 96px rgba(0,0,0,.48); }}
    .phone-slot {{ width:{PHONE['slot_w']}px; height:{PHONE['slot_h']}px; border-radius:{PHONE['radius']}px; background:#09090b; overflow:hidden; }}
    .p-before {{ background:#1c1c1f; color:#EDEDED; justify-content:flex-start; }}
    .p-before .bar.bot {{ margin-top:auto; }}
    .illus {{ width:100%; height:100%; background:#d8d8d8; padding:14px; display:flex; flex-direction:column; gap:12px; font-family:Arial,sans-serif; }}
    .i-nav {{ display:flex; gap:6px; }} .i-nav i {{ flex:1; height:26px; background:#9a9a9a; }}
    .i-banner {{ height:210px; background:#b5b5b5; display:flex; gap:8px; padding:8px; }} .i-banner b {{ flex:1; background:#a0a0a0; }}
    .i-btns {{ display:flex; gap:6px; }} .i-btns span {{ flex:1; background:#777; color:#ddd; font-size:20px; text-align:center; padding:8px 2px; }}
    .i-lines {{ display:flex; flex-direction:column; gap:7px; }} .i-lines u {{ height:12px; background:#a9a9a9; display:block; width:100%; }}
    .i-lines u:nth-child(3n) {{ width:72%; }} .i-lines u:nth-child(4n) {{ width:88%; }}
    .p-reveal {{ background:var(--bg); color:var(--ink); justify-content:flex-start; }}
    .p-reveal .bar.bot {{ margin-top:auto; }}
    .det-head {{ margin-top:30px; font-family:var(--font-display); font-size:60px; font-weight:700; line-height:1.1; }}
    .det-grid {{ margin-top:30px; display:grid; grid-template-columns:440px 440px; grid-template-rows:380px 380px; gap:16px; }}
    .tile {{ position:relative; border-radius:24px; overflow:hidden; border:2px solid var(--border); background-repeat:no-repeat; background-color:var(--surface);
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
