import os, sys, json, sqlite3, shutil, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
root = Path(__file__).resolve().parent.parent
isolated = root / "outputs" / "routing_guard_validation"
isolated.mkdir(exist_ok=True)
with (
    sqlite3.connect(f'file:{root / "outputs/voc.sqlite3"}?mode=ro', uri=True) as source,
    sqlite3.connect(isolated / "voc.sqlite3") as target,
):
    source.backup(target)
for p in sorted(
    (root / "outputs").glob("embedding-*.npz"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)[:2]:
    shutil.copy2(p, isolated / p.name)
os.environ["OUTPUT_PATH"] = str(isolated)
os.environ["STARTUP_MODELS"] = "false"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from backend.service import Service, recommendation_signature
from backend import notebook_logic as logic

service = Service()
report = dict(
    history_searchable=len(logic.history_df),
    history_quality_excluded=service.history_quality_excluded,
    cases=[],
)
truth = logic.evaluation_truth_df.set_index("번호").to_dict("index")
for id in ["900001", "900006", "900009", "900044", "900053"]:
    old = (
        service.store.manual_analysis(id, recommendation_signature("web-v2-strict"))
        or {}
    )
    result = service.recommend(id, force=True, source="evaluation")
    report["cases"].append(
        dict(
            id=id,
            before_topic=old.get("analysis", {}).get("주요지코드"),
            before_department=old.get("recommendation", {}).get(
                "first_priority_department"
            ),
            after_analysis=result.get("analysis"),
            after_recommendation=result.get("recommendation"),
            ranking=result.get("ranking"),
            error=result.get("error"),
            truth_topic=truth[id]["topic_code"],
            truth_department=truth[id]["handling_team"],
        )
    )
    print(json.dumps(report["cases"][-1], ensure_ascii=False), flush=True)
(root / "outputs/routing_guard_real_results.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
