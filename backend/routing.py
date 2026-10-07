from backend import notebook_logic as logic
from backend.config import settings


def restrict_routing_candidates(row):
    pool = logic.history_df
    choices = row.get("업무기능후보", [])
    scope = row.get("routing_scope")
    region = row.get("관할지역코드")
    base = pool
    note = "전체 후보 fallback"
    if scope == "지역형" and row.get("위치매핑상태") == "매핑완료" and region:
        base = pool.loc[pool.dept_scope.eq("지역") & pool.dept_region_code.eq(region)]
        note = "지역 제한: " + str(row.get("관할본부"))
    elif scope == "전국형":
        base = pool.loc[pool.dept_scope.isin(["전국", "광역/전국", "본사"])]
        note = "범위 제한: 본사/전국"
    elif scope == "지역형":
        note = "Master 미매칭: 지역 미확정, 업무기능 fallback"
    if choices:
        preferred = base.loc[base.dept_business_function.isin(choices)]
        if len(preferred) >= settings.min_support:
            return preferred, note + " | 업무기능: " + ", ".join(choices)
    if not base.empty:
        return base, note + " | 기능 후보 부족/불명확: 동일 지역/scope 유지"
    preferred = (
        pool.loc[pool.dept_business_function.isin(choices)]
        if choices
        else pool.iloc[:0]
    )
    if not preferred.empty:
        return preferred, note + " | 동일 범위 이력 없음: 업무기능 fallback"
    return pool, note + " | 검색 가능한 전체 이력 fallback"
