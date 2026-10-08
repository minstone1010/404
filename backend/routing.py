from backend import notebook_logic as logic
from backend.config import settings


def department_eligibility(analysis, department):
    """Master-only compatibility, independent of similarity or historical frequency."""
    matched = logic.department_master.loc[
        logic.department_master.department.eq(department)
    ]
    if len(matched) != 1:
        return dict(eligible=False, reasons=["부서 Master 미매칭/중복"])
    item = matched.iloc[0]
    reasons = []
    if not item.routing_enabled:
        reasons.append("라우팅 비활성 부서")
    scope = analysis.get("routing_scope")
    if scope == "지역형":
        region = analysis.get("관할지역코드")
        if not region or analysis.get("routing_resolution") == "unresolved":
            reasons.append("사건 관할 미확정")
        elif item.scope != "지역" or item.region_code != region:
            reasons.append("확정 지역/scope 불일치")
    elif scope == "전국형":
        if item.scope not in ["전국", "광역/전국", "본사"]:
            reasons.append("전국/scope 불일치")
    else:
        reasons.append("scope 미확정")
    choices = analysis.get("업무기능후보", [])
    if not choices or analysis.get("semantic_issues"):
        reasons.append("업무기능 미확정")
    elif item.business_function not in choices:
        reasons.append("확정 업무기능 불일치")
    return dict(eligible=not reasons, reasons=reasons)


def restrict_routing_candidates(row):
    pool = logic.history_df
    choices = row.get("업무기능후보", [])
    scope, region = row.get("routing_scope"), row.get("관할지역코드")
    active = logic.department_master.loc[
        logic.department_master.routing_enabled.eq(True)
    ]
    if choices and not active.business_function.isin(choices).any():
        empty = pool.iloc[:0].copy()
        empty.attrs["routing_constraints"] = dict(
            stage="mapping_gap",
            mapping_gap=True,
            reference_only=True,
            scope=scope,
            region=region,
            business_functions=choices,
            total_history=len(pool),
            candidate_count=0,
        )
        return (
            empty,
            "업무 Master 담당 부서 연결 없음: "
            + ", ".join(choices)
            + " | 직원/승무원 소속 확인 필요",
        )
    if row.get("semantic_issues"):
        empty = pool.iloc[:0].copy()
        empty.attrs["routing_constraints"] = dict(
            stage="semantic_review",
            reference_only=True,
            scope=scope,
            region=region,
            business_functions=choices,
            total_history=len(pool),
            candidate_count=0,
        )
        return empty, "원문 의미/근거 검증 실패: 분석 재검토 전 부서 후보 검색하지 않음"
    base = pool
    scope_resolved = False
    note = "전체 후보 fallback"
    if scope == "지역형" and row.get("위치매핑상태") == "매핑완료" and region:
        base = pool.loc[pool.dept_scope.eq("지역") & pool.dept_region_code.eq(region)]
        scope_resolved = True
        note = "지역 제한: " + str(row.get("관할본부"))
    elif scope == "전국형":
        base = pool.loc[pool.dept_scope.isin(["전국", "광역/전국", "본사"])]
        scope_resolved = True
        note = "범위 제한: 본사/전국"
    elif scope == "지역형":
        note = "Master 미매칭: 지역 미확정, 업무기능 fallback"
    preferred = (
        base.loc[base.dept_business_function.isin(choices)]
        if choices
        else base.iloc[:0]
    )
    # Even a single exact candidate is retained. Weak support is handled by the guard,
    # never by silently adding departments with an incompatible business function.
    if not preferred.empty:
        selected, stage = preferred, "strict" if scope_resolved else "function_only"
        note += " | 업무기능: " + ", ".join(choices)
    elif not base.empty:
        selected, stage = base, "scope_only" if scope_resolved else "full"
        note += " | 기능 후보 부족/불명확: 동일 지역/scope 유지"
    else:
        preferred = (
            pool.loc[pool.dept_business_function.isin(choices)]
            if choices
            else pool.iloc[:0]
        )
        selected, stage = (
            (preferred, "function_only") if not preferred.empty else (pool, "full")
        )
        note += (
            " | 동일 범위 이력 없음: 업무기능 fallback"
            if not preferred.empty
            else " | 검색 가능한 전체 이력 fallback"
        )
    selected = selected.copy()
    selected.attrs["routing_constraints"] = dict(
        stage=stage,
        reference_only=stage != "strict",
        scope=scope,
        region=region,
        business_functions=choices,
        total_history=len(pool),
        candidate_count=len(selected),
        scope_resolved=scope_resolved,
        function_resolved=bool(choices),
    )
    return selected, note
