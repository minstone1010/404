import json, os, sqlite3, sys, argparse
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
out = root / "outputs/dual_validation"
out.mkdir(exist_ok=True)
if not (out / "voc.sqlite3").exists():
    with (
        sqlite3.connect(
            f'file:{root/"outputs/voc.sqlite3"}?mode=ro', uri=True
        ) as source,
        sqlite3.connect(out / "voc.sqlite3") as target,
    ):
        source.backup(target)
os.environ.update(OUTPUT_PATH=str(out), STARTUP_MODELS="false", HF_HUB_OFFLINE="1")
from backend.service import Service
from backend import notebook_logic as logic

parser = argparse.ArgumentParser(
    description="실제 데이터 검색 검증; --force 사용 시 Qwen 재추론"
)
parser.add_argument("--force", action="store_true")
args = parser.parse_args()
svc = Service()
report = []
for id in ["900010", "900065", "900075", "900044"]:
    result = svc.recommend(id, source="manual", force=args.force)
    assert "recommendation" in result, result.get("error")
    detail = svc.detail(id)
    assert detail["retrievalComparison"]
    (out / (id + "-detail.json")).write_text(
        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert svc.store.manual_analysis(id, svc.signature) == result
    report.append(
        dict(
            id=id,
            topic=result["analysis"].get("주요지코드"),
            comparison=detail["retrievalComparison"],
            departments=[x["name"] for x in detail["recs"]],
            status=result["recommendation"]["status"],
        )
    )
    print(json.dumps(report[-1], ensure_ascii=False), flush=True)
(out / "report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
