import json
from pathlib import Path
from playwright.sync_api import sync_playwright

row = json.loads(Path("outputs/praise_validation/detail.json").read_text())
posts = []


def handle(route):
    path = route.request.url.split("/api/")[1]
    if route.request.method == "POST":
        posts.append(path)
        raise AssertionError("unexpected POST")
    if path == "vocs":
        data = [row]
    elif path == "departments":
        data = []
    elif path == "stats":
        data = {
            "history_searchable": 0,
            "history_total": 0,
            "history_preparation_done": True,
            "history_failed": 0,
        }
    else:
        data = row
    route.fulfill(json=data)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/api/**", handle)
    # Use local static assets, while API traffic is intercepted.
    page.route(
        "http://voc.test/",
        lambda route: route.fulfill(
            path="voc-ui/dist/index.html", content_type="text/html"
        ),
    )
    page.route(
        "http://voc.test/app.js",
        lambda route: route.fulfill(
            path="voc-ui/dist/app.js", content_type="application/javascript"
        ),
    )
    page.route(
        "http://voc.test/styles.css",
        lambda route: route.fulfill(
            path="voc-ui/dist/styles.css", content_type="text/css"
        ),
    )
    page.goto("http://voc.test/")
    page.wait_for_selector(".voc-item")
    page.locator(".voc-item").click()
    assert "민원 의도: 칭찬" in page.locator("#detail-area").inner_text()
    assert "소속 확인" in page.locator(".rec-body").inner_text()
    assert page.locator(".rec-card").count() == 0
    assert not posts and not errors
    page.screenshot(path="outputs/praise_validation/ui.png", full_page=True)
    browser.close()
print("칭찬 표시, 소속 확인 안내, 무관 후보 숨김, 저장 결과 재사용: 통과")
