import json
import pytest
from backend import notebook_logic as logic
from backend.semantic import topic_issues
from backend.cause_validation import cause_issues, review_cause
from backend.service import Service

BUG = "무궁화호 객실에 바퀴벌레가 있었습니다. 아이가 울고 다른 자리로 옮겼습니다. 소독은 하는 건가요?"


def test_wrong_staff_topic_rejected_but_environment_allowed():
    assert topic_issues(BUG, {"주요지코드": "F2"})
    assert not topic_issues(BUG, {"주요지코드": "E3"})
    assert not topic_issues(
        "바퀴벌레를 신고했는데 승무원이 무시했습니다.", {"주요지코드": "F2"}
    )
    assert not topic_issues(
        "승무원님이 의료진을 찾아주셔서 감사드립니다.", {"주요지코드": "F2"}
    )


def test_hallucinated_actor_and_question_as_fact_rejected():
    a = {"인적요인": 1, "발생원인_판단이유": "승무원이 기겁하고 자리를 옮겼습니다."}
    assert any("행동 주체" in x for x in cause_issues(BUG, a))
    a = {
        "cause_claims": [
            {
                "subject": "확인불가",
                "action": "소독은 하는 건가요",
                "evidence": "소독은 하는 건가요?",
                "certainty": "confirmed",
            }
        ]
    }
    assert any("질문/추측" in x for x in cause_issues(BUG, a))


def test_claim_actor_must_belong_to_quoted_action():
    a = {
        "발생원인_판단이유": "직원 행동",
        "cause_claims": [
            {
                "subject": "승무원",
                "action": "울고",
                "evidence": "아이가 울고 다른 자리로 옮겼습니다.",
                "certainty": "inferred",
            }
        ],
    }
    assert any("행동 주체" in x for x in cause_issues(BUG, a))


def test_valid_observation_with_unknown_root_cause():
    a = {
        "인적요인": 0,
        "물적요인": 1,
        "기타": 0,
        "cause_certainty": "unknown",
        "발생원인_판단이유": "객실 벌레 발생이 확인되나 발생 원인은 불명입니다.",
        "cause_claims": [
            {
                "subject": "확인불가",
                "action": "바퀴벌레가 있었습니다",
                "evidence": "무궁화호 객실에 바퀴벌레가 있었습니다.",
                "certainty": "confirmed",
            }
        ],
    }
    assert not cause_issues(BUG, a)


def test_failed_cause_is_not_zero_or_search_input():
    a = review_cause(
        {"인적요인": 1, "발생원인_판단이유": "승무원이 도망갔습니다."}, ["주체 오류"]
    )
    assert a["인적요인"] is None
    assert a["cause_original"]["인적요인"] == 1
    assert logic.cause_text({**a, "분석상태": "분석완료"}) == ""
    embedded = logic.embedding_text(
        {**a, "분석상태": "분석완료", "민원내용": BUG, "주요지": "차내 환경"}
    )
    assert "도망" not in embedded and "차내 환경" in embedded


def test_cause_semantic_retry_then_recovery(monkeypatch):
    svc = Service.__new__(Service)
    calls = []

    def generate(prompt, tokens):
        calls.append(prompt)
        value = {
            "human_factor": 0,
            "material_factor": 1,
            "other_factor": 0,
            "reason": "객실에 벌레가 있으나 발생 원인은 불명입니다.",
            "cause_certainty": "unknown",
            "claims": [
                {
                    "subject": "확인불가",
                    "action": "바퀴벌레가 있었습니다",
                    "evidence": "무궁화호 객실에 바퀴벌레가 있었습니다.",
                    "certainty": "confirmed",
                }
            ],
        }
        if len(calls) == 1:
            value["human_factor"] = 1
            value["reason"] = "승무원이 기겁하고 자리를 옮겼습니다."
        return json.dumps(value, ensure_ascii=False)

    monkeypatch.setattr(logic, "qwen_generate", generate, raising=False)
    raw = {}
    a = svc.analyzed_stage("cause", lambda: logic.qwen_generate("분석", 384), raw, BUG)
    assert len(calls) == 2 and not cause_issues(BUG, a)
    assert raw["semantic_validation_errors"][0]["stage"] == "cause"


