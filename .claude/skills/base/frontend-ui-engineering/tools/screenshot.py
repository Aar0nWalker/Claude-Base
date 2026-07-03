"""Visual QA: log in as admin and screenshot site pages (agent reads the PNGs).

Usage:
  python screenshot.py [outdir] [path ...]        # default paths: /admin /dashboard
  BASE_URL=http://localhost:3000 python screenshot.py out /dashboard

Creds come from repo .env (ADMIN_EMAIL / ADMIN_PASSWORD) and are never printed.
Requires: pip install playwright && python -m playwright install chromium
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[5]
BASE = os.environ.get("BASE_URL", "https://{{DOMAIN}}")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
PAGES = sys.argv[2:] or ["/admin", "/dashboard"]

env = {}
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
email, password = env.get("ADMIN_EMAIL"), env.get("ADMIN_PASSWORD")
assert email and password, "no ADMIN_EMAIL/ADMIN_PASSWORD in .env"

OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{BASE}/login", wait_until="networkidle", timeout=60000)
    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda u: "/login" not in u, timeout=30000)
    for path in PAGES:
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=60000)
        name = path.strip("/").replace("/", "_") or "home"
        page.screenshot(path=str(OUT / f"shot_{name}.png"))
        print(f"{path} -> {page.url} -> shot_{name}.png")
    b.close()
