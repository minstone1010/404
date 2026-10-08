import json
import pandas as pd
from backend.semantic import topic_issues, resolve_routing, recommendation_guard
from backend.routing import restrict_routing_candidates
from backend import notebook_logic as l
from backend.service import Service


def test_local_station_scope_and_suffix():
    result = resolve_routing(
        "수원역 광장 흡연부스 연기가 출입구로 들어옵니다.",
        dict(
            location_candidate="수원역 광장", routing_scope="확인필요", 주요지코드="D2"
        ),
    )
    assert result["표준위치"] == "수원역" and result["관할본부"] == "수도권서부본부"
    assert result["location_role"] == "incident" and result["routing_scope"] == "지역형"


def test_route_station_and_invented_station_are_not_jurisdictions():
    for text, candidate in [
        ("부산역에서 서울 가는 무궁화호 탔는데 에어컨이 고장났습니다.", "부산역"),
        ("적자 개선을 위해 임대 수익을 늘려 주세요.", "경상도역"),
    ]:
        result = resolve_routing(
            text,
            dict(
                location_candidate=candidate, routing_scope="확인필요", 주요지코드="E1"
            ),
        )
        assert result["location_candidate"] is None and result["관할본부"] is None
        assert result["routing_resolution"] == "unresolved"


def test_confirmed_local_problem_restricts_region(monkeypatch):
    result = resolve_routing(
        "부산역 3번 승강장 에스컬레이터 고장입니다.",
        dict(
            location_candidate="부산역",
            routing_scope="확인필요",
            주요지코드="D1",
            업무기능후보=["시설"],
        ),
    )
    frame = pd.DataFrame(
        [
            dict(
                dept_scope="지역",
                dept_region_code=region,
                dept_business_function="시설",
            )
            for region in ["부산경남", "부산경남", "광주", "광주"]
        ]
    )
    monkeypatch.setattr(l, "history_df", frame, raising=False)
    pool, note = restrict_routing_candidates(result)
    assert len(pool) == 2 and set(pool.dept_region_code) == {"부산경남"}


def test_clear_topic_contradictions_guard_confirmed_recommendation():
    text = "동대구역 화장실에 휴지가 없고 세면대가 물바다입니다."
    analysis = resolve_routing(
        text,
        dict(location_candidate="동대구역", routing_scope="확인필요", 주요지코드="A1"),
    )
    assert analysis["semantic_issues"]
    rec = recommendation_guard(
        analysis,
        dict(status="추천가능", recommended_department="수송처", reason="높은 점수"),
        [dict(region_code="전국")],
    )
    assert (
        rec["status"] == "추천보류"
        and rec["recommended_department"] is None
        and rec["candidate_role"] == "reference"
    )


def test_unresolved_fallback_always_reference():
    rec = recommendation_guard(
        dict(routing_resolution="unresolved"),
        dict(
            status="추천가능", recommended_department="광주 시설처", reason="근거10건"
        ),
        [],
    )
    assert rec["status"] == "추천보류" and rec["candidate_role"] == "reference"


def test_topic_semantic_retry_and_persistent_review(monkeypatch):
    service = Service.__new__(Service)
    calls = []

    def generate(prompt, tokens):
        calls.append(prompt)
        return json.dumps(
            dict(
                main_topic_code="A1",
                sub_topic_code=None,
                keywords=["화장실", "휴지", "청결"],
                target="화장실",
                problem="휴지 없음",
                evidence="휴지가 없습니다",
            ),
            ensure_ascii=False,
        )

    monkeypatch.setattr(l, "qwen_generate", generate, raising=False)
    raw = {}
    result = service.analyzed_stage(
        "topic",
        lambda: l.analyze_topic("화장실에 휴지가 없습니다"),
        raw,
        "화장실에 휴지가 없습니다",
    )
    assert len(calls) == 2 and result["semantic_issues"]
    assert len(raw["semantic_validation_errors"]) == 2
    assert l.qwen_generate is generate


def test_valid_topic_with_literal_evidence_passes():
    analysis = dict(
        주요지코드="D2",
        핵심대상="화장실",
        문제상태="휴지 없음",
        요지원문근거="휴지가 없습니다",
    )
    assert (
        topic_issues("화장실에 휴지가 없습니다", analysis, require_evidence=True) == []
    )


def test_station_counter_evidence_overrides_wrong_model_departure_role():
    result = resolve_routing(
        "대전역 매표소 직원이 한숨 쉬며 면박을 줬습니다.",
        dict(
            location_candidate="대전역",
            location_role="departure",
            routing_scope="확인필요",
            주요지코드="F1",
        ),
    )
    assert result["location_role"] == "incident" and result["routing_scope"] == "지역형"
    assert result["관할본부"] == "대전충남본부"


def test_station_prefix_does_not_match_university():
    result = resolve_routing(
        "서울대학교 화장실 청결이 불량합니다.",
        dict(
            location_candidate="서울",
            location_role="incident",
            routing_scope="지역형",
            주요지코드="D2",
        ),
    )
    assert result["location_candidate"] is None and result["관할본부"] is None


def test_history_cache_revalidation_restores_original_routing(tmp_path, monkeypatch):
    import numpy as np
    from dataclasses import replace
    from backend import service as service_module
    from backend.decision import Store

    sample = l.df.iloc[[0]].copy()
    sample["데이터역할"] = "검색이력"
    sample["민원내용"] = "부산역 승강장 에스컬레이터가 고장났습니다."
    monkeypatch.setattr(l, "df", sample)
    monkeypatch.setattr(l, "history_df", pd.DataFrame(), raising=False)
    monkeypatch.setattr(l, "history_embeddings", np.zeros((0, 384)), raising=False)
    monkeypatch.setattr(
        service_module, "settings", replace(service_module.settings, output=tmp_path)
    )
    service = Service.__new__(Service)
    service.store = Store(tmp_path / "test.db")
    service.signature = "new"
    service.legacy_signatures = ["old"]
    service.embedding = type(
        "Embedding",
        (),
        {"encode": lambda self, texts, **kw: np.zeros((len(texts), 384))},
    )()
    service.store.record_recommendation(
        sample.iloc[0]["번호"],
        "old",
        {
            "analysis": {
                "분석상태": "분석완료",
                "주요지코드": "D1",
                "location_candidate": None,
                "routing_scope": "확인필요",
            },
            "raw": {
                "routing": json.dumps(
                    {
                        "location_candidate": "부산역",
                        "location_role": "departure",
                        "routing_scope": "확인필요",
                        "reason": "역 현장 문제",
                    },
                    ensure_ascii=False,
                )
            },
        },
    )
    service.rebuild_index()
    migrated = service.store.analysis(sample.iloc[0]["번호"], "new")["analysis"]
    assert (
        migrated["location_candidate"] == "부산역"
        and migrated["routing_scope"] == "지역형"
    )
    assert service.history_progress == 1
