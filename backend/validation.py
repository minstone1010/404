import json
from backend import notebook_logic as logic


def validate(raw, stage):
    value = logic.parse_json_object(raw)
    required = {
        "topic": ["main_topic_code", "sub_topic_code", "keywords"],
        "cause": ["human_factor", "material_factor", "other_factor", "reason"],
        "routing": ["location_candidate", "routing_scope", "reason"],
    }[stage]
    for key in required:
        if key not in value:
            raise ValueError("필드 누락: " + key)
        item = value[key]
        nullable = key in {"sub_topic_code", "location_candidate"}
        if item is None and not nullable:
            raise ValueError("null 금지: " + key)
        if isinstance(item, str) and (
            not item.strip() or item.strip().lower() in {"null", "none", "nan"}
        ):
            raise ValueError("빈 문자열/문자열 null 금지: " + key)
        if (
            key
            in {
                "main_topic_code",
                "sub_topic_code",
                "location_candidate",
                "routing_scope",
                "reason",
            }
            and item is not None
            and not isinstance(item, str)
        ):
            raise ValueError("문자열 타입 오류: " + key)
    parser = {
        "topic": logic.parse_topic,
        "cause": logic.parse_cause,
        "routing": logic.parse_routing,
    }[stage]
    return parser(raw)
