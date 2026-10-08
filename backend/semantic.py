"""Conservative source-grounded checks; never generate labels or organisations."""

import re
from backend import notebook_logic as logic

VERSION = "semantic-routing-v5-evidence-r2"
LOCAL_CONTEXT = re.compile(
    r"에스컬|엘리베이터|승강장|화장실|대합실|매표소|역무원|흡연|광장|개찰구|역직원|주차장"
)
TRAIN_CONTEXT = re.compile(
    r"열차\s*(?:안|내)|객실|[가-힣]+호\s*(?:탔|에서)|기차\s*(?:안|내)|승무원"
)
DELAY = re.compile(r"지연|연착|늦게\s*(?:도착|출발)|출발.*늦|도착.*늦|운행.*늦")
CONCRETE = re.compile(
    r"에어컨|냉방|난방|화장실|휴지|세면대|에스컬|엘리베이터|유실물|분실|두고\s*내"
)


def compact(text):
    return re.sub(r"\s+", "", logic.clean_text(text)).casefold()


def mentioned(location, text):
    location = logic.clean_text(location)
    if not location:
        return False
    suffix = r"(?=$|[\s\d.,!?\n]|에서|으로|까지|에서|에|의|을|를|은|는|광장|승강장|화장실|매표소|대합실|출입구|개찰구|앞)"
    return bool(re.search(re.escape(location) + suffix, text))


def topic_issues(text, analysis, require_evidence=False):
    issues = []
    if re.search(
        r"유실물|분실물|분실.{0,8}(확인|신고|찾|접수)|백팩.{0,12}두고", text
    ) and analysis.get("주요지코드") not in {"G3", None, ""}:
        issues.append("분실물 확인·접수 원문과 주요지 불일치: 요지 재검토 필요")
    if require_evidence:
        for field in ["핵심대상", "문제상태", "요지원문근거"]:
            if not isinstance(analysis.get(field), str) or not analysis[field].strip():
                issues.append(f"{field} 누락")
        evidence = analysis.get("요지원문근거")
        if evidence and compact(evidence) not in compact(text):
            issues.append("요지 근거가 원문에 없음")
    if require_evidence:
        for field in ["핵심대상", "문제상태"]:
            if analysis.get(field) in logic.CODEBOOK or analysis.get(
                field
            ) == analysis.get("주요지코드"):
                issues.append(field + "에 실제 내용 대신 코드 사용")
        if analysis.get("intent_evidence") and compact(
            analysis["intent_evidence"]
        ) not in compact(text):
            issues.append("의도 근거가 원문에 없음")
    if (
        analysis.get("voc_intent") == "칭찬"
        and re.search(r"무사히|덕분에", text)
        and re.search(
            r"치료.*못|대처하지|조치.*않|도움.*없", analysis.get("문제상태") or ""
        )
    ):
        issues.append("도움과 치료에 감사하는 원문을 도움/치료 실패로 요약함")
    if (
        require_evidence
        and analysis.get("voc_intent") == "칭찬"
        and analysis.get("intent_evidence")
        and not re.search(
            r"감사|칭찬|덕분|도와|배려|조치해|찾아\s*주|챙겨|친절",
            analysis["intent_evidence"],
        )
    ):
        issues.append(
            "칭찬 의도 근거에 감사·도움 행동이 없음: 배경 증상 대신 감사 표현을 원문 그대로 선택"
        )
    code = analysis.get("주요지코드")
    if (
        code == "F1"
        and "승무원" in text
        and not re.search(r"역직원|역무원|매표소.*직원", text)
    ):
        issues.append("열차 승무원 응대(F2)를 역직원 응대(F1)로 선택함")
    if code == "F2" and not re.search(r"승무원|차장|검표.*직원|열차.*직원", text):
        issues.append(
            "승무원 행동 근거 없이 승무원 응대(F2)로 분류: 객실 위생/환경이면 E3 검토"
        )
    if (
        code == "F2"
        and require_evidence
        and analysis.get("요지원문근거")
        and not re.search(r"승무원|차장|직원", analysis["요지원문근거"])
    ):
        issues.append("선택한 F2의 인용 근거에 승무원 응대 행동이 없음")
    if code == "A1" and CONCRETE.search(text) and not DELAY.search(text):
        issues.append("열차지연 근거 없이 시설·차량·분실 문제를 열차지연으로 분류")
    if (
        code == "D1"
        and re.search(r"유실물|분실|두고\s*내", text)
        and not re.search(r"에스컬|엘리베이터|승강설비", text)
    ):
        issues.append("분실 민원에 승강설비 근거가 없음")
    if (
        code == "B1"
        and re.search(r"한숨|면박|불친절|태도", text)
        and re.search(r"직원|매표소|역무원", text)
        and not re.search(r"환불.*(?:안|못)|결제.*오류|변경.*(?:불가|안\s*되)", text)
    ):
        issues.append(
            "직원 응대 문제보다 승차권 업무 언급을 주요지로 선택했는지 재검토 필요"
        )
    return issues


def normalise_location(candidate):
    # Only remove recognised station facility suffixes, never fuzzy-match station names.
    text = logic.clean_text(candidate)
    matched = re.fullmatch(
        r"(.+?역)\s*(?:\d+\s*번?\s*)?(?:광장|매표소|대합실|승강장|화장실|출입구|개찰구|주차장|앞|내부)(?:\s*쪽)?",
        text,
    )
    return matched.group(1) if matched else text


