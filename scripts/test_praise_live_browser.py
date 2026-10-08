import json
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_default_timeout(180000)
    posts = []
    errors = []
    page.on(
        "request", lambda req: posts.append(req.url) if req.method == "POST" else None
    )
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8001")
    page.wait_for_selector(".voc-item")
    page.locator("#search").fill("900075")
    page.locator('.voc-item[data-id="900075"]').click()
    page.wait_for_function("!document.querySelector('#analyze').disabled")
    assert page.locator(".rec-card").count() == 0
    assert "소속 확인" in page.locator(".rec-body").inner_text()
    assert "민원 의도: 칭찬" in page.locator("#detail-area").inner_text()
    assert len(posts) == 1 and posts[0].endswith("/900075/analyze"), posts
    page.reload()
    page.wait_for_selector(".voc-item")
    page.locator("#search").fill("900075")
    page.locator('.voc-item[data-id="900075"]').click()
    assert "민원 의도: 칭찬" in page.locator("#detail-area").inner_text()
    assert len(posts) == 1
    assert not errors, errors
    page.screenshot(path="outputs/praise_validation/live_8001.png", full_page=True)
    browser.close()
print(
    "8001 실제 목록 클릭 → AI 분석 → 칭찬 표시 → 부서 연결 공백 안내 → 무관 후보 없음 → 새로고침 유지: 통과"
)
