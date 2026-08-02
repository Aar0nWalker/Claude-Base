"""Visual QA: screenshot pages of the running app so the agent can actually look at them.

Reading the markup does not tell you whether the layout is broken. This does.

  python screenshot.py                              # BASE_URL + PAGES from env
  python screenshot.py out /dashboard /settings     # outdir + explicit paths
  BASE_URL=http://localhost:3000 python screenshot.py

Optional login, for pages behind a session — set all three, or none:
  LOGIN_URL=/login LOGIN_USER=... LOGIN_PASSWORD=...
  LOGIN_USER_SELECTOR / LOGIN_PASSWORD_SELECTOR / LOGIN_SUBMIT_SELECTOR override the defaults.

Credentials come from the environment and are never printed.
Requires: pip install playwright && python -m playwright install chromium
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:3000").rstrip("/")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PAGES = sys.argv[2:] or [p for p in os.environ.get("PAGES", "/").split(",") if p]

LOGIN_URL = os.environ.get("LOGIN_URL")
LOGIN_USER = os.environ.get("LOGIN_USER")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD")
SEL_USER = os.environ.get("LOGIN_USER_SELECTOR", 'input[type="email"]')
SEL_PASSWORD = os.environ.get("LOGIN_PASSWORD_SELECTOR", 'input[type="password"]')
SEL_SUBMIT = os.environ.get("LOGIN_SUBMIT_SELECTOR", 'button[type="submit"]')

OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    if LOGIN_URL and LOGIN_USER and LOGIN_PASSWORD:
        page.goto(f"{BASE}{LOGIN_URL}", wait_until="networkidle", timeout=60000)
        page.fill(SEL_USER, LOGIN_USER)
        page.fill(SEL_PASSWORD, LOGIN_PASSWORD)
        page.click(SEL_SUBMIT)
        page.wait_for_load_state("networkidle")

    for path in PAGES:
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=60000)
        name = (path.strip("/").replace("/", "_") or "index") + ".png"
        page.screenshot(path=str(OUT / name), full_page=True)
        print(f"{path} -> {page.url} -> {name}")

    browser.close()
