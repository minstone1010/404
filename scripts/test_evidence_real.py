import json, os, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
root = Path(__file__).resolve().parent.parent
out = root / "outputs/evidence_validation"
out.mkdir(exist_ok=True)
with (
    sqlite3.connect(f'file:{root/"outputs/voc.sqlite3"}?mode=ro', uri=True) as source,
    sqlite3.connect(out / "voc.sqlite3") as target,
):
    source.backup(target)
os.environ["OUTPUT_PATH"] = str(out)
os.environ["STARTUP_MODELS"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
from backend.service import Service

svc = Service()
r = svc.recommend("900065", force=True, source="manual")
assert not r.get("error"), r
assert r["analysis"]["주요지코드"] == "E3" or r["analysis"].get("semantic_issues"), r
if r["analysis"]["주요지코드"] == "F2":
    assert r["recommendation"]["recommended_department"] is None
assert not (
    "승무원" in r["analysis"].get("발생원인_판단이유", "")
    and r["analysis"].get("cause_analysis_status") == "validated"
), r
(out / "result.json").write_text(
    json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
)
(out / "detail.json").write_text(
    json.dumps(svc.detail("900065"), ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(r, ensure_ascii=False), flush=True)
