"""Evidence checks for explanatory claims; failed causes never become search input."""

import re
from backend.semantic import compact


def cause_issues(text, analysis, require_claims=True):
    issues = []
    reason = analysis.get("발생원인_판단이유") or ""
    if re.search(r"승무원|역무원|직원", reason) and not re.search(
        r"승무원|역무원|직원", text
    ):
        issues.append("원인 설명에 원문에 없는 직원/승무원 행동 주체 생성")
    for pattern in [
        r"승무원.{0,15}(?:기겁|울고|울었|자리.*옮)",
        r"직원.{0,15}(?:기겁|울고|울었|자리.*옮)",
    ]:
        if re.search(pattern, reason) and not re.search(pattern, text):
            issues.append("원인 설명에서 직원과 승객의 행동 주체를 바꿈")
    claims = analysis.get("cause_claims")
    if require_claims and claims is None:
        issues.append("원인 주장별 원문 근거 누락")
    for claim in claims or []:
        evidence = claim["evidence"]
        if compact(evidence) not in compact(text):
            issues.append("원인 주장 근거가 원문에 없음")
        if compact(claim["action"]) not in compact(evidence):
            issues.append("원인 주장 행동이 인용 근거에 없음")
        subject = claim["subject"]
        if subject not in {"확인불가", "민원인"} and compact(subject) not in compact(
            evidence
        ):
            issues.append("원인 주장 행동 주체가 해당 인용 근거에 없음")
        if subject == "민원인" and not re.search(
            r"나|저|제가|옮겼|이용했|탔", evidence
        ):
            issues.append("민원인 행동 주체 근거 부족")
        if claim["certainty"] == "confirmed" and re.search(
            r"건가요|인지|같|추측|아마|혹시|\?", evidence
        ):
            issues.append("질문/추측을 확정 원인으로 취급")
    if (
        require_claims
        and any(analysis.get(k) == 1 for k in ["인적요인", "물적요인", "기타"])
        and not claims
    ):
        issues.append("선택한 원인 요인의 주장 근거 없음")
    if (
        analysis.get("cause_certainty") == "confirmed"
        and claims
        and not any(
            c["certainty"] == "confirmed"
            and not re.search(r"건가요|인지|같|추측|아마|혹시|\?", c["evidence"])
            for c in claims
        )
    ):
        issues.append("추정 주장만으로 전체 원인을 확정함")
    if analysis.get("cause_certainty") == "confirmed" and not claims:
        issues.append("확정 원인의 근거 주장 없음")
    if analysis.get("인적요인") == 1 and not re.search(
        r"승무원|역무원|직원|담당자|기사", text
    ):
        issues.append("직원 행동 근거 없이 인적 문제로 판단")
    if reason.strip() in {"민원에 근거한 간단한 설명", "본문 근거", "간단한 설명"}:
        issues.append("원인 설명에 실제 내용 대신 예시 문구 출력")
    return list(dict.fromkeys(issues))


def review_cause(analysis, issues):
    result = dict(analysis)
    result.update(
        cause_validation_issues=issues,
        cause_analysis_status="review_required",
        cause_original={
            k: analysis.get(k)
            for k in [
                "인적요인",
                "물적요인",
                "기타",
                "발생원인_판단이유",
                "cause_claims",
                "cause_certainty",
            ]
        },
        인적요인=None,
        물적요인=None,
        기타=None,
        발생원인_판단이유="원인 확인 필요 · 검증되지 않은 설명은 검색에서 제외",
    )
    return result
