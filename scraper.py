"""Resilient Google Maps lead scraper CLI & library for @goandalan.

Usage:
    python scraper.py --query "coffee roastery jakarta selatan" --limit 10
"""

from __future__ import annotations

import argparse
import re
import time
import urllib.parse
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

import database as db
from config import settings


def _infer_city_from_query(query: str, fallback: str = "") -> str:
    if fallback:
        return fallback
    known_cities = [
        "Jakarta Selatan", "Jakarta Barat", "Jakarta Pusat", "Jakarta Timur", "Jakarta Utara",
        "Jakarta", "Bandung", "Surabaya", "Yogyakarta", "Jogja", "Bali", "Canggu", "Ubud",
        "Seminyak", "Denpasar", "Tangerang", "BSD", "Bekasi", "Depok", "Bogor", "Semarang",
        "Malang", "Medan", "Makassar", "Solo",
    ]
    q_lower = query.lower()
    for city in known_cities:
        if city.lower() in q_lower:
            return city
    return settings.DEFAULT_CITY


def _dismiss_consent_if_present(page: Page) -> None:
    selectors = [
        'button:has-text("Terima semua")',
        'button:has-text("Accept all")',
        'button:has-text("Setuju")',
        'button[aria-label*="Accept"]',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1200):
                btn.click(timeout=2000)
                page.wait_for_timeout(800)
                return
        except Exception:
            continue


def _collect_result_links(page: Page, target_count: int) -> list[str]:
    """Scroll Google Maps result feed until enough unique place URLs are collected."""
    feed = page.locator('div[role="feed"]').first
    try:
        feed.wait_for(state="visible", timeout=12000)
    except PlaywrightTimeoutError:
        pass

    seen: set[str] = set()
    links: list[str] = []
    stale_rounds = 0
    max_rounds = max(8, target_count * 2)

    for _ in range(max_rounds):
        anchors = page.locator('a[href*="/maps/place/"]')
        count = anchors.count()
        added_this_round = 0

        for i in range(count):
            try:
                href = anchors.nth(i).get_attribute("href")
            except Exception:
                continue
            if not href:
                continue
            base_href = href.split("?")[0]
            if base_href not in seen:
                seen.add(base_href)
                links.append(href)
                added_this_round += 1
                if len(links) >= target_count:
                    return links

        if added_this_round == 0:
            stale_rounds += 1
            if stale_rounds >= 3:
                break
        else:
            stale_rounds = 0

        try:
            if feed.count() > 0:
                feed.evaluate("el => el.scrollBy(0, el.clientHeight * 0.9)")
            else:
                page.mouse.wheel(0, 1200)
        except Exception:
            page.mouse.wheel(0, 1200)
        page.wait_for_timeout(900)

    return links


def _safe_text(page: Page, selectors: list[str], timeout: int = 1200) -> str:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = (loc.inner_text(timeout=timeout) or "").strip()
                if txt:
                    return txt
        except Exception:
            continue
    return ""


def _safe_attr(page: Page, selectors: list[str], attr: str, timeout: int = 1200) -> str:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                val = (loc.get_attribute(attr, timeout=timeout) or "").strip()
                if val:
                    return val
        except Exception:
            continue
    return ""


def _extract_place_details(page: Page, place_url: str, fallback_city: str, query: str) -> dict[str, Any] | None:
    try:
        page.goto(place_url, wait_until="domcontentloaded", timeout=settings.SCRAPER_TIMEOUT_MS)
        page.locator("h1.DUwDvf, h1").first.wait_for(state="visible", timeout=8000)
        page.wait_for_timeout(600)
    except Exception:
        return None

    name = _safe_text(page, ["h1.DUwDvf", "h1[class*='fontHeadline']", "h1"])
    if not name or name.lower() in {"hasil", "results", "google maps"}:
        return None

    category = _safe_text(
        page,
        [
            'button[jsaction*="category"]',
            'button.DkEaL',
            'span.DkEaL',
        ],
    ) or "Bisnis Lokal"

    address = _safe_text(
        page,
        [
            'button[data-item-id="address"] div.fontBodyMedium',
            'button[data-item-id="address"]',
            '[aria-label^="Alamat:"]',
            '[aria-label^="Address:"]',
        ],
    )
    address = re.sub(r"^(Alamat|Address)\s*:\s*", "", address, flags=re.IGNORECASE).strip()

    phone_raw = _safe_text(
        page,
        [
            'button[data-item-id^="phone:tel:"] div.fontBodyMedium',
            'button[data-item-id^="phone:"] div.fontBodyMedium',
            'button[data-item-id^="phone:"]',
            '[aria-label^="Telepon:"]',
            '[aria-label^="Phone:"]',
        ],
    )
    if not phone_raw:
        tel_id = _safe_attr(page, ['button[data-item-id^="phone:tel:"]'], "data-item-id")
        if tel_id.startswith("phone:tel:"):
            phone_raw = tel_id.replace("phone:tel:", "").strip()
    phone_raw = re.sub(r"^(Telepon|Phone)\s*:\s*", "", phone_raw, flags=re.IGNORECASE).strip()
    phone_wa = db.normalize_indo_phone(phone_raw)

    website_url = _safe_attr(
        page,
        [
            'a[data-item-id="authority"]',
            'a[aria-label^="Situs Web:"]',
            'a[aria-label^="Website:"]',
        ],
        "href",
    )
    if website_url and "google.com/url?" in website_url:
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(website_url).query)
        website_url = (parsed.get("q") or parsed.get("url") or [website_url])[0]

    # Parse rating & review count
    rating = None
    review_count = 0
    rating_text = _safe_text(page, ['div.F7nice span[aria-hidden="true"]', 'span.ceNzKf'])
    if rating_text:
        m = re.search(r"(\d+[.,]\d+)", rating_text)
        if m:
            try:
                rating = float(m.group(1).replace(",", "."))
            except ValueError:
                rating = None

    review_aria = _safe_attr(
        page,
        [
            'div.F7nice span[aria-label*="ulasan"]',
            'div.F7nice span[aria-label*="review"]',
            'button[aria-label*="ulasan"]',
            'button[aria-label*="review"]',
        ],
        "aria-label",
    )
    if review_aria:
        digits = re.sub(r"\D+", "", review_aria)
        if digits:
            review_count = int(digits)

    has_website, priority_score, default_flaw = db.compute_priority_score(
        website_url=website_url,
        rating=rating,
        review_count=review_count,
    )

    return {
        "business_name": name,
        "category": category,
        "address": address,
        "city": fallback_city,
        "phone_raw": phone_raw,
        "phone_wa": phone_wa,
        "website_url": website_url,
        "rating": rating,
        "review_count": review_count,
        "has_website": has_website,
        "priority_score": priority_score,
        "ux_flaw": default_flaw,
        "source_query": query,
        "status": "NEW",
    }


