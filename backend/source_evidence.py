"""Bind model-selected evidence IDs to untouched source text, preserving raw output."""

import json
import re
from backend import notebook_logic as logic


def source_units(text):
    return [part.strip() for part in re.split(r"\n+", text) if part.strip()]


def source_block(text):
    return "\n".join(f"[{i}] {part}" for i, part in enumerate(source_units(text), 1))


def bind_evidence(raw, text, stage):
    value = logic.parse_json_object(raw)
    units = source_units(text)

    def quote(identifier):
        if type(identifier) is not int or not 1 <= identifier <= len(units):
            raise ValueError("원문 근거 ID 범위/타입 오류")
        return units[identifier - 1]

    if stage == "topic":
        for id_key, key in [
            ("evidence_id", "evidence"),
            ("intent_evidence_id", "intent_evidence"),
        ]:
            if id_key in value:
                value[key] = quote(value[id_key])
    elif stage == "cause" and isinstance(value.get("claims"), list):
        for claim in value["claims"]:
            if isinstance(claim, dict) and "evidence_id" in claim:
                claim["evidence"] = quote(claim["evidence_id"])
    return json.dumps(value, ensure_ascii=False)