def test_cause_persistent_failure_preserves_failure_and_original(monkeypatch):
    svc = Service.__new__(Service)
    value = json.dumps(
        {
            "human_factor": 1,
            "material_factor": 0,
            "other_factor": 0,
            "reason": "승무원이 기겁했습니다.",
            "cause_certainty": "confirmed",
            "claims": [],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(logic, "qwen_generate", lambda *a: value, raising=False)
    raw = {}
    a = svc.analyzed_stage("cause", lambda: logic.qwen_generate("", 384), raw, BUG)
    assert a["cause_analysis_status"] == "review_required" and a["인적요인"] is None
    assert len(raw["semantic_validation_errors"]) == 2


def test_malformed_cause_json_is_isolated(monkeypatch):
    svc = Service.__new__(Service)
    monkeypatch.setattr(logic, "qwen_generate", lambda *a: "invalid", raising=False)
    a = svc.analyzed_stage("cause", lambda: logic.qwen_generate("", 384), {}, BUG)
    assert a["cause_analysis_status"] == "review_required"
    assert a["발생원인_판단이유"].startswith("원인 확인 필요")


def test_cause_claims_schema_rejects_missing_fields():
    raw = json.dumps(
        {
            "human_factor": 0,
            "material_factor": 1,
            "other_factor": 0,
            "reason": "벌레",
            "claims": [{"subject": "열차"}],
        }
    )
    with pytest.raises(ValueError):
        logic.parse_cause(raw)


def test_cause_inference_exception_does_not_discard_valid_topic(monkeypatch):
    svc = Service.__new__(Service)
    svc.signature = "test"
    svc.store = type(
        "Store",
        (),
        {"analysis": lambda *a: None, "record_recommendation": lambda *a: None},
    )()

    def stage(name, *args):
        if name == "cause":
            raise RuntimeError("inference failed")
        if name == "topic":
            return {
                "주요지코드": "E3",
                "주요지": "차내 환경",
                "부요지": None,
                "voc_intent": "불만",
                "핵심키워드": "벌레, 위생, 객실",
            }
        return {
            "location_candidate": None,
            "routing_scope": "확인필요",
            "location_role": "unknown",
        }

    monkeypatch.setattr(svc, "analyzed_stage", stage)
    result = svc.analyze({"번호": "test", "민원내용": BUG})
    assert result["analysis"]["분석상태"] == "분석완료"
    assert result["analysis"]["주요지코드"] == "E3"
    assert result["analysis"]["cause_analysis_status"] == "review_required"
    assert result["analysis"]["인적요인"] is None
    assert "RuntimeError" in result["raw"]["cause_inference_error"]


def test_evidence_ids_bind_original_typos_and_reject_invalid_ids():
    from backend.source_evidence import bind_evidence

    raw = json.dumps(
        {
            "main_topic_code": "E3",
            "evidence_id": 2,
            "intent_evidence_id": 2,
            "evidence": "수정된 문장",
        }
    )
    original = "제목\n무궁화호 좌걱에 바퀴벌레가 기어다 녔습니다"
    bound = json.loads(bind_evidence(raw, original, "topic"))
    assert bound["evidence"] == original.split("\n")[1]
    assert json.loads(raw)["evidence"] == "수정된 문장"
    for bad in [0, 3, True, "2"]:
        with pytest.raises(ValueError):
            bind_evidence(json.dumps({"evidence_id": bad}), original, "topic")


def test_history_migration_preserves_persistent_topic_failure(tmp_path, monkeypatch):
    import pandas as pd
    from backend.decision import Store

    frame = logic.df.iloc[[0]].copy()
    frame["데이터역할"] = "검색이력"
    frame["민원내용"] = BUG
    monkeypatch.setattr(logic, "df", frame)
    svc = Service.__new__(Service)
    svc.signature = "new"
    svc.legacy_signatures = ["old"]
    svc.store = Store(tmp_path / "test.sqlite3")
    svc.store.record_recommendation(
        frame.iloc[0]["번호"],
        "old",
        {
            "analysis": {
                "분석상태": "분석완료",
                "주요지코드": "E3",
                "semantic_issues": [],
                "location_candidate": None,
                "routing_scope": "확인필요",
            },
            "raw": {
                "semantic_validation_errors": [
                    {
                        "stage": "topic",
                        "attempt": 2,
                        "issues": ["요지 근거가 원문에 없음"],
                    },
                    {"stage": "cause", "attempt": 2, "issues": ["원인 주장 오류"]},
                ]
            },
        },
    )
    svc.rebuild_index()
    saved = svc.store.analysis(frame.iloc[0]["번호"], "new")["analysis"]
    assert saved["semantic_issues"] == ["요지 근거가 원문에 없음"]
    assert svc.history_quality_excluded == 1 and svc.history_progress == 0
