"""
MIT 8339 - Stage 4: capture dashboard screenshots (headless Chromium via Playwright)
Output: figures/dash_p1_overview.png, figures/dash_p2_retention.png, figures/dash_p1_filtered.png
Run   : python src/04_capture_screenshots.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
url = (ROOT / "dashboard" / "MIT8339_Retention_Dashboard.html").as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(ROOT / "figures" / "dash_p1_overview.png"), full_page=True)
    pg.click("nav button[data-p=p2]"); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(ROOT / "figures" / "dash_p2_retention.png"), full_page=True)
    # Demonstrate slicers: Female, income < $40K, Blue card
    pg.click("nav button[data-p=p1]")
    pg.select_option("#f_Gender", "0"); pg.select_option("#f_Income_Category", "0"); pg.select_option("#f_Card_Category", "0")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(ROOT / "figures" / "dash_p1_filtered.png"), full_page=True)
    b.close()
print("Saved dashboard screenshots to figures/")
