import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright

base = "http://127.0.0.1:8002"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.wait_for_selector(".voc-item", timeout=120000)
    page.locator('.voc-item[data-id="900044"]').click()
    page.locator("#analyze").click()
    page.wait_for_function(
        "document.querySelector('.rec-name')?.textContent.includes('부산경남본부 시설처')",
        timeout=120000,
    )
    assert "관할 일치" in page.locator(".rec-card").first.inner_text()
    assert "최신 공식 명칭 미검증" in page.locator(".rec-card").first.inner_text()
    detail = page.request.get(base + "/api/vocs/900044").json()
    assert detail["locationRole"] == "incident" and detail["scope"] == "지역형"
    page.screenshot(path="outputs/routing_guard_local_ui.png", full_page=True)
    page.locator('.voc-item[data-id="900001"]').click()
    page.locator("#analyze").click()
    page.wait_for_function(
        "document.querySelector('.reason')?.textContent.includes('사건 관할·범위 미확정')",
        timeout=120000,
    )
    assert "참고 후보" in page.locator(".rec-card").first.inner_text()
    row = page.request.get(base + "/api/vocs/900001").json()
    assert row["hold"] and row["hq"] is None
    page.reload()
    page.wait_for_selector(".voc-item")
    page.locator('.voc-item[data-id="900001"]').click()
    assert "사건 관할·범위 미확정" in page.locator(".reason").inner_text()
    assert page.request.get(base + "/api/stats").json()["decisions"] == 0
    assert not errors
    print(
        json.dumps(
            dict(
                local_jurisdiction=True,
                department_provenance=True,
                uncertain_reference=True,
                persist_after_refresh=True,
                no_approvals=True,
                browser_errors=errors,
            ),
            ensure_ascii=False,
        )
    )
    browser.close()
