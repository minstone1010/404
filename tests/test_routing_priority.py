import pandas as pd
from backend import notebook_logic as logic
from backend.routing import restrict_routing_candidates, department_eligibility
from backend.semantic import recommendation_guard


def test_sparse_exact_function_is_not_diluted(monkeypatch):
    monkeypatch.setattr(
        logic,
        "history_df",
        pd.DataFrame(
            [
                dict(dept_scope="지역", dept_region_code="R", dept_business_function=f)
                for f in ["시설", "여객", "여객", "여객"]
            ]
        ),
        raising=False,
    )
    pool, _ = restrict_routing_candidates(
        dict(
            routing_scope="지역형",
            위치매핑상태="매핑완료",
            관할지역코드="R",
            업무기능후보=["시설"],
        )
    )
    assert len(pool) == 1
    assert pool.attrs["routing_constraints"]["stage"] == "strict"


def test_scope_only_is_reference_even_with_strong_similarity(monkeypatch):
    monkeypatch.setattr(
        logic,
        "history_df",
        pd.DataFrame(
            [
                dict(
                    dept_scope="지역",
                    dept_region_code="R",
                    dept_business_function="여객",
                )
            ]
        ),
        raising=False,
    )
    pool, _ = restrict_routing_candidates(
        dict(
            routing_scope="지역형",
            위치매핑상태="매핑완료",
            관할지역코드="R",
            업무기능후보=["시설"],
        )
    )
    rec = recommendation_guard(
        dict(routing_resolution="resolved"),
        dict(
            status="추천가능",
            recommended_department="X",
            routing_constraints=pool.attrs["routing_constraints"],
        ),
        [],
        mode="B",
    )
    assert rec["status"] == "추천보류" and rec["candidate_role"] == "reference"


def test_master_constraints_overrule_similarity(monkeypatch):
    monkeypatch.setattr(
        logic,
        "department_master",
        pd.DataFrame(
            [
                dict(
                    department=name,
                    routing_enabled=True,
                    region_code=region,
                    business_function=fn,
                    scope=scope,
                )
                for name, region, fn, scope in [
                    ("ok", "R", "시설", "지역"),
                    ("wrong_region", "S", "시설", "지역"),
                    ("wrong_function", "R", "여객", "지역"),
                    ("national", "전국", "시설", "전국"),
                ]
            ]
        ),
        raising=False,
    )
    a = dict(
        routing_scope="지역형",
        관할지역코드="R",
        routing_resolution="resolved",
        업무기능후보=["시설"],
    )
    assert department_eligibility(a, "ok")["eligible"]
    for name in ["wrong_region", "wrong_function", "national", "missing"]:
        assert not department_eligibility(a, name)["eligible"]
        rec = recommendation_guard(
            a,
            dict(status="추천가능", recommended_department=name),
            [dict(department=name, region_code="R")],
        )
        assert rec["recommended_department"] is None
    nationwide = {**a, "routing_scope": "전국형"}
    assert department_eligibility(nationwide, "national")["eligible"]
    assert not department_eligibility(nationwide, "ok")["eligible"]


def test_evidence_hold_is_never_presented_as_recommendation():
    rec = recommendation_guard(
        dict(routing_resolution="resolved"), dict(status="추천보류"), [], mode="B"
    )
    assert rec["candidate_role"] == "reference"


def test_incomplete_master_mapping_is_identified(monkeypatch):
    monkeypatch.setattr(
        logic,
        "department_master",
        pd.DataFrame(
            [
                dict(
                    department="시설처",
                    parent_org="본부",
                    region_code="",
                    business_function="시설",
                    scope="지역",
                    routing_enabled=True,
                ),
                dict(
                    department="비활성",
                    parent_org="본부",
                    region_code="R",
                    business_function="시설",
                    scope="지역",
                    routing_enabled=False,
                ),
            ]
        ),
    )
    frame = logic.attach_department_attributes(
        pd.DataFrame({"handling_team": ["시설처", "비활성", "미등록"]})
    )
    assert frame.dept_mapping_status.tolist() == [
        "Master 속성 불완전",
        "라우팅 비활성",
        "Master 미등록",
    ]
    assert frame.handling_team.tolist() == ["시설처", "비활성", "미등록"]
