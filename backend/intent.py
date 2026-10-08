"""VOC intent is separate from topic codes, jurisdiction and department labels."""

import re

INTENTS = {"칭찬", "불만", "문의", "제안", "복합", "확인필요"}
PRAISE = re.compile(r"칭찬|감사드립니다|감사\s*인사|감사했습니다|덕분에|감사한\s*경험")
COMPLAINT = re.compile(r"불친절|무례|불만|항의|짜증|안\s*도와|지나가버|면박")


def source_intent(text):
    praise = bool(PRAISE.search(text))
    complaint = bool(COMPLAINT.search(text))
    if praise and complaint:
        return "복합"
    if praise:
        return "칭찬"
    if complaint:
        return "불만"
    return "확인필요"


def enrich_intent(text, analysis):
    result = dict(analysis)
    inferred = source_intent(text)
    model_intent = result.get("voc_intent", "확인필요")
    issues = list(result.get("semantic_issues", []))
    if inferred == "칭찬" and model_intent not in {"칭찬", "확인필요"}:
        issues.append("명시적 칭찬과 모델 의도 불일치")
    if inferred == "복합":
        intent = "복합"
    else:
        intent = inferred if model_intent == "확인필요" else model_intent
    result.update(
        voc_intent=intent,
        intent_source=(
            "qwen"
            if intent == model_intent and model_intent != "확인필요"
            else "source_rule"
        ),
        semantic_issues=issues,
    )
    return result
