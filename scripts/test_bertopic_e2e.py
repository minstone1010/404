import json, time, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import httpx
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.analytics.bertopic_service import current, cache_root

base = "http://127.0.0.1:8002"
report = {}
with httpx.Client(base_url=base, timeout=120) as client:
    for route in [
        "/api/topics",
        "/api/topics/z1",
        "/api/topics/trends",
        "/api/topics/emerging",
        "/api/topics/warnings",
        "/api/topics/0",
        "/api/topics/documents/900001",
        "/api/vocs/900001",
    ]:
        response = client.get(route)
        assert response.status_code == 200, (route, response.text)
    report["api_routes"] = 8
    assert not client.get("/api/topics/trends").json()["enabled"]
    old = current("z1")["run_id"]
    response = client.post("/api/topics/rebuild", json={"mode": "both", "force": False})
    assert response.status_code == 202, response.text
    for _ in range(120):
        state = client.get("/api/topics").json()["job"]
        if state["status"] in ["completed", "failed"]:
            break
        time.sleep(0.5)
    assert state["status"] == "completed", state
    assert current("z1")["run_id"] == old
    report["rebuild_reuses_model"] = True
    response = client.post("/api/topics/rebuild", json={"mode": "z1", "force": True})
    assert response.status_code == 202, response.text
    second = client.post("/api/topics/rebuild", json={"mode": "all"})
    assert second.status_code == 409, second.text
    for _ in range(180):
        state = client.get("/api/topics").json()["job"]
        if state["status"] in ["completed", "failed"]:
            break
        time.sleep(0.5)
    assert state["status"] == "completed", state
    rebuilt = current("z1")
    assert rebuilt["run_id"] != old
    assert rebuilt["embedding"]["computed_unique"] == 0
    report["force_retrains_without_embedding_recompute"] = True
    report["concurrent_rebuild_rejected"] = True
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    writes = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "request",
        lambda request: (
            writes.append(request.url) if request.method == "POST" else None
        ),
    )
    page.goto(base + "/topics.html")
    page.wait_for_selector(".topic-row", timeout=120000)
    assert page.locator(".topic-row").count() == 151
    page.locator('.topic-row[data-topic="2"]').click()
    assert "Topic 2" in page.locator("#topic-detail").inner_text()
    assert "날짜 데이터 없음" in page.locator("#topic-trends").inner_text()
    page.locator("#mode").select_option("z1")
    page.wait_for_function("document.querySelectorAll('.topic-row').length === 5")
    page.locator('.topic-row[data-topic="2"]').click()
    assert "콘센트" in page.locator("#topic-detail").inner_text()
    page.screenshot(path="outputs/bertopic_admin.png")
    page.reload()
    page.wait_for_selector(".topic-row")
    assert not writes and not errors, (writes, errors)
    page.goto(base + "/index.html")
    page.wait_for_selector(".voc-item", timeout=120000)
    assert page.locator(".voc-item").count() == 512
    assert page.locator('a[href="topics.html"]').count() == 1
    assert not writes
    report.update(
        browser_topic_detail=True,
        browser_z1=True,
        browser_refresh=True,
        live_ui_list_count=512,
        no_live_analysis_or_decision_requests=True,
        browser_errors=errors,
    )
    browser.close()
Path("outputs/bertopic_e2e.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
