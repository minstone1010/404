import numpy as np
import pandas as pd
from backend.dual_retrieval import analysis_text, exclude_query, search


def test_analysis_query_does_not_include_original_or_truth():
    row = {
        "민원내용": "SECRET ORIGINAL",
        "handling_team": "SECRET DEPT",
        "topic_code": "SECRET TRUTH",
        "주요지": "유실물",
        "핵심키워드": "백팩",
        "분석상태": "분석오류",
    }
    text = analysis_text(row)
    assert "유실물" in text and "백팩" in text
    assert "SECRET" not in text


def test_search_excludes_self_duplicates_and_counts_independent_cases():
    frame = pd.DataFrame(
        [
            dict(번호="self", 중복그룹="q", 민원내용="query"),
            dict(번호="dup", 중복그룹="q", 민원내용="other"),
            dict(번호="equal", 중복그룹="e", 민원내용="query"),
            dict(번호="a", 중복그룹="g", 민원내용="case1"),
            dict(번호="b", 중복그룹="g", 민원내용="case2"),
            dict(번호="c", 중복그룹="h", 민원내용="case3"),
        ]
    )
    query = {"번호": "self", "중복그룹": "q", "민원내용": "query"}
    pool = exclude_query(frame, query)
    assert pool.번호.tolist() == ["a", "b", "c"]

    class Embed:
        def encode(self, *args, **kwargs):
            return np.array([[1.0, 0.0]])

    class Service:
        embedding = Embed()

    vectors = np.array(
        [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.7, 0.3]]
    )
    found = search(Service(), frame, vectors, pool, "query")
    assert found.번호.tolist() == ["a", "c"]
    assert np.allclose(found.similarity, [0.9, 0.7])


def test_raw_candidates_survive_analysis_mapping_failure(monkeypatch):
    from types import SimpleNamespace
    from backend import dual_retrieval as dual
    from backend import notebook_logic as logic

    frame = pd.DataFrame(
        [
            dict(
                번호="history1",
                중복그룹="g1",
                민원내용="분실물 백팩",
                handling_team="유실물부서",
                데이터역할="검색이력",
                dept_mapping_status="매핑완료",
                dept_region_code="R1",
                dept_scope="지역",
            ),
            dict(
                번호="history2",
                중복그룹="g2",
                민원내용="다른 지역 분실물",
                handling_team="다른지역부서",
                데이터역할="검색이력",
                dept_mapping_status="매핑완료",
                dept_region_code="R2",
                dept_scope="지역",
            ),
        ]
    )
    monkeypatch.setattr(logic, "df", frame)
    monkeypatch.setattr(logic, "history_df", frame.iloc[:0], raising=False)
    monkeypatch.setattr(logic, "attach_department_attributes", lambda f: f.copy())
    empty = frame.iloc[:0].copy()
    empty.attrs["routing_constraints"] = dict(mapping_gap=True, reference_only=True)
    monkeypatch.setattr(
        dual, "restrict_routing_candidates", lambda row: (empty, "매핑 실패")
    )
    monkeypatch.setattr(
        dual,
        "cached_vectors",
        lambda service, frame, texts, branch: np.array(
            [[1.0, 0.0] for _ in range(len(frame))]
        ),
    )

    class Embed:
        def encode(self, *args, **kwargs):
            return np.array([[1.0, 0.0]])

    monkeypatch.setattr(
        logic, "retrieve_similar_vocs", lambda *args: None, raising=False
    )
    query = dict(
        번호="query",
        중복그룹="q",
        민원내용="분실물",
        분석상태="분석오류",
        routing_scope="지역형",
        관할지역코드="R1",
        routing_resolution="resolved",
    )
    result = dual.recommend(SimpleNamespace(embedding=Embed()), query)
    assert result["similar_vocs"].handling_team.tolist() == ["유실물부서"]
    assert result["retrieval_comparison"]["raw_count"] == 1
    assert result["retrieval_comparison"]["analysis_count"] == 0
    assert result["retrieval_comparison"]["analysis_error"] is True
    assert result["recommended_department"] is None


def test_missing_analysis_similarity_is_json_null(monkeypatch):
    import json
    from backend import dual_retrieval as dual
    from backend import notebook_logic as logic
    from types import SimpleNamespace

    frame = pd.DataFrame(
        [
            dict(
                번호="h",
                중복그룹="g",
                민원내용="분실물",
                handling_team="과거부서",
                데이터역할="검색이력",
                dept_mapping_status="매핑완료",
            )
        ]
    )
    monkeypatch.setattr(logic, "df", frame)
    monkeypatch.setattr(logic, "history_df", frame.iloc[:0], raising=False)
    monkeypatch.setattr(logic, "attach_department_attributes", lambda f: f.copy())
    monkeypatch.setattr(
        dual,
        "cached_vectors",
        lambda service, frame, texts, branch: np.ones((len(frame), 1)),
    )
    monkeypatch.setattr(
        dual, "restrict_routing_candidates", lambda row: (frame.iloc[:0], "분석 실패")
    )
    monkeypatch.setattr(
        logic, "retrieve_similar_vocs", lambda *args: None, raising=False
    )
    embed = SimpleNamespace(encode=lambda *a, **k: np.ones((1, 1)))
    result = dual.recommend(
        SimpleNamespace(embedding=embed),
        dict(번호="q", 중복그룹="q", 민원내용="유실물 확인", 분석상태="분석오류"),
    )
    evidence = result["similar_vocs"].to_dict("records")
    assert evidence[0]["analysis_similarity"] is None
    json.dumps(evidence, allow_nan=False)
