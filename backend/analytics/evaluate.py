"""Offline diagnostics; reference labels are accessed only after warning generation."""

import json, sqlite3
from pathlib import Path
from backend.config import settings
from backend.service import recommendation_signature
from backend.analytics.config import AnalyticsConfig, cache_root
from backend.analytics.bertopic_service import current, atomic_json
from backend.analytics.topic_validation import warnings


def evaluate():
    from backend import notebook_logic as logic

    result = current("all")
    if result["status"] != "ready":
        raise RuntimeError("전체 Topic 배치를 먼저 실행하세요")
    signature = recommendation_signature()
    candidates = warnings(
        result, signature, settings.output / "voc.sqlite3", AnalyticsConfig()
    )
    flagged = {x["id"] for x in candidates}
    saved = {}
    with sqlite3.connect(
        f'file:{settings.output / "voc.sqlite3"}?mode=ro', uri=True
    ) as db:
        for table in ["analyses", "manual_analyses"]:
            saved.update(
                {
                    id: json.loads(payload)
                    for id, payload in db.execute(
                        f"SELECT id,payload FROM {table} WHERE signature=?",
                        (signature,),
                    )
                }
            )
    truth = logic.evaluation_truth_df.set_index("번호").topic_code.to_dict()
    targets = logic.df.loc[logic.df.데이터역할.eq("검토대상")].drop_duplicates(
        "중복그룹"
    )
    checked = []
    for row in targets.itertuples(index=False):
        id = str(getattr(row, "번호"))
        analysis = saved.get(id, {}).get("analysis", {})
        if analysis.get("분석상태") == "분석완료" and truth.get(id):
            checked.append((id, analysis.get("주요지코드") != truth[id], id in flagged))
    errors = sum(wrong for _, wrong, _ in checked)
    detected = sum(wrong and warning for _, wrong, warning in checked)
    marked = sum(warning for _, _, warning in checked)
    report = dict(
        topic_metrics=result["metrics"],
        z1_metrics=current("z1").get("metrics"),
        warning_candidates_total=len(candidates),
        holdout_analyzed_independent_cases=len(checked),
        qwen_label_mismatches=errors,
        flagged_holdout_cases=marked,
        detected_mismatches=detected,
        review_detection_recall=detected / errors if errors else None,
        review_precision=detected / marked if marked else None,
        without_bertopic_review_flags=0,
        with_bertopic_review_flags=marked,
        recommendation_changes=0,
        automatic_label_changes=0,
        notice="저장된 분석만 평가. 더미 원본 라벨의 오류 가능성이 있고 작은 표본은 일반화 불가. 군집은 전체 누적 원문으로 학습한 탐색 분석이며 엄격한 미래 예측 holdout 평가가 아님. 자동 추천 감소 성능은 측정하지 않음.",
    )
    atomic_json(cache_root() / "evaluation.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
