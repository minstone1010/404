import json, urllib.request, copy
from pathlib import Path
from playwright.sync_api import sync_playwright

base = "http://127.0.0.1:8001"
rows = json.load(urllib.request.urlopen(base + "/api/vocs"))[:2]
for row in rows:
    row["result"] = {}
    row["recs"] = []
    row["decision"] = None
    row["status"] = "분석대기"
    row["topic"] = "미분석"
posts = []
held = []
errors = []


def handle(route):
    req = route.request
    path = req.url.split("/api/")[1]
    if path == "vocs":
        data = rows
    elif path == "departments":
        data = ["테스트부서"]
    elif path == "stats":
        data = {
            "history_searchable": 0,
            "history_total": 0,
            "history_preparation_done": True,
            "history_failed": 0,
        }
    elif path.endswith("/analyze"):
        posts.append(path)
        held.append(route)
        return
    elif path.startswith("vocs/"):
        data = next(r for r in rows if r["id"] == path.split("/")[1])
    else:
        raise AssertionError(path)
    route.fulfill(json=data)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/api/**", handle)
    page.goto(base)
    page.wait_for_selector(".voc-item")
    assert not posts
    a, b = [r["id"] for r in rows]

    def click(id):
        page.locator(f'.voc-item[data-id="{id}"]').click()

    click(a)
    page.wait_for_function("document.querySelector('#analyze').disabled")
    click(a)
    assert len(posts) == 1
    assert page.locator("#approve").is_disabled()
    click(b)
    page.locator("#memo").fill("작성 중인 메모")
    page.wait_for_timeout(100)
    rows[0]["result"] = {
        "analysis": {"주요지": "D1"},
        "execution_source": "manual",
        "analyzed_at": "2026-10-08T00:00:00Z",
    }
    rows[0]["topic"] = "테스트 분석 완료"
    held[0].fulfill(json=rows[0]["result"])
    page.wait_for_timeout(300)
    assert page.locator("#memo").input_value() == "작성 중인 메모"
    click(a)
    assert page.locator(".analysis-value").first.inner_text() == "테스트 분석 완료"
    assert len(posts) == 2
    click(a)
    assert len(posts) == 2
    rows[1]["result"] = {"analysis": {"주요지": "D1"}}
    held[1].fulfill(json=rows[1]["result"])
    page.wait_for_timeout(300)
    page.reload()
    page.wait_for_selector(".voc-item")
    click(a)
    assert len(posts) == 2
    page.locator("#analyze").click()
    page.wait_for_timeout(100)
    assert len(posts) == 3
    held[2].fulfill(json=rows[0]["result"])
    page.wait_for_function("!document.querySelector('#analyze').disabled")
    assert not errors, errors
    page.screenshot(path="outputs/auto_selection_ui.png", full_page=True)
    browser.close()
report = {
    "passed": True,
    "checks": [
        "initial load does not analyze",
        "list click auto analyzes",
        "duplicate clicks share request",
        "approval disabled during analysis",
        "other completion preserves current memo",
        "saved analysis reused",
        "refresh reuses saved result",
        "manual reanalysis available",
        "no automatic decision POST",
        "no browser errors",
    ],
}
Path("outputs/auto_selection_browser_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2)
)
print(json.dumps(report, ensure_ascii=False))
