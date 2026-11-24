import secrets
import time
import threading
import uvicorn
from playwright.sync_api import sync_playwright
import database as db
from app import app
from config import settings

db.init_db()
raw_token = secrets.token_hex(32)
db.create_auth_session(raw_token, 'admin', 'admin', 86400)
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8898, log_level='error'))
t = threading.Thread(target=server.run, daemon=True)
t.start()
time.sleep(1)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    c = b.new_context(viewport={'width': 390, 'height': 844})
    c.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': raw_token, 'domain': '127.0.0.1', 'path': '/'}])
    page = c.new_page()
    page.goto('http://127.0.0.1:8898/', wait_until='networkidle')
    page.evaluate('''() => {
        const root = document.querySelector('#app-root') || document.querySelector('[x-data]');
        if (root && root._x_dataStack) {
            root._x_dataStack[0].activeTab = 'review';
            root._x_dataStack[0].reviewSubTab = 'draft_brief';
            root._x_dataStack[0].loadReviewQueue(false);
        }
    }''')
    page.wait_for_timeout(500)
    page.locator("button:has-text('Reels (Video 9:16)')").first.click()
    page.locator("button:has-text('Opsi Lanjutan Reels')").first.click()
    page.wait_for_timeout(400)
    overs = page.evaluate('''() => {
        const out = [];
        document.querySelectorAll('*').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.right > 391 || el.scrollWidth > 391) {
                out.push({
                    tag: el.tagName,
                    class: String(el.className).slice(0, 50),
                    w: Math.round(r.width),
                    right: Math.round(r.right),
                    scrollW: el.scrollWidth,
                    text: (el.innerText || '').slice(0, 30)
                });
            }
        });
        return out;
    }''')
    print('Total overflow elements:', len(overs))
    for o in overs:
        if o['right'] > 391:
            print(o)
    b.close()
server.should_exit = True
