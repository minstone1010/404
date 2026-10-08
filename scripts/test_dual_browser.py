import json
from pathlib import Path
from playwright.sync_api import sync_playwright

row = json.loads(Path("outputs/dual_validation/900010-detail.json").read_text())


def handle(route):
    path = route.request.url.split("/api/")[1]
    if route.request.method == "POST":
        raise AssertionError("unexpected mutation")
    if path == "vocs":
        data = [row]
    elif path == "departments":
        data = [r["name"] for r in row["recs"]]
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
    for url, file, mime in [
        ("http://voc.test/", "index.html", "text/html"),
        ("http://voc.test/app.js", "app.js", "application/javascript"),
        ("http://voc.test/styles.css", "styles.css", "text/css"),
    ]:
        page.route(
            url,
            lambda route, request, file=file, mime=mime: route.fulfill(
                path="voc-ui/dist/" + file, content_type=mime
            ),
        )
    page.goto("http://voc.test/")
    page.wait_for_selector(".voc-item")
    page.locator(".voc-item").click()
    assert "검색 결과 비교" in page.locator(".recommendation-panel").inner_text()
    assert "불일치" in page.locator(".recommendation-panel").inner_text()
    assert page.locator(".rec-card").count() == len(row["recs"])
    assert "참고 후보" in page.locator(".recommendation-panel").inner_text()
    assert not errors, errors
    page.screenshot(path="outputs/dual_validation/ui.png", full_page=True)
    browser.close()
print("검색 비교 · 불일치 · 참고 후보 표시: 통과")
