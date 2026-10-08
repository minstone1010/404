import threading
from types import SimpleNamespace
import pandas as pd
from fastapi.testclient import TestClient
from backend.service import Service
from backend.decision import Store
from backend import notebook_logic as logic
from backend import main


def test_reads_and_evaluation_do_not_publish_manual_results(tmp_path, monkeypatch):
    s = Service.__new__(Service)
    s.store = Store(tmp_path / "isolated.sqlite3")
    s.signature = "test"
    s.lock = threading.RLock()
    s.history_complete = False
    s.history_preparation_done = False
    s.history_failed = 0
    s.row = lambda id: dict(
        번호=id,
        subject="분실물 시험",
        민원내용="열차에 백팩을 두고 내렸습니다",
        intake_channel="STN",
        데이터역할="검토대상",
        중복그룹=id,
    )
    s.parse_channel = lambda value: dict(label="역 접점(서면)", raw=value)
    calls = []

    def analyze(row, force=False):
        calls.append(force)
        result = dict(
            id=row["번호"],
            analysis={"분석상태": "분석완료", "주요지코드": "G3", "주요지": "유실물"},
            analysis_seconds=0.01,
        )
        s.store.record_recommendation(row["번호"], s.signature, result)
        return result

    s.analyze = analyze
    team = logic.department_master.loc[
        logic.department_master.routing_enabled, "department"
    ].iloc[0]
    s.teams = [team]
    recommendation = dict(
        recommended_department=team,
        status="추천가능",
        reason="시험 근거",
        top_departments=pd.DataFrame(
            [dict(department=team, count=2, score=0.8, mean_similarity=0.8)]
        ),
        similar_vocs=pd.DataFrame(
            columns=["번호", "handling_team", "similarity", "민원내용"]
        ),
    )
    monkeypatch.setattr(
        logic, "history_df", pd.DataFrame([{"번호": "history"}]), raising=False
    )
    monkeypatch.setattr(logic, "recommend_department", lambda row: recommendation)
    monkeypatch.setattr(
        "backend.service.dual_recommend", lambda service, row: recommendation
    )
    monkeypatch.setattr(
        logic,
        "restrict_routing_candidates",
        lambda row: (logic.history_df, "시험"),
        raising=False,
    )
    monkeypatch.setattr(main, "Service", lambda: s)
    monkeypatch.setattr(
        main, "settings", SimpleNamespace(startup_models=False, split_mode="holdout")
    )
    id = "900001"
    legacy = {
        "analysis": {"분석상태": "분석완료", "주요지": "이전 평가 결과"},
        "recommendation": {"status": "추천가능"},
        "ranking": [],
    }
    s.store.record_recommendation(id, s.signature, legacy)
    with TestClient(main.app) as c:
        for route in [
            "/api/vocs",
            "/api/vocs/" + id,
            "/api/vocs/" + id + "/recommendations",
        ]:
            assert c.get(route).status_code == 200
        detail = c.get("/api/vocs/" + id).json()
        assert (
            detail["status"] == "분석대기"
            and detail["result"] == {}
            and detail["recs"] == []
        )
        assert calls == []
        assert (
            c.post(
                "/api/vocs/" + id + "/decision",
                json={"status": "승인완료", "department": team},
            ).status_code
            == 422
        )
        assert s.store.analysis(id, s.signature) == legacy
        assert c.post("/api/evaluate", params={"limit": 1}).status_code == 200
        assert s.store.manual_analysis(id, s.signature) is None
        assert c.get("/api/vocs/" + id).json()["status"] == "분석대기"
        calls.clear()
        result = c.post("/api/vocs/" + id + "/analyze").json()
        assert calls == [True] and result["execution_source"] == "manual"
        persisted = s.store.manual_analysis(id, s.signature)
        assert c.get("/api/vocs/" + id).json()["result"] == persisted
        assert calls == [True]
        assert c.post("/api/evaluate", params={"limit": 1}).status_code == 200
        assert s.store.manual_analysis(id, s.signature) == persisted
        assert (
            c.post(
                "/api/vocs/" + id + "/decision",
                json={"status": "승인완료", "department": team},
            ).status_code
            == 200
        )
        assert c.get("/api/vocs/" + id).json()["status"] == "승인완료"
        before = len(calls)
        c.post("/api/vocs/" + id + "/analyze")
        assert calls[before:] == [True]


def test_failed_manual_rerun_replaces_old_display_result(tmp_path, monkeypatch):
    s = Service.__new__(Service)
    s.store = Store(tmp_path / "failure.sqlite3")
    s.signature = "test"
    s.lock = threading.RLock()
    s.row = lambda id: dict(번호=id, 데이터역할="검토대상")
    s.analyze = lambda row, force: dict(
        id=row["번호"],
        analysis={"분석상태": "분석오류"},
        failed_stage="topic",
        error="모델 추론 실패",
    )
    monkeypatch.setattr(
        logic, "history_df", pd.DataFrame([{"번호": "history"}]), raising=False
    )
    s.store.save_manual_analysis(
        "1",
        s.signature,
        {
            "analysis": {"분석상태": "분석완료"},
            "recommendation": {"status": "추천가능"},
        },
    )
    result = s.recommend("1", mode="A", force=True, source="manual")
    assert (
        result["analysis"]["분석상태"] == "분석오류"
        and result["execution_source"] == "manual"
    )
    assert s.store.manual_analysis("1", s.signature) == result
    assert "recommendation" not in result
