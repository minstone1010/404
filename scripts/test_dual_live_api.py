import json, urllib.request
from pathlib import Path

base = "http://127.0.0.1:8001"


def read(path):
    return json.load(urllib.request.urlopen(base + path, timeout=300))


rows = read("/api/vocs")
assert rows
id = "900010"
before = read("/api/stats")["decisions"]
result = json.load(
    urllib.request.urlopen(
        urllib.request.Request(base + "/api/vocs/" + id + "/analyze", method="POST"),
        timeout=300,
    )
)
first = read("/api/vocs/" + id)
second = read("/api/vocs/" + id)
assert first["result"] == second["result"] == result
assert first["retrievalComparison"] and first["recs"]
assert read("/api/stats")["decisions"] == before
out = Path("outputs/dual_validation")
(out / "live-detail.json").write_text(
    json.dumps(first, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        dict(
            list_count=len(rows),
            comparison=first["retrievalComparison"],
            departments=[r["name"] for r in first["recs"]],
            status=first["status"],
            decision_unchanged=True,
            persisted=True,
        ),
        ensure_ascii=False,
    ),
    flush=True,
)
