from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_default_timeout(30000)
    posts = []
    errors = []
    page.on(
        "request", lambda req: posts.append(req.url) if req.method == "POST" else None
    )
    page.on("pageerror", lambda error: errors.append(str(error)))
    for refresh in range(2):
        page.goto("http://127.0.0.1:8001/")
        page.wait_for_selector(".voc-item")
        page.locator("#search").fill("900010")
        page.locator('.voc-item[data-id="900010"]').click()
        panel = page.locator(".recommendation-panel")
        assert "검색 결과 비교" in panel.inner_text()
        assert "불일치" in panel.inner_text()
        assert page.locator(".rec-card").count() > 0
    assert not posts, posts
    assert not errors, errors
    page.screenshot(path="outputs/dual_validation/live_8001.png", full_page=True)
    browser.close()
print("8001 실제 후보·검색 비교 표시 / 새로고침 유지 / 자동 승인·중복 분석 없음: 통과")
