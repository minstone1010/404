import json
import numpy as np
import pandas as pd
import pytest
from backend import notebook_logic as logic
from backend.intent import enrich_intent, source_intent
from backend.routing import restrict_routing_candidates
from backend.semantic import resolve_routing, recommendation_guard


def test_praise_distinguishes_complaint_and_mixed():
    assert source_intent("승무원님 덕분에 치료받았습니다. 감사드립니다.") == "칭찬"
    assert source_intent("승무원이 안 도와주고 그냥 지나가버렸어요") == "불만"
    assert (
        source_intent("도움은 감사드립니다. 하지만 다른 직원은 불친절했습니다.")
        == "복합"
    )
    assert (
        source_intent("환불이 안 됩니다. 답변 부탁드립니다. 감사합니다.") == "확인필요"
    )
    a = enrich_intent("도와주셔서 감사드립니다.", {"voc_intent": "불만"})
    assert a["semantic_issues"]


def test_missing_master_function_never_searches_other_functions(monkeypatch):
    frame = pd.DataFrame(
        [
            dict(
                dept_business_function="여객·서비스",
                dept_scope="지역",
                dept_region_code="전남",
            )
        ]
    )
    monkeypatch.setattr(logic, "history_df", frame, raising=False)
    pool, note = restrict_routing_candidates(
        {"업무기능후보": ["승무·서비스"], "routing_scope": "확인필요"}
    )
    assert pool.empty and pool.attrs["routing_constraints"]["mapping_gap"]
    assert "소속 확인" in note


def test_praise_retrieval_excludes_high_similarity_complaints(monkeypatch):
    frame = pd.DataFrame(
        [
            {
                "번호": str(i),
                "중복그룹": str(i),
                "민원내용": str(i),
                "voc_intent": intent,
            }
            for i, intent in enumerate(["칭찬", "불만", "확인필요", "복합"])
        ]
    )
    monkeypatch.setattr(logic, "history_df", frame, raising=False)
    monkeypatch.setattr(
        logic, "restrict_routing_candidates", lambda r: (frame, "시험"), raising=False
    )
    monkeypatch.setattr(
        logic,
        "history_embeddings",
        np.array([[0.7, 0], [1, 0], [0.99, 0], [0.98, 0]]),
        raising=False,
    )
    monkeypatch.setattr(
        logic,
        "embed_model",
        type("Embed", (), {"encode": lambda self, *a, **k: np.array([[1.0, 0.0]])})(),
        raising=False,
    )
    pool = logic.retrieve_similar_vocs(
        {
            "번호": "new",
            "중복그룹": "new",
            "민원내용": "감사드립니다",
            "분석상태": "분석완료",
            "voc_intent": "칭찬",
        }
    )
    assert pool.번호.tolist() == ["0"]
    assert pool.attrs["routing_constraints"]["intent_excluded_count"] == 3


def test_intent_json_validation_and_summary_embedding():
    data = {
        "main_topic_code": "F2",
        "sub_topic_code": None,
        "keywords": ["승무원", "응급 대응", "감사"],
        "voc_intent": "칭찬",
        "request_summary": "승무원 응급 대응 칭찬",
        "intent_evidence": "감사드립니다",
    }
    parsed = logic.parse_topic(json.dumps(data, ensure_ascii=False))
    assert parsed["voc_intent"] == "칭찬"
    assert "승무원 응급 대응 칭찬" in logic.embedding_text(parsed)
    data["voc_intent"] = "좋음"
    with pytest.raises(ValueError):
        logic.parse_topic(json.dumps(data))


def test_intent_conflict_and_mapping_gap_are_held():
    a = resolve_routing(
        "승무원님 도움에 감사드립니다.",
        {"voc_intent": "불만", "routing_scope": "확인필요", "location_candidate": None},
    )
    assert a["semantic_issues"]
    rec = recommendation_guard(
        a, {"status": "추천가능", "routing_constraints": {"mapping_gap": True}}, []
    )
    assert rec["status"] == "추천보류" and rec["recommended_department"] is None


def test_semantic_failure_never_expands_to_unrelated_candidates(monkeypatch):
    monkeypatch.setattr(
        logic,
        "history_df",
        pd.DataFrame(
            [
                dict(
                    dept_business_function="시설",
                    dept_scope="지역",
                    dept_region_code="R",
                )
            ]
        ),
        raising=False,
    )
    pool, note = restrict_routing_candidates(
        {
            "업무기능후보": ["시설"],
            "semantic_issues": ["원문에 없는 요약"],
            "routing_scope": "확인필요",
        }
    )
    assert (
        pool.empty and pool.attrs["routing_constraints"]["stage"] == "semantic_review"
    )
    assert "검색하지 않음" in note
