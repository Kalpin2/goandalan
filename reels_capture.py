"""Reusable Playwright mobile capture module for the @goandalan Reels engine.

Opens a generated portfolio/concept website (file) or a verified public URL, waits for fonts and
lazy-loaded images, then captures: tall mobile page (for eased scrolling), hero viewport, a real
CTA highlight pair, an optional real tab-switch pair, section offsets and desktop hero.
Nothing is fabricated: interactions are only captured when the real DOM exposes them.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


@dataclass
class CaptureConfig:
    viewport_w: int = 390
    viewport_h: int = 844
    dpr: float = 2.0                 # 2 (default) or 3 for sharper capture
    settle_ms: int = 220             # extra wait after fonts/images settle
    max_dpr_pixels: int = 15000      # Chromium full-page screenshot limit guard
    desktop_w: int = 1280
    desktop_h: int = 800
    hide_selectors: tuple[str, ...] = (".goandalan-pill",)
    capture_cta: bool = True
    capture_tabs: bool = True
    allow_remote_url: bool = False   # only verified public http(s) URLs when True
    # Timing hints consumed by the composer (kept here so one config object drives capture + scroll):
    scroll_pause_beats: int = 3
    scroll_hold_frac: float = 0.2
    duration_s: float = 10.0
    extra: dict[str, Any] = field(default_factory=dict)


_SETTLE_JS = """
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; });
  const h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
  for (let y = 0; y < h; y += Math.round(innerHeight * 0.7)) { window.scrollTo(0, y); await sleep(80); }
  window.scrollTo(0, 0);
  await Promise.all(Array.from(document.images).map(i => i.complete ? 0 :
    new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 3000); })));
  await document.fonts.ready;
  await sleep(120);
  return { height: h, images: document.images.length, broken: Array.from(document.images).filter(i => !i.naturalWidth).length };
}
"""

_SECTIONS_JS = """
() => {
  const tops = [];
  document.querySelectorAll('header, section, footer, main > *, body > div, body > main > div').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.height > 120) tops.push(Math.round(r.top + window.scrollY));
  });
  return Array.from(new Set(tops)).sort((a, b) => a - b);
}
"""

_FACTS_JS = """
() => {
  const txt = sel => (document.querySelector(sel)?.innerText || '').trim();
  const items = Array.from(document.querySelectorAll('.ledger-row, .menu-card, .sig-item, .mini-offer')).map(el => ({
    name: (el.querySelector('h3, strong')?.innerText || '').trim(),
  })).filter(x => x.name);
  return { headline: txt('h1'), cta_label: txt('.btn-primary') || 'Lihat Layanan', items,
           is_full_demo: Boolean(document.querySelector('section#layanan')) };
}
"""

_CTA_JS = """
() => {
  const cands = Array.from(document.querySelectorAll(
    'a[href*="wa.me"], a[href*="whatsapp"], .btn-primary, a.btn, button.btn, a[href^="tel:"], a[href*="booking"], a[href*="reserv"]'));
  for (const el of cands) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (r.width > 40 && r.height > 20 && cs.visibility !== 'hidden' && cs.display !== 'none') {
      el.setAttribute('data-gaa-cta', '1');
      const href = (el.getAttribute('href') || '').toLowerCase();
      const kind = href.includes('wa.me') || href.includes('whatsapp') ? 'whatsapp' : href.startsWith('tel:') ? 'tel' : 'button';
      return { label: (el.innerText || '').trim().slice(0, 60), kind: kind };
    }
  }
  return null;
}
"""

_TABS_JS = """
() => {
  const sel = '[role="tab"], .tab, .tab-btn, [data-tab], .tabs button, .segmented button';
  const vis = Array.from(document.querySelectorAll(sel)).filter(el => {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 24 && r.height > 18 && cs.visibility !== 'hidden' && cs.display !== 'none';
  });
  if (vis.length < 2) return null;
  const parent = vis[0].parentElement;
  const group = vis.filter(el => el.parentElement === parent);
  if (group.length < 2) return null;
  group.forEach((el, i) => el.setAttribute('data-gaa-tab', String(i)));
  return { count: group.length, label_a: (group[0].innerText || '').trim().slice(0, 40), label_b: (group[1].innerText || '').trim().slice(0, 40) };
}
"""

_BBOX_JS = """
(sel) => {
  const el = document.querySelector(sel); if (!el) return null;
  el.scrollIntoView({ block: 'center', inline: 'nearest' });
  const r = el.getBoundingClientRect();
  return { x: r.left, y: r.top, w: r.width, h: r.height };
}
"""


def _is_public_http_url(url: str) -> bool:
    try:
        u = urlparse(url)
        if u.scheme not in {"http", "https"} or not u.hostname:
            return False
        for info in socket.getaddrinfo(u.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def _prepare(page, cfg: CaptureConfig) -> dict[str, Any]:
    try:
        page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:
        pass
    report = page.evaluate(_SETTLE_JS)
    css = ",".join(cfg.hide_selectors)
    if css:
        page.add_style_tag(content=f"{css} {{ display: none !important; }}")
    page.wait_for_timeout(cfg.settle_ms)
    return report or {}


def capture_site(source: Path | str, out_dir: Path, cfg: CaptureConfig | None = None) -> dict[str, Any]:
    """Capture all raw website material needed by the Reels composer. Returns a plain dict."""
    cfg = cfg or CaptureConfig()
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(source, str) and source.startswith(("http://", "https://")):
        if not (cfg.allow_remote_url and _is_public_http_url(source)):
            raise ValueError("URL remote ditolak: hanya URL publik http(s) terverifikasi dengan allow_remote_url=True.")
        uri, source_kind = source, "url"
    else:
        uri, source_kind = Path(source).resolve().as_uri(), "file"

    res: dict[str, Any] = {
        "source_kind": source_kind,
        "desktop_png": out_dir / "reels_desktop.png",
        "mobile_tall_png": out_dir / "reels_mobile_tall.png",
        "mobile_hero_png": out_dir / "reels_mobile_hero.png",
        "viewport": [cfg.viewport_w, cfg.viewport_h],
        "dpr": cfg.dpr,
        "cta": None,
        "tabs": None,
        "section_tops": [],
        "image_report": {},
        "facts": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Desktop hero (also source of verified DOM facts)
        d_ctx = browser.new_context(viewport={"width": cfg.desktop_w, "height": cfg.desktop_h}, device_scale_factor=2)
        d_page = d_ctx.new_page()
        d_page.goto(uri, wait_until="domcontentloaded")
        _prepare(d_page, cfg)
        d_page.screenshot(path=str(res["desktop_png"]), full_page=False)
        res["facts"] = d_page.evaluate(_FACTS_JS)
        d_ctx.close()

        # --- Mobile (390x844 @ DPR)
        m_ctx = browser.new_context(
            viewport={"width": cfg.viewport_w, "height": cfg.viewport_h},
            device_scale_factor=cfg.dpr,
            is_mobile=True,
            has_touch=True,
        )
        m_page = m_ctx.new_page()
        m_page.goto(uri, wait_until="domcontentloaded")
        res["image_report"] = _prepare(m_page, cfg)

        page_h = int(m_page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"))
        res["page_height_css"] = page_h
        res["section_tops"] = m_page.evaluate(_SECTIONS_JS)

        m_page.evaluate("() => window.scrollTo(0, 0)")
        m_page.wait_for_timeout(120)
        m_page.screenshot(path=str(res["mobile_hero_png"]), full_page=False)
        scale_mode = "device" if page_h * cfg.dpr <= cfg.max_dpr_pixels else "css"
        m_page.screenshot(path=str(res["mobile_tall_png"]), full_page=True, scale=scale_mode)
        res["tall_scale"] = scale_mode

        # --- Real CTA highlight pair (plain + highlighted) ---
        if cfg.capture_cta:
            try:
                cta = m_page.evaluate(_CTA_JS)
                if cta:
                    bbox = m_page.evaluate(_BBOX_JS, "[data-gaa-cta]")
                    m_page.wait_for_timeout(220)
                    plain = out_dir / "reels_cta_plain.png"
                    hl = out_dir / "reels_cta_highlight.png"
                    m_page.screenshot(path=str(plain), full_page=False)
                    hl_tag = m_page.add_style_tag(content=(
                        "[data-gaa-cta]{outline:5px solid #FFC400 !important;outline-offset:5px !important;"
                        "box-shadow:0 0 0 16px rgba(255,196,0,.30) !important;}"
                    ))
                    m_page.wait_for_timeout(160)
                    m_page.screenshot(path=str(hl), full_page=False)
                    hl_tag.evaluate("e => e.remove()")  # keep later captures pristine
                    res["cta"] = {**cta, "bbox_vp": bbox, "plain": plain, "highlight": hl}
            except Exception as exc:  # keep pipeline resilient
                res["cta_error"] = str(exc)[:160]

        # --- Real tab switch (only if the DOM exposes >=2 tabs) ---
        if cfg.capture_tabs:
            try:
                m_page.evaluate("() => window.scrollTo(0, 0)")
                tabs = m_page.evaluate(_TABS_JS)
                if tabs:
                    bbox = m_page.evaluate(_BBOX_JS, '[data-gaa-tab="1"]')
                    m_page.wait_for_timeout(200)
                    a_png, b_png = out_dir / "reels_tab_a.png", out_dir / "reels_tab_b.png"
                    m_page.screenshot(path=str(a_png), full_page=False)
                    m_page.locator('[data-gaa-tab="1"]').first.click(timeout=3000)
                    m_page.wait_for_timeout(420)
                    m_page.screenshot(path=str(b_png), full_page=False)
                    res["tabs"] = {**tabs, "bbox_vp": bbox, "a": a_png, "b": b_png}
            except Exception as exc:
                res["tabs_error"] = str(exc)[:160]

        m_ctx.close()
        browser.close()

    return res
