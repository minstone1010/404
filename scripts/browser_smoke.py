import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8001")
    page.wait_for_selector(".voc-item", timeout=120000)
    assert page.locator(".voc-item").count() == 512
    assert page.locator("#analyze").count() == 1
    rows = page.request.get("http://127.0.0.1:8001/api/vocs").json()
    target = next(v["id"] for v in rows if v["status"] == "분석대기")
    page.locator(f'.voc-item[data-id="{target}"]').click()
    assert page.locator("#approve").is_disabled()
    page.locator("#search").fill("900001")
    assert page.locator(".voc-item").count() == 1
    page.locator("#search").fill("")
    page.screenshot(path="outputs/ui_initial.png", full_page=True)
    print(
        json.dumps(
            {
                "list_count": 512,
                "search": True,
                "approve_before_analysis_disabled": True,
                "browser_errors": errors,
            }
        )
    )
    assert not errors
    browser.close()
