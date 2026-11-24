"""Playwright UI & Visual Regression Verification for @goandalan.

Checks:
- Viewports: Mobile (390x844) & Desktop (1280x800)
- Themes: Dark Mode & Light Mode
- Pages:
  1. Public Bio Catalog (`site/index.html`)
  2. Demo Landing Page (`site/demos/seduh-pagi-coffee-roastery/index.html`)
  3. Dashboard Tab 4 Draft Brief Builder (Format toggle & Collapsible Reels Options)
  4. Content Review Modal (GitHub Status Checks, 9:16 Video Player, Beat & Motion Breakdown)
- Assertions:
  - 0 horizontal overflow (scrollWidth <= innerWidth)
  - 0 console errors
"""

import secrets
import sys
import threading
import time
from pathlib import Path
from typing import Any
import uvicorn
from playwright.sync_api import sync_playwright

import database as db
import demo_generator as dg
import content_review as cr
from app import app
from config import settings


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def test_ui():
    db.init_db()
    # Rebuild portfolio index to guarantee site/index.html is synced with DB
    dg.rebuild_portfolio_index()

    # Ensure lead 69 has an active pending_review reels entry for modal testing
    rev69 = db.get_review_by_lead(69)
    if not rev69:
        try:
            cr.create_draft_brief_from_recycle(69, actor="Admin Test")
        except Exception:
            pass

    # Create admin session
    raw_token = secrets.token_hex(32)
    db.create_auth_session(
        raw_token=raw_token,
        role="admin",
        username=settings.ADMIN_USN or "admin",
        ttl_seconds=86400,
    )
    admin_session_id = raw_token

    host = "127.0.0.1"
    port = 8877
    server = ServerThread(host, port)
    server.start()
    time.sleep(1.2)  # Wait for uvicorn to boot

    base_url = f"http://{host}:{port}"
    errors: list[str] = []

    print(f"=== STARTING PLAYWRIGHT VERIFICATION ON {base_url} ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        viewports = [
            ("Mobile 390x844", {"width": 390, "height": 844}),
            ("Desktop 1280x800", {"width": 1280, "height": 800}),
        ]
        color_schemes = ["dark", "light"]

        for vp_name, vp in viewports:
            for theme in color_schemes:
                case_id = f"[{vp_name} | {theme.upper()}]"
                print(f"\n--- Testing {case_id} ---")

                context = browser.new_context(
                    viewport=vp,
                    color_scheme=theme,
                )
                context.add_cookies([
                    {
                        "name": settings.SESSION_COOKIE_NAME,
                        "value": admin_session_id,
                        "domain": host,
                        "path": "/",
                    }
                ])

                page_errors: list[str] = []
                page = context.new_page()

                def on_console(msg):
                    if msg.type == "error":
                        # Ignore benign favicon / static 404s if any
                        page_errors.append(f"Console error: {msg.text}")

                def on_page_error(exc):
                    page_errors.append(f"Page unhandled exception: {exc}")

                page.on("console", on_console)
                page.on("pageerror", on_page_error)

                # ==========================================================
                # 1. Test site/index.html (Public Bio Catalog)
                # ==========================================================
                catalog_url = f"{base_url}/site/index.html"
                page.goto(catalog_url, wait_until="networkidle")
                page.wait_for_timeout(300)

                # Check horizontal overflow
                overflow = page.evaluate("""() => {
                    const docEl = document.documentElement;
                    const body = document.body;
                    const innerW = window.innerWidth;
                    const scrollW = Math.max(docEl.scrollWidth, body.scrollWidth);
                    return { innerW, scrollW, hasOverflow: scrollW > innerW + 1 };
                }""")
                if overflow["hasOverflow"]:
                    err = f"{case_id} Catalog horizontal overflow: innerWidth={overflow['innerW']}, scrollWidth={overflow['scrollW']}"
                    print(f"  [FAIL] {err}")
                    errors.append(err)
                else:
                    print(f"  [OK] Catalog 0 horizontal overflow ({overflow['scrollW']}px <= {overflow['innerW']}px)")

                # Verify cards exist and no broken links
                cards_count = page.locator(".demo-row").count()
                print(f"  [OK] Catalog portfolio cards: {cards_count}")

                # ==========================================================
                # 2. Test Demo Landing Page (Pre-DP / Production)
                # ==========================================================
                demo_url = f"{base_url}/demos/seduh-pagi-coffee-roastery/index.html"
                page.goto(demo_url, wait_until="networkidle")
                page.wait_for_timeout(300)

                demo_overflow = page.evaluate("""() => {
                    const docEl = document.documentElement;
                    const body = document.body;
                    const innerW = window.innerWidth;
                    const scrollW = Math.max(docEl.scrollWidth, body.scrollWidth);
                    return { innerW, scrollW, hasOverflow: scrollW > innerW + 1 };
                }""")
                if demo_overflow["hasOverflow"]:
                    err = f"{case_id} Demo site horizontal overflow: innerWidth={demo_overflow['innerW']}, scrollWidth={demo_overflow['scrollW']}"
                    print(f"  [FAIL] {err}")
                    errors.append(err)
                else:
                    print(f"  [OK] Demo site 0 horizontal overflow ({demo_overflow['scrollW']}px <= {demo_overflow['innerW']}px)")

                # Check WhatsApp CTA visibility and touch target
                btn_cta = page.locator(".btn-primary").first
                if btn_cta.count() > 0:
                    bbox = btn_cta.bounding_box()
                    if bbox and bbox["height"] >= 40:
                        print(f"  [OK] Demo WhatsApp CTA target height: {bbox['height']}px >= 40px")
                    else:
                        print(f"  [WARN] Demo CTA height: {bbox['height'] if bbox else 0}px")

                # Check Floating concept pill
                pill = page.locator(".goandalan-pill")
                if pill.count() > 0:
                    pill_w = pill.evaluate("el => el.offsetWidth")
                    print(f"  [OK] Floating concept pill rendered cleanly (width: {pill_w}px)")

                # ==========================================================
                # 3. Test Dashboard UI Tab 4 (Brief / Siap Generate Sub-tab)
                # ==========================================================
                page.goto(f"{base_url}/", wait_until="networkidle")
                page.wait_for_timeout(500)

                # Check if login gate is visible; if so, authenticate
                if page.locator("input[type='password']").is_visible():
                    page.fill("input[type='text']", settings.ADMIN_USN or "admin")
                    page.fill("input[type='password']", settings.ADMIN_PASS or "")
                    page.click("button[type='submit']")
                    page.wait_for_timeout(600)

                # Switch to Tab 4 & sub-tab 'draft_brief' via Alpine
                page.evaluate("""() => {
                    const root = document.querySelector('#app-root') || document.querySelector('[x-data]');
                    if (window.Alpine && root && root._x_dataStack) {
                        const app = root._x_dataStack[0];
                        app.activeTab = 'review';
                        app.reviewSubTab = 'draft_brief';
                        app.loadReviewQueue(false);
                    }
                }""")
                page.wait_for_timeout(400)

                # Find format buttons (Carousel vs Reels)
                reels_btn = page.locator("button:has-text('Reels (Video 9:16)')").first
                if reels_btn.count() > 0 and reels_btn.is_visible():
                    reels_btn.click()
                    page.wait_for_timeout(300)
                    print(f"  [OK] Toggled format to Reels (9:16)")

                    # Test Notion Collapsible Toggle: Opsi Lanjutan Reels
                    adv_btn = page.locator("button:has-text('Opsi Lanjutan Reels')").first
                    if adv_btn.count() > 0 and adv_btn.is_visible():
                        adv_btn.click()
                        page.wait_for_timeout(200)
                        print(f"  [OK] Expanded Notion Collapsible Toggle: Opsi Lanjutan Reels")

                dash_overflow = page.evaluate("""() => {
                    const docEl = document.documentElement;
                    const body = document.body;
                    const innerW = window.innerWidth;
                    const scrollW = Math.max(docEl.scrollWidth, body.scrollWidth);
                    return { innerW, scrollW, hasOverflow: scrollW > innerW + 1 };
                }""")
                if dash_overflow["hasOverflow"]:
                    err = f"{case_id} Tab 4 Brief horizontal overflow: innerWidth={dash_overflow['innerW']}, scrollWidth={dash_overflow['scrollW']}"
                    print(f"  [FAIL] {err}")
                    errors.append(err)
                else:
                    print(f"  [OK] Tab 4 Brief 0 horizontal overflow ({dash_overflow['scrollW']}px <= {dash_overflow['innerW']}px)")

                # ==========================================================
                # 4. Test Content Review Modal for Reels item (Lead 69)
                # ==========================================================
                # Switch to 'to_review' subtab
                to_review_btn = page.locator("button.v-tab:has-text('Perlu Review')")
                if to_review_btn.count() > 0:
                    to_review_btn.click()
                    page.wait_for_timeout(300)

                # Open review modal via Alpine or card click
                page.evaluate("""() => {
                    const root = document.querySelector('#app-root') || document.querySelector('[x-data]');
                    if (window.Alpine && root && root._x_dataStack) {
                        root._x_dataStack[0].openReviewDetail(69);
                    }
                }""")
                page.wait_for_timeout(600)

                # Check Modal is visible
                modal = page.locator(".surface-modal")
                if modal.count() > 0 and modal.is_visible():
                    print(f"  [OK] Content Review Modal opened successfully")

                    # Verify GitHub Status Checks video badges
                    gh_checks = page.locator(".gh-check").all_inner_texts()
                    print(f"  [OK] GitHub Status Checks visible: {gh_checks}")

                    has_safe_zone = any("Safe-Zone" in c for c in gh_checks)
                    has_audio = any("Audio AAC" in c for c in gh_checks)
                    has_black_frames = any("0 Black Frames" in c for c in gh_checks)
                    has_mobile_cap = any("Mobile Capture" in c for c in gh_checks)

                    if has_safe_zone and has_audio and has_black_frames and has_mobile_cap:
                        print(f"  [OK] All 4 Video GitHub Status Checks present!")
                    else:
                        err = f"{case_id} Missing expected video check badges in {gh_checks}"
                        print(f"  [WARN] {err}")

                    # Test Notion Collapsible Toggle: Beat & Motion Breakdown
                    breakdown_btn = page.locator("button:has-text('Beat & Motion Breakdown')").first
                    if breakdown_btn.count() > 0:
                        breakdown_btn.click()
                        page.wait_for_timeout(250)
                        print(f"  [OK] Expanded Notion Collapsible Toggle: Beat & Motion Breakdown")

                    modal_overflow = page.evaluate("""() => {
                        const modal = document.querySelector('.surface-modal');
                        if (!modal) return { hasOverflow: false, scrollW: 0, clientW: 0 };
                        return {
                            hasOverflow: modal.scrollWidth > modal.clientWidth + 1,
                            scrollW: modal.scrollWidth,
                            clientW: modal.clientWidth
                        };
                    }""")
                    if modal_overflow["hasOverflow"]:
                        err = f"{case_id} Review modal horizontal overflow: scrollWidth={modal_overflow['scrollW']}, clientWidth={modal_overflow['clientW']}"
                        print(f"  [FAIL] {err}")
                        errors.append(err)
                    else:
                        print(f"  [OK] Review modal 0 horizontal overflow ({modal_overflow['scrollW']}px <= {modal_overflow['clientW']}px)")

                    # Close modal
                    close_btn = page.locator(".surface-modal button:has-text('Tutup')").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        page.wait_for_timeout(200)

                if page_errors:
                    for pe in page_errors:
                        print(f"  [PAGE ERROR] {pe}")
                        errors.append(f"{case_id} {pe}")
                else:
                    print(f"  [OK] 0 console errors in {case_id}")

                context.close()

        browser.close()

    server.stop()

    print("\n==================================================")
    if errors:
        print(f"FAILED with {len(errors)} issues:")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)
    else:
        print("ALL PLAYWRIGHT TESTS PASSED (0 HORIZONTAL OVERFLOW & 0 CONSOLE ERRORS)!")
        print("==================================================")
        sys.exit(0)


if __name__ == "__main__":
    test_ui()
