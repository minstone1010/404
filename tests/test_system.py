import json
import numpy as np
import pandas as pd
import pytest
from backend import notebook_logic as l
from backend.validation import validate
from backend.decision import Store
from backend.routing import restrict_routing_candidates
from backend.service import Service


def test_holdout_groups():
    assert len(l.df) == 2500
    assert l.df.groupby("중복그룹").데이터역할.nunique().max() == 1
    s = Service()
    row = s.row(l.df.번호.iloc[0])
    assert (
        not {
            "handling_team",
            "topic_code",
            "topic_code_secondary",
            "origin_station",
            "destination_station",
        }
        & row.keys()
    )


def test_strict_nulls():
    base = {
        "main_topic_code": "D1",
        "sub_topic_code": None,
        "keywords": ["고장", "시설", "불편"],
    }
    assert validate(json.dumps(base), "topic")["부요지코드"] is None
    for value in ["null", "", 3]:
        with pytest.raises(ValueError):
            validate(json.dumps({**base, "sub_topic_code": value}), "topic")
    del base["sub_topic_code"]
    with pytest.raises(ValueError):
        validate(json.dumps(base), "topic")
    for value in [True, None, "0"]:
        with pytest.raises(ValueError):
            validate(
                json.dumps(
                    {
                        "human_factor": value,
                        "material_factor": 0,
                        "other_factor": 1,
                        "reason": "제도",
                    }
                ),
                "cause",
            )


def test_master_and_channel():
    assert l.lookup_location("수원역")["관할본부"] == "수도권서부본부"
    assert l.lookup_location("없는역")["위치매핑상태"] == "미매핑"
    assert l.lookup_location("광주송정역")["표준위치"] == "광주송정역"
    s = Service()
    assert s.parse_channel("APP")["label"] == "코레일톡 앱"
    assert s.parse_channel("없는채널")["raw"] == "없는채널"
    assert s.parse_channel("")["status"] == "미입력"


def test_fallback_and_no_leak(monkeypatch):
    frame = pd.DataFrame(
        [
            dict(
                번호=str(i),
                handling_team=team,
                dept_scope=scope,
                dept_region_code=region,
                dept_business_function=fn,
                중복그룹=str(i),
                민원내용="과거" + str(i),
                분석상태="분석완료",
            )
            for i, (team, scope, region, fn) in enumerate(
                [
                    ("지역시설", "지역", "서부", "시설"),
                    ("지역시설", "지역", "서부", "시설"),
                    ("본사IT", "본사", "", "IT"),
                ]
            )
        ]
    )
    monkeypatch.setattr(l, "history_df", frame, raising=False)
    row = {
        "routing_scope": "지역형",
        "위치매핑상태": "미매핑",
        "업무기능후보": ["시설"],
    }
    pool, note = restrict_routing_candidates(row)
    assert len(pool) == 2 and "미매칭" in note
    row = {"routing_scope": "전국형", "업무기능후보": ["시설"]}
    pool, note = restrict_routing_candidates(row)
    assert pool.handling_team.tolist() == ["본사IT"]
    row = {
        "routing_scope": "지역형",
        "位": "x",
        "위치매핑상태": "매핑완료",
        "관할지역코드": "서부",
        "업무기능후보": ["IT"],
    }
    pool, note = restrict_routing_candidates(row)
    assert len(pool) == 2
    assert (
        l.rank_departments(frame.assign(similarity=[0.9, 0.8, 0.7])).iloc[0].department
        == "지역시설"
    )


def test_decision_persistence(tmp_path):
    path = tmp_path / "test.sqlite3"
    s = Store(path)
    assert s.load_approvals() == {}
    with pytest.raises(ValueError):
        s.save_decision("1", "없는부서", "승인완료", "", ["시설"], "시설", "sig")
    s.save_decision("1", "시설", "승인완료", "검토", ["시설"], "시설", "sig")
    assert Store(path).load_approvals()["1"]["department"] == "시설"
    s.save_decision("1", "시설", "보류", "추가확인", ["시설"], "시설", "sig")
    assert Store(path).load_approvals()["1"]["department"] == ""
    with s.connect() as db:
        assert db.execute("SELECT count(*) FROM decision_events").fetchone()[0] == 2


def test_validation_retry_records_raw(monkeypatch):
    s = Service.__new__(Service)
    calls = []

    def generate(prompt, tokens):
        calls.append(prompt)
        return (
            '{"main_topic_code":"D1","sub_topic_code":"D1","keywords":["고장","시설","불편"]}'
            if len(calls) == 1
            else '{"main_topic_code":"D1","sub_topic_code":null,"keywords":["고장","시설","불편"]}'
        )

    monkeypatch.setattr(l, "qwen_generate", generate)
    raw = {}
    output = s.analyzed_stage(
        "topic", lambda: l.qwen_generate("원문 프롬프트", 128), raw
    )
    assert output["부요지코드"] is None
    assert len(raw["validation_errors"]) == 1
    assert "재시도 검증 오류" in calls[1]
    assert l.qwen_generate is generate
