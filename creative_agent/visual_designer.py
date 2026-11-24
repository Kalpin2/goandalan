"""Role 3: Visual Designer — 4-Layer Graphic Campaign -> Actual Website Renderer + 2x2 Contact Sheet.

Slides 1 & 2: Bold graphic-design poster & editorial campaign slides driven by
              `typography_direction` (4-layer typographic intelligence: classification,
              personality, art direction/movement, treatment & composition behavior).
Slides 3 & 4: Clean, unobstructed Actual Website Desktop + Mobile reveal & inner-section
              walkthrough closing neutrally with `Website Concept · @goandalan`.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from config import settings


def _esc(val: Any) -> str:
    return html.escape(str(val or ""), quote=True)


def _trim_words(val: Any, max_chars: int) -> str:
    txt = " ".join(str(val or "").split())
    if len(txt) <= max_chars:
        return txt
    cut = txt[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not cut:
        cut = txt[:max_chars].rstrip(" ,;:-")
    return cut + "." if not cut.endswith((".", "!", "?")) else cut


def _img_src(path_str: str | None, out_dir: Path) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if p.is_absolute():
        try:
            return p.relative_to(out_dir.resolve()).as_posix()
        except ValueError:
            return p.as_uri()
    return p.as_posix()


class VisualDesigner:
    """Captures real website screenshots, renders 4-layer 4:5 campaign slides, and builds contact sheets."""

    def capture_from_html(
        self,
        html_path: Path,
        out_dir: Path,
        is_full_demo: bool = False,
    ) -> dict[str, Any]:
        """Capture 4 real multi-angle screenshots, verify mobile header integrity, & extract verified DOM facts."""
        out_dir.mkdir(parents=True, exist_ok=True)
        desktop_hero = out_dir / "desktop.png"
        mobile_hero = out_dir / "mobile.png"
        desktop_detail = out_dir / "detail_desktop.png"
        mobile_detail = out_dir / "detail_mobile.png"
        uri = html_path.resolve().as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Desktop 1280x800 @2x
            d_ctx = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
            d_page = d_ctx.new_page()
            d_page.goto(uri, wait_until="networkidle")
            d_page.evaluate("() => document.fonts.ready")
            d_page.add_style_tag(content=".goandalan-pill { display: none !important; }")
            d_page.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); window.scrollTo(0, 0); }")
            d_page.wait_for_timeout(240)
            d_page.screenshot(path=str(desktop_hero), full_page=False)

            facts = d_page.evaluate(
                """() => {
                  const txt = sel => {
                    const el = document.querySelector(sel);
                    return el ? el.innerText.trim() : '';
                  };
                  const navLinks = Array.from(document.querySelectorAll('.nav-links a'))
                    .map(a => a.innerText.trim()).filter(Boolean);

                  const ledgerRows = Array.from(document.querySelectorAll('.ledger-row')).map(c => ({
                    name: (c.querySelector('h3')?.innerText || '').trim(),
                    price: (c.querySelector('.ledger-price')?.innerText || '').trim(),
                    tag: (c.querySelector('.ledger-tag')?.innerText || '').trim(),
                  })).filter(x => x.name);

                  const menuCards = Array.from(document.querySelectorAll('.menu-card')).map(c => ({
                    name: (c.querySelector('h3')?.innerText || '').trim(),
                    price: (c.querySelector('.menu-price')?.innerText || '').trim(),
                    tag: (c.querySelector('.mono-tag')?.innerText || '').trim(),
                  })).filter(x => x.name);

                  const sigItems = Array.from(document.querySelectorAll('.sig-item, .mini-offer')).map(c => ({
                    name: (c.querySelector('strong')?.innerText || '').trim(),
                    price: (c.querySelector('span')?.innerText || '').trim(),
                    tag: 'SIGNATURE',
                  })).filter(x => x.name);

                  const infoRows = Array.from(document.querySelectorAll('.hero-fact-row, .hero-card-row')).map(r => ({
                    label: (r.querySelector('.hero-fact-label, .hero-card-label')?.innerText || '').trim(),
                    value: (r.querySelector('.hero-fact-val, .hero-card-val')?.innerText || '').trim(),
                  })).filter(x => x.label);

                  const items = ledgerRows.length ? ledgerRows : (menuCards.length ? menuCards : sigItems);
                  const brokenImgs = Array.from(document.querySelectorAll('img')).filter(
                    img => !img.complete || img.naturalWidth === 0
                  ).length;

                  return {
                    brand_header: txt('.brand-mark'),
                    headline: txt('h1'),
                    sub: txt('.hero-sub'),
                    cta_label: txt('.btn-primary'),
                    secondary_label: txt('.btn-secondary'),
                    nav_links: navLinks,
                    items,
                    info_rows: infoRows,
                    faq_count: document.querySelectorAll('.faq-item').length,
                    story_point_count: document.querySelectorAll('.story-point, .reason-card').length,
                    has_layanan_section: Boolean(document.querySelector('section#layanan')),
                    broken_site_images: brokenImgs,
                  };
                }"""
            )

            d_page.evaluate(
                """() => {
                  const sec = document.querySelector('section#layanan');
                  if (sec) {
                    const y = Math.max(0, sec.getBoundingClientRect().top + window.scrollY - 64);
                    window.scrollTo(0, y);
                  } else {
                    const maxY = Math.max(0, document.body.scrollHeight - window.innerHeight);
                    window.scrollTo(0, Math.min(maxY, 240));
                  }
                }"""
            )
            d_page.wait_for_timeout(180)
            d_page.screenshot(path=str(desktop_detail), full_page=False)
            d_ctx.close()

            # Mobile 390x844 @2x + automated brand header truncation check
            m_ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
            m_page = m_ctx.new_page()
            m_page.goto(uri, wait_until="networkidle")
            m_page.evaluate("() => document.fonts.ready")
            m_page.add_style_tag(content=".goandalan-pill { display: none !important; }")
            m_page.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); window.scrollTo(0, 0); }")
            m_page.wait_for_timeout(240)

            mobile_audit = m_page.evaluate(
                """() => {
                  const bm = document.querySelector('.brand-mark');
                  if (!bm) return { ok: true, truncated: false, overflowX: 0 };
                  const style = getComputedStyle(bm);
                  const rect = bm.getBoundingClientRect();
                  const overflowX = Math.max(0, bm.scrollWidth - bm.clientWidth);
                  const pageOverflowX = Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth);
                  const truncated = overflowX > 2 || style.textOverflow === 'ellipsis';
                  return {
                    ok: !truncated && pageOverflowX <= 2,
                    truncated,
                    overflowX,
                    pageOverflowX,
                    brandText: bm.innerText.trim(),
                    brandWidth: Math.round(rect.width),
                    brandHeight: Math.round(rect.height),
                  };
                }"""
            )
            m_page.screenshot(path=str(mobile_hero), full_page=False)

            m_page.evaluate(
                """() => {
                  const sec = document.querySelector('section#layanan');
                  if (sec) {
                    const y = Math.max(0, sec.getBoundingClientRect().top + window.scrollY - 64);
                    window.scrollTo(0, y);
                  } else {
                    const strip = document.querySelector('.signature-ledger, .hero-facts');
                    if (strip) {
                      const y = Math.max(0, strip.getBoundingClientRect().top + window.scrollY - 78);
                      window.scrollTo(0, y);
                    } else {
                      window.scrollTo(0, 380);
                    }
                  }
                }"""
            )
            m_page.wait_for_timeout(180)
            m_page.screenshot(path=str(mobile_detail), full_page=False)
            m_ctx.close()

            browser.close()

        facts["project_status"] = "DEMO PREVIEW" if is_full_demo else "WEBSITE CONCEPT"
        facts["is_full_demo"] = is_full_demo
        facts["mobile_header_audit"] = mobile_audit

        assets: dict[str, str] = {
            "desktop_screenshot": str(desktop_hero),
            "mobile_screenshot": str(mobile_hero),
            "desktop_detail": str(desktop_detail),
            "mobile_detail": str(mobile_detail),
        }
        media_dir = html_path.parent / "media"
        for slot, asset_key in (("hero", "hero_photo"), ("secondary", "secondary_photo"), ("accent", "accent_photo")):
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                cand = media_dir / f"{slot}{ext}"
                if cand.exists():
                    assets[asset_key] = str(cand.resolve())
                    break

        return {"assets": assets, "facts": facts}

    def build_slides_html(self, spec: dict[str, Any], out_dir: Path) -> str:
        """Compile a 4-layer Graphic Campaign (Slides 1-2) -> Actual Website Showcase (Slides 3-4) deck."""
        proj = spec["project"]
        cd = spec["creative_direction"]
        td = spec.get("typography_direction") or cd.get("typography_direction") or {}
        pal = cd["palette"]
        poster_pal = td.get("poster_palette") or {
            "poster_bg": pal["accent"],
            "poster_ink": "#FFFFFF",
            "poster_accent": pal["ink"],
            "poster_secondary_bg": pal["ink"],
            "poster_secondary_ink": pal["bg"],
            "poster_highlight": pal["accent_2"],
        }
        fonts = cd["fonts"]
        geom = cd["geometry"]
        slides = spec["slides"]

        brand_name = proj["brand_name"]
        industry = proj["industry"]
        city = proj.get("city", "")
        domain = proj.get("domain", "")
        issue_num = int(proj.get("issue_num", 1))
        handle = proj.get("handle", f"@{settings.IG_USERNAME}")
        status_badge = proj.get("project_status", "WEBSITE CONCEPT")

        is_sharp = geom.get("radius", "16px") == "0px"
        is_dark = bool(geom.get("dark"))
        primary_ad = td.get("primary_art_direction") or cd["primary_style"]
        treatments = set(td.get("typographic_treatments") or [])
        s1_behavior = slides[0].get("composition", "monumental_headline")
        s2_behavior = slides[1].get("composition", "asymmetric_editorial")

        use_outline_echo = "outline_type" in treatments or s1_behavior == "diagonal_momentum"
        use_rotated_edge = "rotated_typography" in treatments or s1_behavior == "diagonal_momentum"

        frame_rad = "0px" if is_sharp else "12px"
        phone_rad = "10px" if is_sharp else "32px"
        phone_inner_rad = "2px" if is_sharp else "22px"
        phone_bezel = "#1D1D1C" if is_dark else "#131312"

        custom_font_css = ""
        if fonts.get("custom_font_file") and Path(fonts["custom_font_file"]).exists():
            font_uri = Path(fonts["custom_font_file"]).resolve().as_uri()
            custom_font_css = f"@font-face {{ font-family: 'CustomBrandFont'; src: url('{font_uri}'); font-display: swap; }}"

        # P4: Flexible slide rendering driven by slide['kind'] & slide['name'] (never hardcoded to 01_cover..04_details)
        total_slides = len(slides)
        default_kinds = ("poster", "story", "reveal", "details")
        rendered_sections: list[str] = []

        for idx, slide in enumerate(slides, start=1):
            s_name = slide.get("name") or f"{idx:02d}_slide"
            s_kind = slide.get("kind") or default_kinds[min(idx - 1, 3)]
            s_comp = slide.get("composition", "monumental_headline")
            is_last = idx == total_slides
            closing_left = f"WEBSITE CONCEPT · {handle.upper()}" if is_last else handle
            counter = f"{idx:02d} / {total_slides:02d}"

            if s_kind == "poster":
                s_photo = _img_src(slide.get("visual"), out_dir)
                s_peek = _img_src(slide.get("visual_preview") or spec.get("assets", {}).get("desktop_screenshot"), out_dir)
                top_word = slide.get("poster_display_top") or brand_name.split()[0].upper()
                bot_word = slide.get("poster_display_bottom") or "CONCEPT."
                stamp_txt = slide.get("poster_stamp") or industry.upper()
                short_sub = _trim_words(slide.get("subhead") or "", 88)

                if s_comp == "diagonal_momentum":
                    inner = f"""
                    <div class="poster-s1 poster-constructivist">
                      <div class="p1-top-meta">
                        <span>{_esc(brand_name)}</span>
                        <span>{_esc(status_badge)} · {_esc(city or industry)}</span>
                      </div>
                      <div class="p1-const-stage">
                        <div class="p1-vermilion-slash"></div>
                        <div class="p1-outline-ghost" aria-hidden="true">{_esc(top_word)}</div>
                        <h1 class="p1-giant-const">{_esc(top_word)}<br><span class="p1-accent-word">{_esc(bot_word)}</span></h1>
                        <div class="p1-const-visual-row">
                          <div class="p1-cutout-photo">
                            <img src="{_esc(s_photo)}" alt="Brand Craft Visual" />
                            <span class="p1-photo-tag">{_esc(stamp_txt)}</span>
                          </div>
                          <div class="p1-const-copy">
                            <p class="p1-lead-copy">{_esc(short_sub)}</p>
                            <div class="p1-web-peek">
                              <img src="{_esc(s_peek)}" alt="Website Preview" />
                            </div>
                          </div>
                        </div>
                      </div>
                      {'<div class="p1-vertical-edge">' + _esc(primary_ad.upper()) + '</div>' if use_rotated_edge else ''}
                      <div class="p1-foot">
                        <span>{_esc(closing_left)}</span>
                        <span>{counter}</span>
                      </div>
                    </div>
                    """
                else:
                    inner = f"""
                    <div class="poster-s1 poster-monumental">
                      <div class="p1-top-meta">
                        <span>{_esc(brand_name)}</span>
                        <span>{_esc(status_badge)} · {_esc(city or industry)}</span>
                      </div>
                      <div class="p1-mon-hero">
                        <div class="p1-mon-type-wrap">
                          <div class="p1-mon-kicker">{_esc(stamp_txt)} · {_esc(primary_ad)}</div>
                          <h1 class="p1-giant-mon">{_esc(top_word)}<span class="p1-mon-break">{_esc(bot_word)}</span></h1>
                        </div>
                        <div class="p1-mon-collage">
                          <div class="p1-mon-photo">
                            <img src="{_esc(s_photo)}" alt="Editorial Atmosphere" />
                          </div>
                          <div class="p1-mon-inset">
                            <div class="p1-inset-label">{_esc(domain)}</div>
                            <img src="{_esc(s_peek)}" alt="Website Hero Peek" />
                          </div>
                        </div>
                        <div class="p1-mon-bottom-bar">
                          <p class="p1-mon-sub">{_esc(short_sub)}</p>
                          <div class="p1-issue-stamp">
                            <span>WEB</span>
                            <strong>{issue_num:02d}</strong>
                          </div>
                        </div>
                      </div>
                      <div class="p1-foot">
                        <span>{_esc(closing_left)}</span>
                        <span>{counter}</span>
                      </div>
                    </div>
                    """

            elif s_kind == "story":
                s_mob = _img_src(slide.get("visual_mobile") or spec.get("assets", {}).get("mobile_screenshot"), out_dir)
                s_statement = slide.get("poster_statement") or "WEBSITE YANG BEKERJA UNTUK BRAND."
                highlights = slide.get("story_highlights") or [
                    (st["num"].split("/")[0].strip(), st["title"], st["desc"])
                    for st in (slide.get("journey_steps") or [])[:2]
                ]
                highlights_html = "".join(
                    f"""
                    <div class="p2-row">
                      <span class="p2-num">{_esc(num)}</span>
                      <div>
                        <h3>{_esc(title)}</h3>
                        <p>{_esc(_trim_words(desc, 74))}</p>
                      </div>
                    </div>
                    """
                    for num, title, desc in highlights[:2]
                )
                if s_comp == "split_canvas":
                    inner = f"""
                    <div class="poster-s2 poster-split">
                      <div class="p2-top-meta">
                        <span>{_esc(slide.get('kicker', ''))}</span>
                        <span>{_esc(primary_ad)}</span>
                      </div>
                      <div class="p2-split-banner">
                        <div class="p2-mega-line">{_esc(s_statement)}</div>
                      </div>
                      <div class="p2-split-body">
                        <div class="p2-left-col">
                          <h2 class="p2-headline">{slide.get('headline_html', '')}</h2>
                          <div class="p2-ledger">
                            {highlights_html}
                          </div>
                        </div>
                        <div class="p2-phone-col">
                          <div class="p2-phone-shell">
                            <div class="p2-phone-screen"><img src="{_esc(s_mob)}" alt="Actual Mobile Website" /></div>
                          </div>
                        </div>
                      </div>
                      <div class="p2-foot">
                        <span>{_esc(closing_left)}</span>
                        <span>{counter}</span>
                      </div>
                    </div>
                    """
                else:
                    inner = f"""
                    <div class="poster-s2 poster-editorial-dark">
                      <div class="p2-top-meta">
                        <span>{_esc(slide.get('kicker', ''))}</span>
                        <span>{_esc(primary_ad)}</span>
                      </div>
                      <div class="p2-asym-grid">
                        <div class="p2-left-col">
                          <div class="p2-statement-badge">{_esc(s_statement)}</div>
                          <h2 class="p2-headline-serif">{slide.get('headline_html', '')}</h2>
                          <div class="p2-ledger">
                            {highlights_html}
                          </div>
                        </div>
                        <div class="p2-phone-col">
                          <div class="p2-phone-shell">
                            <div class="p2-phone-screen"><img src="{_esc(s_mob)}" alt="Actual Mobile Website" /></div>
                          </div>
                        </div>
                      </div>
                      <div class="p2-foot">
                        <span>{_esc(closing_left)}</span>
                        <span>{counter}</span>
                      </div>
                    </div>
                    """

            elif s_kind == "reveal":
                s_desk = _img_src(slide.get("visual_desktop") or spec.get("assets", {}).get("desktop_screenshot"), out_dir)
                s_mob = _img_src(slide.get("visual_mobile") or spec.get("assets", {}).get("mobile_screenshot"), out_dir)
                inner = f"""
                <div class="showcase-s3">
                  <div class="meta-bar">
                    <span>ACTUAL WEBSITE · {_esc(brand_name)}</span>
                    <span>DESKTOP &amp; MOBILE</span>
                  </div>
                  <div class="s3-body">
                    <div class="s3-head">
                      <span class="mono-kicker">{_esc(slide.get('kicker', ''))}</span>
                      <h2 class="s3-title">{slide.get('headline_html', '')}</h2>
                    </div>
                    <div class="s3-overlap-stage">
                      <div class="browser-shell">
                        <div class="browser-chrome">
                          <span class="b-dot"></span><span class="b-dot"></span><span class="b-dot"></span>
                          <span class="b-url">{_esc(domain)}</span>
                        </div>
                        <div class="browser-viewport">
                          <img src="{_esc(s_desk)}" alt="Actual Desktop Website" />
                        </div>
                      </div>
                      <div class="overlap-phone">
                        <div class="overlap-phone-screen">
                          <img src="{_esc(s_mob)}" alt="Actual Mobile Website" />
                        </div>
                      </div>
                    </div>
                    <div class="s3-caption-bar">
                      <span>VIEWPORT 1280×800 + 390×844</span>
                      <span>{_esc(primary_ad)}</span>
                    </div>
                  </div>
                  <div class="footer-bar">
                    <span>{_esc(closing_left)}</span>
                    <span>{counter}</span>
                  </div>
                </div>
                """

            else:  # details
                s_desk = _img_src(slide.get("visual_desktop_detail") or spec.get("assets", {}).get("desktop_detail"), out_dir)
                s_mob = _img_src(slide.get("visual_mobile_detail") or spec.get("assets", {}).get("mobile_detail"), out_dir)
                points = slide.get("walkthrough_points") or []
                notes_html = "".join(
                    f"""
                    <div class="s4-note-row">
                      <span class="s4-note-num">{_esc(pt['num'])}</span>
                      <div>
                        <h3>{_esc(pt['title'])}</h3>
                        <p>{_esc(_trim_words(pt['desc'], 76))}</p>
                      </div>
                    </div>
                    """
                    for pt in points[:2]
                )
                inner = f"""
                <div class="showcase-s4">
                  <div class="meta-bar">
                    <span>{_esc(brand_name)} · INSIDE SECTIONS</span>
                    <span>WEBSITE CONCEPT</span>
                  </div>
                  <div class="s4-body">
                    <div>
                      <span class="mono-kicker">{_esc(slide.get('kicker', ''))}</span>
                      <h2 class="s4-title">{slide.get('headline_html', '')}</h2>
                    </div>
                    <div class="s4-split-stage">
                      <div class="s4-left">
                        <div class="s4-frame">
                          <div class="df-label"><span>DESKTOP SECTION VIEW</span><span>{_esc(domain)}</span></div>
                          <div class="s4-desk-img"><img src="{_esc(s_desk)}" alt="Inner Desktop Section" /></div>
                        </div>
                        <div class="s4-notes-ledger">
                          {notes_html}
                        </div>
                      </div>
                      <div class="s4-right">
                        <div class="s4-frame s4-mob-frame">
                          <div class="df-label"><span>MOBILE SCROLL</span></div>
                          <div class="s4-mob-img"><img src="{_esc(s_mob)}" alt="Inner Mobile Section" /></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="footer-bar">
                    <span>{_esc(closing_left)}</span>
                    <span>{counter}</span>
                  </div>
                </div>
                """

            rendered_sections.append(
                f'  <section class="slide" data-name="{_esc(s_name)}" data-kind="{_esc(s_kind)}" data-n="{idx}">{inner}</section>'
            )

        slides_markup = "\n".join(rendered_sections)

        return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <link href="{fonts['fonts_url']}" rel="stylesheet" />
  <style>
    {custom_font_css}
    :root {{
      --bg: {pal['bg']};
      --surface: {pal['surface']};
      --ink: {pal['ink']};
      --muted: {pal['muted']};
      --accent: {pal['accent']};
      --accent-2: {pal['accent_2']};
      --border: {pal['border']};

      --p1-bg: {poster_pal['poster_bg']};
      --p1-ink: {poster_pal['poster_ink']};
      --p1-accent: {poster_pal['poster_accent']};
      --p2-bg: {poster_pal['poster_secondary_bg']};
      --p2-ink: {poster_pal['poster_secondary_ink']};
      --p-hi: {poster_pal['poster_highlight']};

      --font-display: {fonts['font_display']};
      --font-body: {fonts['font_body']};
      --font-mono: {fonts['font_mono']};
      --radius: {frame_rad};
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #111; display: flex; flex-direction: column; gap: 40px; align-items: center; padding: 40px; }}

    .slide {{
      width: 1080px;
      height: 1350px;
      position: relative;
      overflow: hidden;
      font-family: var(--font-body);
    }}

    /* ================= SLIDE 1: FULL-BLEED GRAPHIC POSTER ================= */
    .poster-s1 {{
      width: 100%; height: 100%;
      background: var(--p1-bg);
      color: var(--p1-ink);
      padding: 58px 64px;
      display: flex; flex-direction: column; justify-content: space-between;
      position: relative;
    }}
    .p1-top-meta, .p1-foot {{
      display: flex; justify-content: space-between; align-items: center;
      font-family: var(--font-mono); font-size: 16px; letter-spacing: 0.1em;
      text-transform: uppercase; opacity: 0.9;
      position: relative; z-index: 4;
    }}
    .p1-top-meta {{ padding-bottom: 16px; border-bottom: 1.5px solid color-mix(in srgb, var(--p1-ink) 28%, transparent); }}
    .p1-foot {{ padding-top: 16px; border-top: 1.5px solid color-mix(in srgb, var(--p1-ink) 28%, transparent); }}

    /* Slide 1 Variant A: Monumental Heritage / Art-Magazine Poster */
    .p1-mon-hero {{
      flex: 1; display: flex; flex-direction: column; justify-content: space-between;
      padding: 22px 0 18px; gap: 18px; min-height: 0; position: relative; z-index: 3;
    }}
    .p1-mon-kicker {{
      font-family: var(--font-mono); font-size: 16px; letter-spacing: 0.12em;
      text-transform: uppercase; color: var(--p-hi); margin-bottom: 8px;
    }}
    .p1-giant-mon {{
      font-family: var(--font-display);
      font-size: 126px; font-weight: 700; line-height: 0.88;
      letter-spacing: -0.04em; text-transform: uppercase;
      color: var(--p1-ink);
    }}
    .p1-mon-break {{
      display: block; color: var(--p-hi); padding-left: 48px;
    }}
    .p1-mon-collage {{
      position: relative; flex: 1; min-height: 0; width: 100%;
    }}
    .p1-mon-photo {{
      width: 78%; height: 100%; border-radius: var(--radius); overflow: hidden;
      border: 2px solid color-mix(in srgb, var(--p1-ink) 22%, transparent);
    }}
    .p1-mon-photo img {{ width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }}
    .p1-mon-inset {{
      position: absolute; right: 0; bottom: 18px; width: 410px;
      background: var(--p1-accent); padding: 10px; border-radius: var(--radius);
      box-shadow: 0 26px 56px rgba(0,0,0,0.38);
      border: 1.5px solid color-mix(in srgb, var(--p1-ink) 25%, transparent);
    }}
    .p1-inset-label {{
      font-family: var(--font-mono); font-size: 14px; letter-spacing: 0.08em;
      color: var(--p-hi); margin-bottom: 8px; text-transform: uppercase;
    }}
    .p1-mon-inset img {{ width: 100%; aspect-ratio: 16 / 10; object-fit: cover; object-position: top center; border-radius: 4px; display: block; }}
    .p1-mon-bottom-bar {{
      display: flex; justify-content: space-between; align-items: flex-end; gap: 24px;
      padding-top: 8px;
    }}
    .p1-mon-sub {{
      font-size: 32px; line-height: 1.28; max-width: 760px;
      color: var(--p1-ink); opacity: 0.94;
    }}
    .p1-issue-stamp {{
      flex-shrink: 0; width: 102px; height: 102px;
      border: 2px solid var(--p-hi); border-radius: 999px;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      font-family: var(--font-mono); color: var(--p-hi);
    }}
    .p1-issue-stamp span {{ font-size: 12px; letter-spacing: 0.14em; }}
    .p1-issue-stamp strong {{ font-size: 36px; line-height: 1; }}

    /* Slide 1 Variant B: Constructivist / Diagonal Momentum Poster */
    .poster-constructivist {{ overflow: hidden; }}
    .p1-const-stage {{
      flex: 1; display: flex; flex-direction: column; justify-content: space-between;
      padding: 24px 0 18px; position: relative; z-index: 3; min-height: 0; overflow: hidden;
    }}
    .p1-vermilion-slash {{
      position: absolute; right: 8px; top: 36px; width: 340px; height: 112px;
      background: var(--p1-accent); transform: rotate(-8deg); opacity: 0.92; z-index: 0;
    }}
    .p1-outline-ghost {{
      position: absolute; left: 0px; top: 8px; z-index: 1;
      font-family: var(--font-display); font-size: 166px; line-height: 0.85;
      letter-spacing: 0.01em; text-transform: uppercase;
      color: transparent; -webkit-text-stroke: 2px color-mix(in srgb, var(--p1-ink) 22%, transparent);
      pointer-events: none; user-select: none;
    }}
    .p1-giant-const {{
      position: relative; z-index: 2;
      font-family: var(--font-display); font-size: 148px; font-weight: 800;
      line-height: 0.88; letter-spacing: 0.01em; text-transform: uppercase;
      color: var(--p1-ink);
    }}
    .p1-accent-word {{ color: var(--p1-accent); }}
    .p1-const-visual-row {{
      position: relative; z-index: 2;
      display: grid; grid-template-columns: 1.12fr 0.88fr; gap: 24px;
      align-items: end; flex: 1; min-height: 0; margin-top: 20px;
    }}
    .p1-cutout-photo {{
      height: 100%; max-height: 460px; position: relative; overflow: hidden;
      border-top: 5px solid var(--p1-accent);
    }}
    .p1-cutout-photo img {{ width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }}
    .p1-photo-tag {{
      position: absolute; left: 16px; bottom: 16px;
      background: var(--p1-bg); color: var(--p1-ink);
      font-family: var(--font-mono); font-size: 15px; letter-spacing: 0.1em;
      padding: 6px 12px;
    }}
    .p1-const-copy {{ display: flex; flex-direction: column; justify-content: space-between; gap: 16px; height: 100%; max-height: 460px; }}
    .p1-lead-copy {{ font-size: 32px; line-height: 1.24; color: var(--p1-ink); opacity: 0.94; }}
    .p1-web-peek {{ border: 2px solid color-mix(in srgb, var(--p1-ink) 28%, transparent); overflow: hidden; }}
    .p1-web-peek img {{ width: 100%; aspect-ratio: 16 / 10; object-fit: cover; object-position: top center; display: block; }}
    .p1-vertical-edge {{
      position: absolute; right: 14px; bottom: 104px;
      writing-mode: vertical-rl;
      font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.2em;
      color: var(--p1-ink); opacity: 0.5; white-space: nowrap;
    }}

    /* ================= SLIDE 2: EDITORIAL CAMPAIGN STORY ================= */
    .poster-s2 {{
      width: 100%; height: 100%;
      background: var(--p2-bg);
      color: var(--p2-ink);
      padding: 58px 64px;
      display: flex; flex-direction: column; justify-content: space-between;
    }}
    .p2-top-meta, .p2-foot {{
      display: flex; justify-content: space-between; align-items: center;
      font-family: var(--font-mono); font-size: 16px; letter-spacing: 0.1em;
      text-transform: uppercase; opacity: 0.88;
    }}
    .p2-top-meta {{ padding-bottom: 16px; border-bottom: 1.5px solid color-mix(in srgb, var(--p2-ink) 26%, transparent); }}
    .p2-foot {{ padding-top: 16px; border-top: 1.5px solid color-mix(in srgb, var(--p2-ink) 26%, transparent); }}

    .p2-split-banner {{
      padding: 20px 0 16px;
      border-bottom: 2px solid color-mix(in srgb, var(--p2-ink) 35%, transparent);
    }}
    .p2-mega-line {{
      font-family: var(--font-display); font-size: 74px; font-weight: 800;
      line-height: 0.94; letter-spacing: 0.01em; text-transform: uppercase;
      color: var(--p2-ink);
    }}
    .p2-split-body, .p2-asym-grid {{
      flex: 1; display: grid; grid-template-columns: 1.15fr 0.85fr;
      gap: 38px; align-items: center; padding: 24px 0; min-height: 0;
    }}
    .p2-left-col {{ display: flex; flex-direction: column; gap: 22px; }}
    .p2-statement-badge {{
      display: inline-block; align-self: flex-start;
      background: var(--p-hi); color: #161412;
      font-family: var(--font-mono); font-size: 16px; font-weight: 600;
      letter-spacing: 0.08em; padding: 8px 16px;
    }}
    .p2-headline {{
      font-family: var(--font-body); font-size: 38px; font-weight: 700;
      line-height: 1.16; letter-spacing: -0.02em;
    }}
    .p2-headline em, .p2-headline-serif em {{ font-style: italic; color: var(--p-hi); }}
    .p2-headline-serif {{
      font-family: var(--font-display); font-size: 52px; font-weight: 700;
      line-height: 1.06; letter-spacing: -0.02em;
    }}
    .p2-sub {{ font-size: 32px; line-height: 1.28; opacity: 0.92; }}
    .p2-ledger {{ border-top: 1.5px solid color-mix(in srgb, var(--p2-ink) 30%, transparent); }}
    .p2-row {{
      display: grid; grid-template-columns: 48px 1fr; gap: 12px;
      padding: 16px 0; border-bottom: 1px solid color-mix(in srgb, var(--p2-ink) 22%, transparent);
    }}
    .p2-num {{ font-family: var(--font-mono); font-size: 20px; font-weight: 600; color: var(--p-hi); }}
    .p2-row h3 {{ font-size: 34px; font-weight: 700; margin-bottom: 6px; line-height: 1.12; }}
    .p2-row p {{ font-size: 32px; line-height: 1.24; opacity: 0.9; }}

    .p2-phone-col {{ display: flex; justify-content: center; align-items: center; height: 100%; }}
    .p2-phone-shell {{
      width: 374px; height: 790px; background: {phone_bezel};
      border-radius: {phone_rad}; padding: 13px;
      box-shadow: 0 28px 64px rgba(0,0,0,0.34);
      border: 1.5px solid color-mix(in srgb, var(--p2-ink) 22%, transparent);
    }}
    .p2-phone-screen {{ width: 100%; height: 100%; border-radius: {phone_inner_rad}; overflow: hidden; background: var(--bg); }}
    .p2-phone-screen img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}

    /* ================= SLIDES 3 & 4: ACTUAL WEBSITE SHOWCASE ================= */
    .showcase-s3, .showcase-s4 {{
      width: 100%; height: 100%;
      background: var(--bg); color: var(--ink);
      padding: 58px 64px;
      display: flex; flex-direction: column; justify-content: space-between;
    }}
    .meta-bar, .footer-bar {{
      display: flex; justify-content: space-between; align-items: center;
      font-family: var(--font-mono); font-size: 16px; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--muted); flex-shrink: 0;
    }}
    .meta-bar {{ padding-bottom: 16px; border-bottom: 1px solid var(--border); }}
    .footer-bar {{ padding-top: 16px; border-top: 1px solid var(--border); }}
    .mono-kicker {{
      display: inline-block; font-family: var(--font-mono); font-size: 15px; font-weight: 600;
      letter-spacing: 0.09em; text-transform: uppercase; color: var(--accent); margin-bottom: 8px;
    }}

    .s3-body {{ flex: 1; display: flex; flex-direction: column; justify-content: space-between; padding: 20px 0 14px; gap: 18px; min-height: 0; }}
    .s3-title {{
      font-family: var(--font-display); font-size: 46px; font-weight: 700;
      line-height: 1.08; letter-spacing: -0.02em;
    }}
    .s3-overlap-stage {{ position: relative; flex: 1; min-height: 0; width: 100%; }}
    .browser-shell {{
      width: 836px; background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 14px;
      box-shadow: {'none' if is_sharp else '0 24px 54px rgba(0,0,0,0.12)'};
    }}
    .browser-chrome {{ display: flex; align-items: center; gap: 8px; margin-bottom: 11px; padding: 0 4px; }}
    .b-dot {{ width: 9px; height: 9px; border-radius: {'0' if is_sharp else '50%'}; background: var(--border); }}
    .b-url {{
      margin-left: 10px; font-family: var(--font-mono); font-size: 14px; color: var(--muted);
      background: var(--bg); padding: 4px 14px; border-radius: {'0px' if is_sharp else '999px'}; border: 1px solid var(--border);
    }}
    .browser-viewport {{ width: 100%; height: 520px; border-radius: {'0px' if is_sharp else '8px'}; overflow: hidden; border: 1px solid var(--border); background: var(--bg); }}
    .browser-viewport img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
    .overlap-phone {{
      position: absolute; right: 0; bottom: 0; width: 318px; height: 656px;
      background: {phone_bezel}; border-radius: {phone_rad}; padding: 12px;
      box-shadow: 0 28px 66px rgba(0,0,0,0.28);
    }}
    .overlap-phone-screen {{ width: 100%; height: 100%; border-radius: {phone_inner_rad}; overflow: hidden; background: var(--bg); }}
    .overlap-phone-screen img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
    .s3-caption-bar {{ display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 14px; color: var(--muted); }}

    .s4-body {{ flex: 1; display: flex; flex-direction: column; gap: 20px; padding: 20px 0 14px; min-height: 0; }}
    .s4-title {{
      font-family: var(--font-body); font-size: 42px; font-weight: 700;
      line-height: 1.12; letter-spacing: -0.025em;
    }}
    .s4-split-stage {{ flex: 1; display: grid; grid-template-columns: 1.32fr 0.88fr; gap: 24px; min-height: 0; }}
    .s4-left {{ display: flex; flex-direction: column; justify-content: space-between; gap: 18px; min-height: 0; }}
    .s4-right {{ display: flex; flex-direction: column; min-height: 0; }}
    .s4-frame {{
      border: 1px solid var(--border); border-radius: var(--radius);
      overflow: hidden; background: var(--bg); display: flex; flex-direction: column;
    }}
    .df-label {{
      display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 13px;
      letter-spacing: 0.08em; color: var(--muted); padding: 8px 12px;
      background: var(--surface); border-bottom: 1px solid var(--border);
    }}
    .s4-desk-img {{ width: 100%; aspect-ratio: 16 / 10; overflow: hidden; }}
    .s4-desk-img img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
    .s4-mob-frame {{ flex: 1; min-height: 0; background: var(--bg); }}
    .s4-mob-img {{ flex: 1; min-height: 0; overflow: hidden; background: var(--bg); padding: 6px; }}
    .s4-mob-img img {{ width: 100%; height: 100%; object-fit: contain; object-position: top center; display: block; }}

    .s4-notes-ledger {{ border-top: 1.5px solid var(--ink); display: flex; flex-direction: column; }}
    .s4-note-row {{
      display: grid; grid-template-columns: 1fr; gap: 4px;
      padding: 12px 0; border-bottom: 1px solid var(--border);
    }}
    .s4-note-num {{ font-family: var(--font-mono); font-size: 15px; font-weight: 600; color: var(--accent); }}
    .s4-note-row h3 {{ font-size: 34px; font-weight: 700; color: var(--ink); line-height: 1.12; }}
    .s4-note-row p {{ font-size: 32px; line-height: 1.24; color: var(--muted); }}
  </style>
</head>
<body>
{slides_markup}
</body>
</html>
"""

    def render_slides(
        self,
        spec: dict[str, Any],
        out_dir: Path,
        only_slide: int | None = None,
        scale: int = 2,
    ) -> dict[str, Any]:
        """Render 4 separate PNGs (1080x1350 @2x = 2160x2700), plus 2x2 contact_sheet.png & cover_grid.png."""
        out_dir.mkdir(parents=True, exist_ok=True)
        expected_pngs = {
            f"{s.get('name') or f'slide_{idx:02d}'}.png"
            for idx, s in enumerate(spec.get("slides") or [], start=1)
        }
        if only_slide is None:
            for existing in out_dir.glob("0[1-4]_*.png"):
                if existing.name not in expected_pngs:
                    existing.unlink()
        for stale in ("02_problem_thinking.png", "03_preview.png", "04_closing.png"):
            p = out_dir / stale
            if p.exists():
                p.unlink()

        slides_html = self.build_slides_html(spec, out_dir)
        slides_file = out_dir / "slides.html"
        slides_file.write_text(slides_html, encoding="utf-8")

        slide_results: list[dict[str, Any]] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 1500}, device_scale_factor=scale)
            page.goto(slides_file.resolve().as_uri(), wait_until="networkidle")
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(260)

            locator = page.locator(".slide")
            count = locator.count()
            for i in range(count):
                slide_num = i + 1
                slide = locator.nth(i)
                name = slide.get_attribute("data-name") or f"slide_{slide_num:02d}"
                target = out_dir / f"{name}.png"
                if only_slide is None or only_slide == slide_num or not target.exists():
                    slide.screenshot(path=str(target))
                with Image.open(target) as im:
                    w, h = im.size
                slide_results.append(
                    {
                        "n": slide_num,
                        "name": f"{name}.png",
                        "path": str(target),
                        "width": w,
                        "height": h,
                        "size_bytes": target.stat().st_size,
                    }
                )
            browser.close()

        contact_sheet_info = self.build_contact_sheet(spec, slide_results, out_dir / "contact_sheet.png")
        cover_grid_info = self.build_cover_grid_preview(Path(slide_results[0]["path"]), out_dir / "cover_grid.png")

        return {
            "slides_html": str(slides_file),
            "slides": slide_results,
            "contact_sheet": contact_sheet_info,
            "cover_grid": cover_grid_info,
        }

    def render_candidate_test_slide(
        self,
        candidate: dict[str, Any],
        brand_name: str,
        photo_path: Path,
        target_png: Path,
    ) -> dict[str, Any]:
        """Section 15.2 Step 5: Render 1 standalone test slide for a newly proposed typography candidate."""
        target_png.parent.mkdir(parents=True, exist_ok=True)
        html_path = target_png.with_suffix(".html")
        photo_uri = photo_path.resolve().as_uri() if photo_path.exists() else ""

        doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=IBM+Plex+Mono:wght@500;600&family=Zilla+Slab:wght@700&display=swap" rel="stylesheet" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #111; }}
    .test-slide {{
      width: 1080px; height: 1350px; background: #1E3A2A; color: #F9F2E4;
      padding: 64px; display: flex; flex-direction: column; justify-content: space-between;
      font-family: 'Zilla Slab', serif; position: relative; overflow: hidden;
    }}
    .enamel-band {{
      background: #D1532B; color: #FFF8EE; padding: 14px 22px;
      display: flex; justify-content: space-between; align-items: center;
      font-family: 'IBM Plex Mono', monospace; font-size: 16px; letter-spacing: 0.12em;
    }}
    .woodblock {{
      font-family: 'Barlow Condensed', sans-serif; font-size: 176px; font-weight: 800;
      line-height: 0.86; text-transform: uppercase; letter-spacing: -0.01em;
    }}
    .woodblock span {{ color: #E8BC66; display: block; }}
    .photo-strip {{
      height: 490px; border: 3px solid #E8BC66; overflow: hidden;
    }}
    .photo-strip img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .note {{ font-family: 'IBM Plex Mono', monospace; font-size: 17px; line-height: 1.5; color: #F9F2E4; opacity: 0.92; }}
  </style>
</head>
<body>
  <section class="test-slide" id="test">
    <div class="enamel-band">
      <span>CANDIDATE TEST · {_esc(candidate['id'].upper())}</span>
      <span>STATUS: CANDIDATE</span>
    </div>
    <h1 class="woodblock">SANGRAI<span>NUSANTARA.</span></h1>
    <div class="photo-strip"><img src="{_esc(photo_uri)}" alt="Roastery Craft" /></div>
    <p class="note">{_esc(brand_name)} — Uji tipografi kandidat '{_esc(candidate['name'])}' (enamel color-blocking + woodblock numerals). Menunggu review &amp; persetujuan user.</p>
  </section>
</body>
</html>
"""
        html_path.write_text(doc, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(180)
            page.locator("#test").screenshot(path=str(target_png))
            browser.close()
        return {"path": str(target_png), "size_bytes": target_png.stat().st_size}

    def build_contact_sheet(
        self,
        spec: dict[str, Any],
        slide_results: list[dict[str, Any]],
        target_path: Path,
    ) -> dict[str, Any]:
        """Build a crisp 2x2 Contact Sheet PNG with 4-layer typography & art direction header."""
        tile_w, tile_h = 900, 1125
        pad = 48
        header_h = 148
        label_h = 36
        canvas_w = pad * 3 + tile_w * 2
        canvas_h = header_h + pad * 3 + (tile_h + label_h) * 2

        sheet = Image.new("RGB", (canvas_w, canvas_h), "#141413")
        draw = ImageDraw.Draw(sheet)

        try:
            font_lg = ImageFont.truetype("arial.ttf", 32)
            font_sm = ImageFont.truetype("arial.ttf", 19)
        except OSError:
            font_lg = ImageFont.load_default()
            font_sm = ImageFont.load_default()

        proj = spec["project"]
        cd = spec["creative_direction"]
        td = spec.get("typography_direction") or cd.get("typography_direction") or {}
        pal = cd["palette"]
        pp = td.get("poster_palette") or {}

        title_line = f"{proj['brand_name']} — 2x2 Contact Sheet ({td.get('primary_art_direction') or cd['primary_style']})"
        meta_line = f"Type: {cd.get('font_pair_label', '')}  |  Treatments: {', '.join((td.get('typographic_treatments') or [])[:3])}"
        draw.text((pad, 28), title_line, fill="#F6F3EC", font=font_lg)
        draw.text((pad, 78), meta_line, fill="#A8A39A", font=font_sm)

        swatch_colors = [
            pp.get("poster_bg", pal["accent"]),
            pp.get("poster_secondary_bg", pal["ink"]),
            pal["bg"],
            pal["accent"],
        ]
        sw_size = 34
        start_x = canvas_w - pad - (len(swatch_colors) * (sw_size + 10))
        for idx, col in enumerate(swatch_colors):
            x0 = start_x + idx * (sw_size + 10)
            draw.rectangle([x0, 44, x0 + sw_size, 44 + sw_size], fill=col, outline="#444440", width=1)

        positions = [
            (pad, header_h + pad),
            (pad * 2 + tile_w, header_h + pad),
            (pad, header_h + pad * 2 + tile_h + label_h),
            (pad * 2 + tile_w, header_h + pad * 2 + tile_h + label_h),
        ]

        for idx, s_info in enumerate(slide_results[:4]):
            x, y = positions[idx]
            comp = spec["slides"][idx].get("composition", "")
            role = spec["slides"][idx].get("role", "")
            draw.text((x, y), f"0{idx + 1} / {role.upper()}  [{comp}]", fill="#D6D2C9", font=font_sm)
            with Image.open(s_info["path"]) as im:
                resized = im.convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
                sheet.paste(resized, (x, y + label_h))
            draw.rectangle([x, y + label_h, x + tile_w, y + label_h + tile_h], outline="#333330", width=2)

        sheet.save(target_path, format="PNG", optimize=True)
        return {
            "path": str(target_path),
            "width": canvas_w,
            "height": canvas_h,
            "size_bytes": target_path.stat().st_size,
        }

    def build_cover_grid_preview(self, cover_path: Path, target_path: Path) -> dict[str, Any]:
        """Simulate Instagram's 3:4 profile grid crop on Slide 1 so margins can be visually verified."""
        with Image.open(cover_path) as im:
            w, h = im.size
            crop_w = int(h * 0.75)
            margin_x = max(0, (w - crop_w) // 2)
            cropped = im.crop((margin_x, 0, w - margin_x, h)).resize((900, 1200), Image.Resampling.LANCZOS)
            cropped.save(target_path, format="PNG", optimize=True)
        return {
            "path": str(target_path),
            "width": 900,
            "height": 1200,
            "size_bytes": target_path.stat().st_size,
        }

    def render_concept_preview_photo(
        self,
        spec: dict[str, Any],
        desktop_rel: str,
        mobile_rel: str,
        demo_dir: Path,
    ) -> dict[str, Any]:
        """Render Stage A single combined Desktop + Mobile photo (`concept_preview.png`, 2880x2160) for IG DM."""
        proj = spec["project"]
        cd = spec["creative_direction"]
        pal = cd["palette"]
        fonts = cd["fonts"]
        geom = cd["geometry"]
        is_sharp = geom.get("radius") == "0px"
        frame_rad = "0px" if is_sharp else "20px"
        inner_rad = "0px" if is_sharp else "12px"

        preview_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <link href="{fonts['fonts_url']}" rel="stylesheet" />
  <style>
    :root {{
      --bg: {pal['bg']}; --surface: {pal['surface']}; --ink: {pal['ink']};
      --muted: {pal['muted']}; --accent: {pal['accent']}; --border: {pal['border']};
      --font-display: {fonts['font_display']}; --font-body: {fonts['font_body']}; --font-mono: {fonts['font_mono']};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #111; display: flex; justify-content: center; padding: 24px; }}
    .preview-canvas {{
      width: 1440px; height: 1080px; background: var(--bg); color: var(--ink);
      padding: 58px 70px; display: flex; flex-direction: column; justify-content: space-between;
      font-family: var(--font-body); position: relative; overflow: hidden;
    }}
    .top-bar {{ display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 18px; border-bottom: 1px solid var(--border); }}
    .top-title {{ font-family: var(--font-display); font-size: 44px; font-weight: 700; letter-spacing: -0.02em; }}
    .top-title em {{ font-style: italic; color: var(--accent); }}
    .top-meta {{ font-family: var(--font-mono); font-size: 15px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
    .stage {{ position: relative; flex: 1; display: flex; align-items: center; margin: 24px 0; }}
    .browser-frame {{
      width: 1040px; background: var(--surface); border: 1px solid var(--border);
      border-radius: {frame_rad}; padding: 15px;
      box-shadow: {'none' if is_sharp else '0 26px 60px rgba(0,0,0,0.12)'};
    }}
    .browser-top {{ display: flex; align-items: center; gap: 9px; margin-bottom: 11px; }}
    .dot {{ width: 10px; height: 10px; border-radius: {'0' if is_sharp else '50%'}; background: var(--border); }}
    .url-pill {{ margin-left: 10px; font-family: var(--font-mono); font-size: 14px; color: var(--muted); background: var(--bg); padding: 4px 14px; border-radius: {'0px' if is_sharp else '999px'}; border: 1px solid var(--border); }}
    .browser-screen {{ width: 100%; height: 632px; background: var(--bg); border-radius: {inner_rad}; overflow: hidden; border: 1px solid var(--border); }}
    .browser-screen img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
    .phone-frame {{
      position: absolute; right: 0; bottom: 8px; width: 326px; background: #141413;
      border-radius: {'10px' if is_sharp else '38px'}; padding: 12px;
      box-shadow: 0 32px 72px rgba(0,0,0,0.28);
    }}
    .phone-screen {{ width: 100%; height: 652px; background: var(--bg); border-radius: {'2px' if is_sharp else '26px'}; overflow: hidden; }}
    .phone-screen img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
    .bottom-bar {{ display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid var(--border); font-family: var(--font-mono); font-size: 15px; color: var(--muted); }}
    .style-pill {{ background: var(--surface); border: 1px solid var(--border); color: var(--ink); padding: 6px 14px; border-radius: {'0px' if is_sharp else '999px'}; font-size: 13px; }}
  </style>
</head>
<body>
  <section class="preview-canvas" id="preview">
    <div class="top-bar">
      <div class="top-title">Konsep halaman <em>{_esc(proj['brand_name'])}</em></div>
      <div class="top-meta">DESKTOP + MOBILE · {_esc(proj['industry'])}</div>
    </div>
    <div class="stage">
      <div class="browser-frame">
        <div class="browser-top"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="url-pill">{_esc(proj['domain'])}</span></div>
        <div class="browser-screen"><img src="{_esc(desktop_rel)}" alt="Desktop Concept" /></div>
      </div>
      <div class="phone-frame">
        <div class="phone-screen"><img src="{_esc(mobile_rel)}" alt="Mobile Concept" /></div>
      </div>
    </div>
    <div class="bottom-bar">
      <span>website concept · {_esc(proj['handle'])}</span>
      <span class="style-pill">{_esc(cd['primary_style'])}</span>
    </div>
  </section>
</body>
</html>
"""
        html_file = demo_dir / "concept_preview.html"
        html_file.write_text(preview_html, encoding="utf-8")
        target_png = demo_dir / "concept_preview.png"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1520, "height": 1160}, device_scale_factor=2)
            page.goto(html_file.resolve().as_uri(), wait_until="networkidle")
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(180)
            page.locator("#preview").screenshot(path=str(target_png))
            browser.close()

        with Image.open(target_png) as im:
            w, h = im.size
        return {
            "path": str(target_png),
            "width": w,
            "height": h,
            "size_bytes": target_png.stat().st_size,
        }
