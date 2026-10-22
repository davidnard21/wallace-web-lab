"""
The Big Lizard checks the ticket inbox every N seconds (headless).
Any stored XSS waiting there fires against HIS bigadmin session.

Run alongside the webapp:
    python webapps/webapp-a/bot.py
The intended admin→bigadmin path is the password-reset flaw under
/dashboard/admin/admintools; the stored-XSS sink stays live as an
alternative route (exfil via fetch to /collect, readable at /collected).
"""
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5002"
INTERVAL = 15  # seconds between visits

def visit_inbox():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"{BASE}/login")
        page.fill("input[name=username]", "daddylizard")
        page.fill("input[name=password]", "big-lizard-67!")
        page.click("button[type=submit]")
        page.goto(f"{BASE}/dashboard/admin")
        page.wait_for_timeout(2000)  # let stored scripts fire / exfil fetches land
        browser.close()

if __name__ == "__main__":
    print(f"big lizard bot visiting {BASE}/dashboard/admin every {INTERVAL}s")
    while True:
        try:
            visit_inbox()
            print("visited inbox")
        except Exception as e:
            print(f"visit failed: {e}")
        time.sleep(INTERVAL)
