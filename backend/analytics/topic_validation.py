from collections import Counter, defaultdict
import sqlite3, json


def warnings(result, signature, db_path, config):
    if not db_path.exists():
        return []
    groups = defaultdict(dict)
    for row in result["document_mapping"]:
        if (
            row["topic_id"] != -1
            and row["role"] == "검색이력"
            and row["source_topic_code"]
        ):
            groups[row["topic_id"]].setdefault(
                row["case_group_id"], row["source_topic_code"]
            )
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        saved = {}
        for table in ["analyses", "manual_analyses"]:
            for id, payload in db.execute(
                f"SELECT id,payload FROM {table} WHERE signature=?", (signature,)
            ):
                saved[id] = json.loads(payload)
    output = []
    for row in result["document_mapping"]:
        analysis = saved.get(row["id"], {}).get("analysis", {})
        label = analysis.get("주요지코드")
        if analysis.get("분석상태") != "분석완료" or not label or row["topic_id"] == -1:
            continue
        # Independent history labels only, never this VOC's label or duplicate group.
        counts = Counter(
            v
            for group, v in groups[row["topic_id"]].items()
            if group != row["case_group_id"]
        )
        total = sum(counts.values())
        if total < config.warning_min_cases:
            continue
        dominant, n = counts.most_common(1)[0]
        share = n / total
        own = counts.get(label, 0) / total
        if (
            dominant != label
            and share >= config.dominant_ratio
            and own <= config.warning_threshold
        ):
            output.append(
                dict(
                    id=row["id"],
                    topic_id=row["topic_id"],
                    qwen_topic_code=label,
                    dominant_label=dominant,
                    dominant_ratio=share,
                    qwen_label_ratio=own,
                    reference_unique_cases=total,
                    semantic_warning=True,
                    reason="분류 재검토 필요",
                    reference="동일 군집의 과거 이력 원본 요지 라벨; 대상 및 중복 그룹 제외",
                    automatic_label_change=False,
                )
            )
    return output
