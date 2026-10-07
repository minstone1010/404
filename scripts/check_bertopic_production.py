import json, sys, hashlib, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx
from playwright.sync_api import sync_playwright
from backend.config import settings

base = "http://127.0.0.1:8001"
with httpx.Client(base_url=base, timeout=120) as client:
    all_data = client.get("/api/topics").json()
    z1 = client.get("/api/topics/z1").json()
    assert all_data["status"] == z1["status"] == "ready"
    assert all_data["metrics"]["topic_count"] == 150
    assert client.get("/api/topics/trends").json()["reason"] == "날짜 데이터 없음"
    assert client.get("/api/vocs").status_code == 200
    assert client.get("/topics.html").status_code == 200
    runtime = client.get("/api/stats").json()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "/topics.html")
    page.wait_for_selector(".topic-row", timeout=120000)
    page.locator("#mode").select_option("z1")
    page.wait_for_function("document.querySelectorAll('.topic-row').length === 5")
    page.locator('.topic-row[data-topic="2"]').click()
    assert "콘센트" in page.locator("#topic-detail").inner_text()
    page.screenshot(path="outputs/bertopic_admin.png")
    assert not errors
    browser.close()
with sqlite3.connect(f'file:{settings.output / "voc.sqlite3"}?mode=ro', uri=True) as db:
    manual = db.execute("SELECT count(*) FROM manual_analyses").fetchone()[0]
    decisions = db.execute("SELECT count(*) FROM decisions").fetchone()[0]
report = dict(
    base_url=base,
    all_metrics=all_data["metrics"],
    z1_metrics=z1["metrics"],
    browser_errors=errors,
    manual_analysis_count=manual,
    decision_count=decisions,
    runtime=runtime,
)
Path("outputs/bertopic_production_check.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
