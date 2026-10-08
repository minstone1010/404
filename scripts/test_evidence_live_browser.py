import json, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

base = "http://127.0.0.1:8001"
last_error = "모델 준비 중"
for attempt in range(120):
    try:
        stats = json.load(urllib.request.urlopen(base + "/api/stats", timeout=2))
        if stats["model_ready"]:
            break
    except OSError as exc:
        last_error = str(exc)
    time.sleep(1)
else:
    raise RuntimeError("서버 준비 시간 초과: " + last_error)
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
    page.goto(base)
    page.wait_for_selector(".voc-item")
    page.locator("#search").fill("900065")
    page.locator('.voc-item[data-id="900065"]').click()
    page.wait_for_function("!document.querySelector('#analyze').disabled")
    assert "E3" in page.locator(".analysis-value").first.inner_text()
    assert (
        "원인 확인 필요" in page.locator(".analysis").inner_text()
        or "원인 미확정" in page.locator(".analysis").inner_text()
    )
    assert len(posts) == 1 and posts[0].endswith("/900065/analyze"), posts
    detail = json.load(urllib.request.urlopen(base + "/api/vocs/900065", timeout=10))
    assert detail["function"] == "차량"
    assert all(
        rec["candidate_role"] == "reference" and "차량" in rec["fn"]
        for rec in detail["recs"]
    )
    assert detail["decision"] is None
    page.reload()
    page.wait_for_selector(".voc-item")
    page.locator("#search").fill("900065")
    page.locator('.voc-item[data-id="900065"]').click()
    assert (
        "E3" in page.locator(".analysis-value").first.inner_text() and len(posts) == 1
    )
    assert not errors, errors
    Path("outputs/evidence_validation/live_detail.json").write_text(
        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    page.screenshot(path="outputs/evidence_validation/live_8001.png", full_page=True)
    browser.close()
print(
    "8001 실제 자동 분석 → E3/차량 → 원인 검증 상태 → 참고 후보 → 새로고침 유지: 통과"
)
