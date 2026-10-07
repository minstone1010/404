import json
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.analytics.config import AnalyticsConfig
from backend.analytics.topic_trend import trends
from backend.analytics.topic_validation import warnings
from backend.analytics.topic_discovery import discover
from backend.analytics import bertopic_service as batch
from backend.decision import Store


def test_config_rejects_nan_and_bad_cluster():
    with pytest.raises(ValueError):
        replace(AnalyticsConfig(), dominant_ratio=float("nan")).validate()
    with pytest.raises(ValueError):
        replace(AnalyticsConfig(), min_cluster_size=1).validate()


def test_fingerprint_changes_with_model_data_and_config(tmp_path, monkeypatch):
    data = tmp_path / "data.xlsx"
    data.write_bytes(b"data")
    fake = SimpleNamespace(
        voc_path=data,
        embedding_model="model-a",
        split_mode="holdout",
        history_fraction=0.8,
    )
    monkeypatch.setattr(batch, "settings", fake)
    config = AnalyticsConfig()
    first = batch.fingerprint(config)
    assert first != batch.fingerprint(
        replace(config, min_cluster_size=config.min_cluster_size + 1)
    )
    fake.embedding_model = "model-b"
    assert first != batch.fingerprint(config)
    fake.embedding_model = "model-a"
    data.write_bytes(b"new")
    assert first != batch.fingerprint(config)


def test_raw_and_unique_counts_and_korean_words():
    frame = pd.DataFrame(
        [
            dict(
                id="1",
                case_group_id="a",
                text="충전 콘센트 오류",
                source_topic_code="Z1",
                role="검색이력",
                date=None,
            ),
            dict(
                id="2",
                case_group_id="a",
                text="충전 콘센트 오류",
                source_topic_code="Z1",
                role="검색이력",
                date=None,
            ),
            dict(
                id="3",
                case_group_id="b",
                text="충전 용량 부족",
                source_topic_code="Z1",
                role="검토대상",
                date=None,
            ),
        ]
    )
    representatives = frame.drop_duplicates("case_group_id").reset_index(drop=True)
    model = SimpleNamespace(get_topic=lambda t: [("충전", 0.5), ("콘센트", 0.4)])
    topics, mapping, metrics = discover(
        model, frame, representatives, np.array([[1.0, 0.0], [1.0, 0.0]]), [0, 0]
    )
    assert topics[0]["raw_document_count"] == 3 and topics[0]["unique_case_count"] == 2
    assert topics[0]["representative_words"][0] == "충전" and len(mapping) == 3
    assert metrics["outlier_ratio"] == 0


def test_trends_no_dates_and_dedup_new_topic():
    config = replace(AnalyticsConfig(), trend_days=30, trend_min_cases=2)
    assert (
        trends([dict(id="1", case_group_id="a", topic_id=0, date=None)], config)[
            "enabled"
        ]
        is False
    )
    rows = [
        dict(id="1", case_group_id="a", topic_id=0, date="2026-09-25"),
        dict(id="2", case_group_id="a", topic_id=0, date="2026-09-26"),
        dict(id="3", case_group_id="b", topic_id=0, date="2026-09-28"),
        dict(id="4", case_group_id="c", topic_id=1, date="2026-07-01"),
    ]
    topic = next(t for t in trends(rows, config)["topics"] if t["topic_id"] == 0)
    assert (
        topic["recent_count"] == 2
        and topic["new_topic"]
        and topic["growth_rate"] is None
    )


def test_warning_excludes_target_labels_duplicate_groups_and_stale_qwen(tmp_path):
    store = Store(tmp_path / "isolated.db")
    for id, sig in [("target", "current"), ("stale", "old")]:
        store.record_recommendation(
            id, sig, dict(analysis={"분석상태": "분석완료", "주요지코드": "D1"})
        )
    history = [
        dict(
            id=str(i),
            case_group_id=str(i),
            topic_id=0,
            source_topic_code="G3",
            role="검색이력",
        )
        for i in range(6)
    ]
    mapping = history + [
        dict(
            id="duplicate",
            case_group_id="0",
            topic_id=0,
            source_topic_code="D1",
            role="검색이력",
        ),
        dict(
            id="target",
            case_group_id="0",
            topic_id=0,
            source_topic_code="D1",
            role="검토대상",
        ),
        dict(
            id="stale",
            case_group_id="x",
            topic_id=0,
            source_topic_code="D1",
            role="검토대상",
        ),
    ]
    result = {"document_mapping": mapping}
    first = warnings(result, "current", store.path, AnalyticsConfig())
    assert (
        len(first) == 1
        and first[0]["reference_unique_cases"] == 5
        and first[0]["dominant_label"] == "G3"
    )
    mapping[-2]["source_topic_code"] = "Z1"
    assert first == warnings(result, "current", store.path, AnalyticsConfig())
    assert store.analysis("target", "current")["analysis"]["주요지코드"] == "D1"


def test_missing_current_cache_does_not_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(batch, "fingerprint", lambda c: "new")
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "all.json").write_text("{}")
    assert batch.current("all")["status"] == "not_built"


def test_analytics_failure_isolated_from_live_api(monkeypatch):
    from backend import main
    from backend.analytics import api

    monkeypatch.setattr(
        main,
        "Service",
        lambda: SimpleNamespace(detail=lambda id: dict(id=id, result={})),
    )
    monkeypatch.setattr(main, "settings", SimpleNamespace(startup_models=False))
    monkeypatch.setattr(
        api,
        "current",
        lambda mode: (_ for _ in ()).throw(RuntimeError("analytics unavailable")),
    )
    with TestClient(main.app) as client:
        assert client.get("/api/topics").status_code == 503
        assert client.get("/api/vocs/900001").status_code == 200


def test_bad_analytics_env_does_not_break_live_api(monkeypatch):
    from backend import main

    monkeypatch.setenv("BER_TOPIC_MIN_CLUSTER_SIZE", "bad-number")
    monkeypatch.setattr(
        main,
        "Service",
        lambda: SimpleNamespace(detail=lambda id: dict(id=id, result={})),
    )
    monkeypatch.setattr(main, "settings", SimpleNamespace(startup_models=False))
    with TestClient(main.app) as client:
        assert client.get("/api/topics").status_code == 503
        assert client.get("/api/vocs/900001").status_code == 200


def test_completed_batch_child_is_not_reported_as_running(tmp_path, monkeypatch):
    import subprocess, sys, time
    from backend.analytics import api

    process = subprocess.Popen([sys.executable, "-c", "pass"])
    monkeypatch.setattr(api, "_process", process)
    monkeypatch.setattr(api, "cache_root", lambda: tmp_path)
    (tmp_path / "job.json").write_text(
        json.dumps({"status": "completed", "mode": "both"})
    )
    (tmp_path / "launch.json").write_text(
        json.dumps({"status": "starting", "mode": "both", "pid": process.pid})
    )
    try:
        for _ in range(100):
            stat = __import__("pathlib").Path(f"/proc/{process.pid}/stat")
            if not stat.exists() or stat.read_text().split(")")[-1].split()[0] == "Z":
                break
            time.sleep(0.02)
        assert api.job()["status"] == "completed"
    finally:
        process.wait(timeout=5)