def resolve_routing(text, analysis):
    from backend.intent import enrich_intent

    result = enrich_intent(text, analysis)
    original = result.get("location_candidate")
    candidate = normalise_location(original)
    role = result.get("location_role", "unknown")
    notes = []
    grounded = mentioned(candidate, text)
    # Canonical location lookup is always a Master operation.
    attrs = logic.lookup_location(candidate)
    if not grounded and attrs.get("표준위치"):
        grounded = mentioned(attrs["표준위치"], text)
    if candidate and not grounded:
        notes.append("추출 위치가 원문에 없어 관할에 사용하지 않음")
        candidate = None
        role = "unknown"
        attrs = logic.lookup_location(None)
    if candidate:
        mentions = []
        for m in re.finditer(re.escape(candidate), text):
            clause = re.split(r"[。.!?\n]", text[max(0, m.start() - 35) : m.end() + 65])
            mentions.extend(clause)
        local = any(
            LOCAL_CONTEXT.search(x)
            and not (
                TRAIN_CONTEXT.search(x)
                and re.search(r"에서.{0,25}(?:가는|행|탔|타고)", x)
            )
            for x in mentions
        )
        route = bool(
            re.search(
                re.escape(candidate)
                + r".{0,20}(?:에서.{0,20}(?:가는|행|탔|타고)|까지|출발|도착)",
                text,
            )
        )
        if local:
            role = "incident"
            result["routing_scope"] = "지역형"
            notes.append("원문의 역 현장 문제를 근거로 지역형 확정")
        elif route or role in {"departure", "destination", "route"}:
            role = "route"
            candidate = None
            attrs = logic.lookup_location(None)
            notes.append("출발·도착·경로 위치는 사건 관할로 사용하지 않음")
            if result.get("routing_scope") == "지역형":
                result["routing_scope"] = "확인필요"
        elif role != "incident":
            candidate = None
            attrs = logic.lookup_location(None)
            notes.append("사건 장소 근거가 불충분하여 위치 미확정")
    scope = result.get("routing_scope", "확인필요")
    if scope == "전국형" and role == "incident":
        scope = "지역형"
    if scope == "전국형":
        candidate = None
        attrs = logic.lookup_location(None)
    result.update(attrs)
    result.update(
        location_candidate=candidate or None,
        location_candidate_raw=original,
        location_role=role,
        routing_scope=scope,
        routing_validation_notes=notes,
    )
    result["routing_resolution"] = (
        "resolved"
        if scope == "전국형"
        or scope == "지역형"
        and attrs.get("위치매핑상태") == "매핑완료"
        and role == "incident"
        else "unresolved"
    )
    intent_issues = result.get("semantic_issues", [])
    result["semantic_issues"] = topic_issues(text, result) + intent_issues
    result["semantic_issues"] = list(
        dict.fromkeys(analysis.get("semantic_issues", []) + result["semantic_issues"])
    )
    result["semantic_status"] = (
        "review_required" if result["semantic_issues"] else "passed"
    )
    return result


def recommendation_guard(analysis, recommendation, ranking, mode="C"):
    reasons = list(analysis.get("semantic_issues", []))
    constraints = recommendation.get("routing_constraints", {})
    if constraints.get("mapping_gap"):
        reasons.append("업무 Master 담당 부서 연결 없음 · 직원/승무원 소속 확인 필요")
    if analysis.get("voc_intent") == "복합":
        reasons.append("칭찬·불만이 혼재하여 의도 재검토 필요")
    if constraints.get("reference_only"):
        reasons.append("지역·업무·scope 조건을 모두 충족하지 못한 참고 검색")
    if mode == "C":
        from backend.routing import department_eligibility

        for candidate in ranking:
            check = department_eligibility(analysis, candidate.get("department"))
            candidate["routing_eligibility"] = check
        if ranking and not ranking[0]["routing_eligibility"]["eligible"]:
            reasons.extend(ranking[0]["routing_eligibility"]["reasons"])
    if analysis.get("routing_resolution") == "unresolved":
        reasons.append("사건 관할·범위 미확정")
    note = recommendation.get("routing_filter_info", "")
    if "동일 범위 이력 없음" in note or "검색 가능한 전체 이력 fallback" in note:
        reasons.append("관할 조건을 완화한 참고 검색 결과")
    region = analysis.get("관할지역코드")
    if (
        ranking
        and mode == "C"
        and analysis.get("routing_scope") == "지역형"
        and region
        and ranking[0].get("region_code") != region
    ):
        reasons.append("1순위 후보가 확정 관할과 불일치")
    if reasons:
        recommendation.update(
            status="추천보류",
            recommended_department=None,
            candidate_role="reference",
            guard_reasons=list(dict.fromkeys(reasons)),
        )
        recommendation["reason"] = (
            "담당자 확인 필요: "
            + " / ".join(recommendation["guard_reasons"])
            + " | "
            + recommendation.get("reason", "")
        )
    else:
        recommendation.update(
            candidate_role=(
                "recommendation"
                if recommendation.get("status") == "추천가능"
                else "reference"
            ),
            guard_reasons=[],
        )
    return recommendation
