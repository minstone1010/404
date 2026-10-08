import os, sys, json, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
root = Path(__file__).resolve().parent.parent
out = root / "outputs/praise_validation"
out.mkdir(exist_ok=True)
with (
    sqlite3.connect(f'file:{root / "outputs/voc.sqlite3"}?mode=ro', uri=True) as src,
    sqlite3.connect(out / "voc.sqlite3") as dst,
):
    src.backup(dst)
os.environ["OUTPUT_PATH"] = str(out)
os.environ["STARTUP_MODELS"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
from backend.service import Service

svc = Service()
r = svc.recommend("900075", force=True, source="manual")
assert not r.get("error"), r
assert r["analysis"]["voc_intent"] == "칭찬", r["analysis"]
assert r["analysis"]["cause_analysis_status"] == "not_applicable"
assert r["recommendation"]["status"] == "추천보류"
assert r["recommendation"]["routing_constraints"]["mapping_gap"]
assert not r["ranking"] and not r["evidence"]
assert svc.detail("900075")["intent"] == "칭찬"
assert (
    svc.store.manual_analysis("900075", svc.signature)["analysis"]["voc_intent"]
    == "칭찬"
)
(out / "result.json").write_text(
    json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
)
(out / "detail.json").write_text(
    json.dumps(svc.detail("900075"), ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(r, ensure_ascii=False), flush=True)
