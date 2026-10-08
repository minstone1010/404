"""Independent original-text and analysis-text retrieval; no query truth labels."""

import hashlib
import json
import numpy as np
import pandas as pd
from backend import notebook_logic as logic
from backend.config import settings
from backend.routing import restrict_routing_candidates
from backend.intent import source_intent
from backend.semantic import topic_issues

VERSION = "dual-retrieval-v1"


def analysis_text(row):
    fields = ["voc_intent", "request_summary", "주요지", "부요지", "핵심키워드"]
    return (
        "\n".join(str(row.get(k) or "") for k in fields) + "\n" + logic.cause_text(row)
    )


def cached_vectors(service, frame, texts, branch):
    key = hashlib.sha256(
        json.dumps(
            [VERSION, settings.embedding_model, branch, frame["번호"].tolist(), texts],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    memory = getattr(service, "dual_vector_cache", {})
    if key in memory:
        return memory[key]
    cache = settings.output / ("dual-" + branch + "-" + key + ".npz")
    if not texts:
        vectors = np.zeros((0, 384))
    elif cache.exists():
        with np.load(cache, allow_pickle=False) as saved:
            vectors = saved["vectors"]
    else:
        vectors = service.embedding.encode(
            texts,
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        temp = cache.with_suffix(".tmp.npz")
        np.savez_compressed(temp, vectors=vectors)
        temp.replace(cache)
    if len(vectors) != len(frame):
        raise ValueError("검색 인덱스와 VOC 행 수가 다릅니다")
    memory = {
        k: v for k, v in memory.items() if k == getattr(service, "raw_vector_key", None)
    }
    memory[key] = vectors
    service.dual_vector_cache = memory
    if branch == "raw":
        service.raw_vector_key = key
    return vectors


def exclude_query(pool, query):
    return pool.loc[
        pool["번호"].ne(logic.clean_id(query["번호"]))
        & pool["중복그룹"].ne(query["중복그룹"])
        & pool["민원내용"].map(logic.clean_text).ne(logic.clean_text(query["민원내용"]))
    ].copy()


def search(service, frame, vectors, pool, text):
    if pool.empty or not text.strip():
        result = pool.iloc[:0].copy()
        result["similarity"] = pd.Series(dtype=float)
        return result
    vector = service.embedding.encode(
        [text], normalize_embeddings=True, convert_to_numpy=True
    )[0]
    pool = pool.copy()
    pool["similarity"] = vectors[pool.index.to_numpy()] @ vector
    # Each duplicate group contributes at most one independent case.
    return (
        pool.sort_values("similarity", ascending=False)
        .drop_duplicates("중복그룹")
        .head(settings.top_k)
        .copy()
    )


def recommend(service, query):
    raw_frame = logic.attach_department_attributes(
        logic.df.loc[logic.df["데이터역할"].eq("검색이력")]
    ).reset_index(drop=True)
    raw_frame = raw_frame.loc[raw_frame.dept_mapping_status.eq("매핑완료")].reset_index(
        drop=True
    )
    raw_vectors = cached_vectors(
        service, raw_frame, raw_frame["민원내용"].map(logic.clean_text).tolist(), "raw"
    )
    raw_pool = raw_frame
    resolved = query.get("routing_resolution") != "unresolved"
    scope = query.get("routing_scope")
    if resolved and scope == "지역형" and query.get("관할지역코드"):
        raw_pool = raw_pool.loc[
            raw_pool.dept_region_code.eq(query["관할지역코드"])
            & raw_pool.dept_scope.eq("지역")
        ]
    elif resolved and scope == "전국형":
        raw_pool = raw_pool.loc[raw_pool.dept_scope.isin(["전국", "광역/전국", "본사"])]
    if query.get("voc_intent") in {"칭찬", "불만"}:
        intents = raw_pool["민원내용"].map(source_intent)
        if query.get("voc_intent") == "칭찬":
            raw_pool = raw_pool.loc[intents.eq("칭찬")]
        else:
            raw_pool = raw_pool.loc[~intents.eq("칭찬")]
    source_issues = topic_issues(query["민원내용"], query)
    choices = query.get("업무기능후보", [])
    function_filtered = False
    if (
        choices
        and not source_issues
        and not query.get("semantic_issues")
        and query.get("분석상태") == "분석완료"
    ):
        preferred = raw_pool.loc[raw_pool.dept_business_function.isin(choices)]
        if not preferred.empty:
            raw_pool = preferred
            function_filtered = True
    raw = search(
        service,
        raw_frame,
        raw_vectors,
        exclude_query(raw_pool, query),
        logic.clean_text(query["민원내용"]),
    )
    frame = logic.history_df
    analysis_vectors = cached_vectors(
        service, frame, [analysis_text(r) for r in frame.to_dict("records")], "analysis"
    )
    pool, note = restrict_routing_candidates(query)
    constraints = dict(pool.attrs.get("routing_constraints", {}))
    if query.get("분석상태") != "분석완료":
        pool = pool.iloc[:0]
    analyzed = search(
        service,
        frame,
        analysis_vectors,
        exclude_query(pool, query),
        analysis_text(query),
    )
    raw_valid = raw.loc[raw.similarity.ge(settings.min_similarity)]
    analysis_valid = analyzed.loc[
        analyzed.similarity.ge(settings.analysis_min_similarity)
    ]
    raw_ids = set(raw_valid["번호"])
    analysis_ids = set(analysis_valid["번호"])
    raw_teams = set(raw_valid.handling_team)
    analysis_teams = set(analysis_valid.handling_team)
    disagreement = bool(
        raw_teams and (not analysis_teams or not raw_teams.intersection(analysis_teams))
    )
    selected = raw_valid.copy()
    scores = dict(zip(analysis_valid["번호"], analysis_valid.similarity))
    selected["raw_similarity"] = selected["similarity"]
    selected["analysis_similarity"] = selected["번호"].map(scores)
    selected["analysis_similarity"] = (
        selected["analysis_similarity"]
        .astype(object)
        .where(selected["analysis_similarity"].notna(), None)
    )
    selected["search_source"] = selected["번호"].map(
        lambda id: "원문 + 분석 일치" if id in analysis_ids else "원문 검색"
    )
    # Analysis-only matches cannot introduce cases unsupported by the original text.
    selected.attrs["routing_filter_info"] = (
        "원문 검색 → 분석 검색 비교 → 독립 사례 기반 후보 구성 | " + note
    )
    constraints["reference_only"] = bool(
        constraints.get("reference_only")
        or disagreement
        or source_issues
        or query.get("semantic_issues")
        or query.get("분석상태") != "분석완료"
    )
    selected.attrs["routing_constraints"] = constraints
    original = logic.retrieve_similar_vocs
    try:
        logic.retrieve_similar_vocs = lambda row, top_k=settings.top_k: selected.head(
            top_k
        ).copy()
        result = logic.recommend_department(query)
    finally:
        logic.retrieve_similar_vocs = original
    if disagreement or query.get("분석상태") != "분석완료":
        result.update(status="추천보류", recommended_department=None)
        result[
            "reason"
        ] += " | 원문과 분석 검색 불일치 또는 분석 실패: 원문 근거 후보를 담당자가 확인하세요."
    result["retrieval_comparison"] = dict(
        raw_count=len(raw_valid),
        analysis_count=len(analysis_valid),
        overlap_count=len(raw_ids.intersection(analysis_ids)),
        disagreement=disagreement,
        selection_policy="원문 유사도 기준 충족 + 중복 그룹당 1건; 분석 검색은 비교 근거",
        raw_history_count=len(raw_frame),
        analysis_history_count=len(frame),
        raw_departments=sorted(raw_teams),
        analysis_departments=sorted(analysis_teams),
        analysis_error=query.get("분석상태") != "분석완료",
        source_validation_issues=source_issues,
        function_filtered=function_filtered,
        analysis_min_similarity=settings.analysis_min_similarity,
    )
    return result
