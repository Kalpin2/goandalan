import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def render(html_path: str, out_dir: str):
    html_file = Path(html_path).resolve()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1500}, device_scale_factor=2)
        page.goto(html_file.as_uri(), wait_until="networkidle")
        page.evaluate("() => document.fonts.ready")

        slides = page.locator(".slide")
        count = slides.count()
        for i in range(count):
            slide = slides.nth(i)
            name = slide.get_attribute("data-name") or f"slide_{i+1:02d}"
            target = out / f"{name}.png"
            slide.screenshot(path=str(target))
            print(f"[OK] Rendered {target}")

        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render_slides.py <input.html> <output_dir>")
        sys.exit(1)
    render(sys.argv[1], sys.argv[2])
