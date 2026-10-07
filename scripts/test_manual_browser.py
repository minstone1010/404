import sys, json, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from backend.config import settings

id = "900010"
path = settings.output / "voc.sqlite3"
with sqlite3.connect(path) as db:
    prior = db.execute(
        "SELECT payload FROM manual_analyses WHERE id=?", (id,)
    ).fetchone()
    assert prior is None, "사용자 실행 기록이 있는 VOC는 시험에서 덮어쓰지 않습니다"
    legacy = db.execute("SELECT payload FROM analyses WHERE id=?", (id,)).fetchone()
    if legacy:
        (settings.output / "manual_fix_previous_result.json").write_text(legacy[0])
result = None
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_default_timeout(300000)
        requests = []
        errors = []
        page.on("request", lambda r: requests.append((r.method, r.url)))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8001")
        page.wait_for_selector(".voc-item")
        page.locator(f'.voc-item[data-id="{id}"]').click()
        assert page.locator(".analysis-value").first.inner_text() == "미분석"
        assert page.locator("#approve").is_disabled()
        page.locator("#search").fill(id)
        page.locator("#reset").click()
        page.wait_for_selector(".voc-item")
        page.reload()
        page.wait_for_selector(".voc-item")
        page.locator(f'.voc-item[data-id="{id}"]').click()
        assert page.locator(".analysis-value").first.inner_text() == "미분석"
        assert not [
            url for method, url in requests if method == "POST" and "/analyze" in url
        ]
        with page.expect_response(
            lambda r: f"/{id}/analyze" in r.url and r.request.method == "POST"
        ) as event:
            page.locator("#analyze").click()
        response = event.value
        result = response.json()
        assert response.status == 200 and result["execution_source"] == "manual"
        assert result["analysis"]["분석상태"] == "분석완료", result
        page.wait_for_function(
            "document.getElementById('analyze').textContent.includes('재분석')"
        )
        timestamp = result["analyzed_at"]
        page.reload()
        page.wait_for_selector(".voc-item")
        page.locator(f'.voc-item[data-id="{id}"]').click()
        assert page.locator(".analysis-value").first.inner_text() != "미분석"
        restored = page.request.get(f"http://127.0.0.1:8001/api/vocs/{id}").json()
        assert (
            restored["result"]["analyzed_at"] == timestamp
            and restored["decision"] is None
        )
        assert (
            len(
                [
                    url
                    for method, url in requests
                    if method == "POST" and "/analyze" in url
                ]
            )
            == 1
        )
        assert not errors
        page.screenshot(
            path=str(settings.output / "manual_analysis_browser.png"), full_page=True
        )
        report = dict(
            no_analysis_on_load_select_refresh=True,
            one_post_after_click=True,
            real_qwen=True,
            manual_result_persisted=True,
            no_auto_approval=True,
            browser_errors=errors,
            analysis=result,
        )
        (settings.output / "manual_analysis_browser_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
        )
        print(
            json.dumps(
                {k: v for k, v in report.items() if k != "analysis"}, ensure_ascii=False
            )
        )
        browser.close()
finally:
    if result:
        with sqlite3.connect(path) as db:
            row = db.execute(
                "SELECT payload FROM manual_analyses WHERE id=?", (id,)
            ).fetchone()
            if row and json.loads(row[0]).get("analyzed_at") == result.get(
                "analyzed_at"
            ):
                db.execute("DELETE FROM manual_analyses WHERE id=?", (id,))