def scrape_google_maps(
    query: str,
    limit: int = 10,
    city: str = "",
    headless: bool | None = None,
    prioritize_no_web: bool = True,
) -> dict[str, Any]:
    """Scrape Google Maps search results and upsert prioritized leads into SQLite."""
    db.init_db()
    query = query.strip()
    if not query:
        raise ValueError("Query pencarian tidak boleh kosong.")

    limit = max(1, min(int(limit), 50))
    use_headless = settings.SCRAPER_HEADLESS if headless is None else headless
    inferred_city = _infer_city_from_query(query, city)

    # Oversample slightly when prioritizing businesses without websites
    fetch_target = min(limit * 2, 40) if prioritize_no_web else limit
    encoded_q = urllib.parse.quote_plus(query)
    search_url = f"https://www.google.com/maps/search/{encoded_q}?hl=id"

    candidates: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    errors: list[str] = []

    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=use_headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="id-ID",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(settings.SCRAPER_TIMEOUT_MS)

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=settings.SCRAPER_TIMEOUT_MS)
            _dismiss_consent_if_present(page)
            page.wait_for_timeout(1500)

            place_links = _collect_result_links(page, fetch_target)
            if not place_links and "/maps/place/" in page.url:
                place_links = [page.url]

            for link in place_links:
                item = _extract_place_details(page, link, inferred_city, query)
                if not item:
                    continue
                norm_key = item["business_name"].strip().lower()
                if norm_key in seen_names:
                    continue
                seen_names.add(norm_key)
                candidates.append(item)
                if not prioritize_no_web and len(candidates) >= limit:
                    break
        except Exception as exc:
            errors.append(str(exc))
        finally:
            context.close()
            browser.close()

    if prioritize_no_web:
        candidates.sort(
            key=lambda x: (
                0 if not x["has_website"] else 1,
                -int(x["priority_score"]),
                -(x.get("review_count") or 0),
            )
        )

    selected = candidates[:limit]
    inserted = 0
    updated = 0
    saved_leads: list[dict[str, Any]] = []

    for item in selected:
        lead, created = db.upsert_lead(item)
        if created:
            inserted += 1
        else:
            updated += 1
        saved_leads.append(lead)

    return {
        "query": query,
        "city": inferred_city,
        "scraped_candidates": len(candidates),
        "saved_count": len(saved_leads),
        "inserted": inserted,
        "updated": updated,
        "elapsed_seconds": round(time.time() - started, 2),
        "errors": errors,
        "leads": saved_leads,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="@goandalan Google Maps Lead Scraper")
    parser.add_argument("--query", required=True, help='Kata kunci pencarian, mis. "coffee roastery jakarta selatan"')
    parser.add_argument("--limit", type=int, default=10, help="Jumlah maksimal prospek yang disimpan (default: 10)")
    parser.add_argument("--city", default="", help="Kota default jika tidak terdeteksi dari query")
    parser.add_argument("--headed", action="store_true", help="Tampilkan browser Chromium saat scraping")
    parser.add_argument("--no-priority-sort", action="store_true", help="Jangan prioritaskan bisnis tanpa website")
    args = parser.parse_args()

    result = scrape_google_maps(
        query=args.query,
        limit=args.limit,
        city=args.city,
        headless=not args.headed,
        prioritize_no_web=not args.no_priority_sort,
    )
    print(
        f"[OK] Scrape selesai ({result['elapsed_seconds']}s) | "
        f"kandidat={result['scraped_candidates']} | baru={result['inserted']} | update={result['updated']}"
    )
    for idx, lead in enumerate(result["leads"], start=1):
        web_flag = "TANPA WEB" if not lead["has_website"] else lead["website_url"]
        print(
            f"  {idx:02d}. {lead['business_name']} ({lead['category']}) | "
            f"WA: {lead['phone_wa'] or '-'} | Score: {lead['priority_score']} | {web_flag}"
        )
    if result["errors"]:
        print("[WARN] Errors:", "; ".join(result["errors"]))


if __name__ == "__main__":
    main()
