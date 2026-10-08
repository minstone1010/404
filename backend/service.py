import hashlib, json, time, threading, logging
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from backend.config import settings
from backend import notebook_logic as logic
from backend.models import Qwen, Embedding
from backend.decision import Store
from backend.routing import restrict_routing_candidates
from backend.validation import validate
from backend.dual_retrieval import recommend as dual_recommend
from backend.cause_validation import cause_issues, review_cause
from backend.source_evidence import bind_evidence
from backend.semantic import (
    topic_issues,
    resolve_routing,
    recommendation_guard,
    VERSION,
)

log = logging.getLogger(__name__)


def recommendation_signature(
    version="web-v4-dual-search", semantic_version=VERSION, retrieval_profile=True
):
    # Versioned prompts/semantic checks; old cache remains available for offline revalidation.
    return hashlib.sha256(
        json.dumps(
            [
                settings.qwen_model,
                settings.embedding_model,
                settings.quantization,
                logic.CODEBOOK_HASH,
                logic.MASTER_HASH,
                hashlib.sha256(settings.voc_path.read_bytes()).hexdigest(),
                (
                    version
                    if version == "web-v2-strict"
                    else f"{version}:{semantic_version}"
                ),
                settings.split_mode,
                settings.history_fraction,
                settings.top_k,
                settings.min_similarity,
                settings.min_support,
                settings.min_score_margin,
                *(
                    [settings.analysis_min_similarity, "dual-retrieval-v1"]
                    if version == "web-v4-dual-search" and retrieval_profile
                    else []
                ),
            ],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


class Service:
    def __init__(self):
        self.store = Store()
        self.qwen = Qwen()
        self.embedding = Embedding()
        self.lock = threading.RLock()
        self.ready = False
        self.error = None
        self.history_progress = 0
        self.history_total = int(logic.df.데이터역할.eq("검색이력").sum())
        self.history_complete = False
        self.history_preparation_done = False
        self.history_failed = 0
        self.signature = recommendation_signature()
        self.legacy_signature = recommendation_signature("web-v2-strict")
        self.legacy_signatures = [
            recommendation_signature(retrieval_profile=False),
            recommendation_signature("web-v3-routing-guard", semantic_version=VERSION),
            recommendation_signature(
                "web-v3-routing-guard",
                semantic_version="semantic-routing-v5-evidence-r1",
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v5-evidence"
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v4-intent-r1"
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v4-intent"
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v3"
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v2"
            ),
            recommendation_signature(
                "web-v3-routing-guard", semantic_version="semantic-routing-v1"
            ),
            self.legacy_signature,
        ]
        self.history_quality_excluded = 0
        self.teams = sorted(
            logic.department_master.loc[
                logic.department_master.routing_enabled, "department"
            ].tolist()
        )
        self.channels = pd.read_excel(
            settings.master_path, sheet_name="channel_master"
        ).fillna("")
        logic.assert_columns(
            self.channels,
            ["raw_channel", "code", "label", "channel_group", "enabled"],
            "channel_master",
        )
        logic.qwen_generate = self.qwen.generate
        logic.restrict_routing_candidates = restrict_routing_candidates
        logic.embed_model = self.embedding
        self.rebuild_index()

    def parse_channel(self, raw):
        raw = logic.clean_text(raw)
        code = raw.split()[0].upper() if raw else ""
        rows = (
            self.channels.loc[
                self.channels.enabled.map(logic.enabled_flag)
                & (self.channels.raw_channel.eq(raw) | self.channels.code.eq(code))
            ]
            if raw
            else self.channels.iloc[:0]
        )
        if len(rows) != 1:
            return dict(
                raw=raw,
                code=code,
                label="확인 필요",
                group=None,
                status="미입력" if not raw else "미매핑",
            )
        row = rows.iloc[0]
        return dict(
            raw=raw,
            code=row.code,
            label=row.label,
            group=row.channel_group,
            status="DB확인",
        )

    def row(self, id):
        rows = logic.df.loc[logic.df.번호.eq(str(id))]
        if len(rows) != 1:
            raise KeyError(id)
        return rows.iloc[0].drop(labels=["handling_team"]).to_dict()

    def analyzed_stage(self, stage, generate, raw, voc_text=None):
        original = logic.qwen_generate
        feedback = ""
        try:
            for attempt in range(2):
                logic.qwen_generate = lambda prompt, tokens: original(
                    prompt + feedback, tokens
                )
                raw[stage] = generate()
                try:
                    validated_input = (
                        bind_evidence(raw[stage], voc_text, stage)
                        if voc_text is not None and stage in {"topic", "cause"}
                        else raw[stage]
                    )
                    parsed = validate(validated_input, stage)
                    if stage in {"topic", "cause"} and voc_text is not None:
                        issues = (
                            topic_issues(voc_text, parsed, require_evidence=True)
                            if stage == "topic"
                            else cause_issues(voc_text, parsed)
                        )
                        if issues:
                            raw.setdefault("semantic_validation_errors", []).append(
                                {
                                    "stage": stage,
                                    "attempt": attempt + 1,
                                    "issues": issues,
                                }
                            )
                            if attempt == 0:
                                feedback = (
                                    "\n[원문 의미 검증 재시도] "
                                    + " / ".join(issues)
                                    + (
                                        " 원문의 대상·문제와 근거에 맞는 요지를 선택하세요."
                                        if stage == "topic"
                                        else " 각 주장 주체/행동을 인용 근거로 확인하세요. 원인이 불명이면 unknown, 근거 없으면 claims=[]로 적으세요. 원문에 없는 직원 행동을 만들지 마세요."
                                    )
                                )
                                continue
                            if stage == "cause":
                                return review_cause(parsed, issues)
                            parsed["semantic_issues"] = issues
                    return parsed
                except ValueError as exc:
                    raw.setdefault("validation_errors", []).append(
                        {
                            "stage": stage,
                            "attempt": attempt + 1,
                            "error": str(exc),
                            "response": raw[stage],
                        }
                    )
                    if attempt == 1:
                        if stage == "cause" and voc_text is not None:
                            return review_cause(
                                {}, ["원인 JSON 검증 실패: " + str(exc)]
                            )
                        raise
                    feedback = (
                        "\n[재시도 검증 오류] "
                        + str(exc)
                        + "\n이 오류를 수정하세요. 모든 필수 필드를 포함하고 주·부 요지코드는 서로 달라야 하며 부요지가 없으면 JSON null을 사용하세요."
                    )
        finally:
            logic.qwen_generate = original

    def analyze(self, row, force=False):
        # No truth labels, origin/destination or database topic fields cross this boundary.
        assert "handling_team" not in row and "topic_code" not in row
        id = row["번호"]
        saved = self.store.analysis(id, self.signature)
        if (
            saved
            and saved.get("analysis", {}).get("분석상태") == "분석완료"
            and not force
        ):
            return saved
        t = time.perf_counter()
        raw = {}
        stage = "input"
        try:
            if not row["민원내용"]:
                raise ValueError("민원내용 없음")
            stage = "topic"
            topic = self.analyzed_stage(
                stage,
                lambda: logic.analyze_topic(row["민원내용"]),
                raw,
                row["민원내용"],
            )
            stage = "cause"
            if topic.get("voc_intent") == "칭찬":
                cause = {
                    "인적요인": 0,
                    "물적요인": 0,
                    "기타": 0,
                    "발생원인_판단이유": "칭찬 VOC: 문제 발생 원인 평가는 해당 없음",
                    "cause_analysis_status": "not_applicable",
                }
            else:
                try:
                    cause = self.analyzed_stage(
                        stage,
                        lambda: logic.analyze_cause(row["민원내용"], topic),
                        raw,
                        row["민원내용"],
                    )
                except Exception as exc:
                    log.exception(
                        "VOC %s 원인 추론 실패: 원인만 검토 대상으로 분리", id
                    )
                    raw["cause_inference_error"] = f"{type(exc).__name__}: {exc}"
                    cause = review_cause(
                        {}, ["원인 추론 실패: " + raw["cause_inference_error"]]
                    )
            cause.setdefault("cause_analysis_status", "validated")
            stage = "routing"
            routing = self.analyzed_stage(
                stage, lambda: logic.analyze_routing(row["민원내용"]), raw
            )
            analysis = {
                **topic,
                **cause,
                **routing,
                **logic.lookup_location(routing["location_candidate"]),
                **logic.lookup_function(topic["주요지코드"]),
                "분석상태": "분석완료",
                "라우팅분석상태": "완료",
            }
            analysis = resolve_routing(row["민원내용"], analysis)
            result = dict(
                id=id,
                analysis=analysis,
                raw=raw,
                analysis_seconds=time.perf_counter() - t,
                model=settings.qwen_model,
            )
        except Exception as exc:
            result = dict(
                id=id,
                analysis={"분석상태": "분석오류"},
                failed_stage=stage,
                error=f"{type(exc).__name__}: {exc}",
                raw=raw,
                analysis_seconds=time.perf_counter() - t,
                model=settings.qwen_model,
            )
            log.exception("VOC %s %s 분석 실패", id, stage)
        self.store.record_recommendation(id, self.signature, result)
        return result

    def rebuild_index(self):
        records = []
        self.history_quality_excluded = 0
        for _, r in logic.df.loc[logic.df.데이터역할.eq("검색이력")].iterrows():
            p = self.store.analysis(r["번호"], self.signature)
            if p is None:
                legacy = next(
                    (
                        p
                        for sig in self.legacy_signatures
                        if (p := self.store.analysis(r["번호"], sig))
                    ),
                    None,
                )
                if legacy and legacy.get("analysis", {}).get("분석상태") == "분석완료":
                    original_analysis = dict(legacy["analysis"])
                    # Preserve persistent failures when migrating, including old caches
                    # whose status was cleared while the raw audit still records failure.
                    recorded_issues = [
                        issue
                        for event in legacy.get("raw", {}).get(
                            "semantic_validation_errors", []
                        )
                        if event.get("stage", "topic") == "topic"
                        and event.get("attempt") == 2
                        for issue in event.get("issues", [])
                    ]
                    original_analysis["semantic_issues"] = list(
                        dict.fromkeys(
                            original_analysis.get("semantic_issues", [])
                            + recorded_issues
                        )
                    )
                    original_routing = legacy.get("raw", {}).get("routing")
                    if original_routing:
                        original_analysis.update(logic.parse_routing(original_routing))
                    cause_problems = cause_issues(r["민원내용"], original_analysis)
                    if (
                        original_analysis.get("cause_analysis_status")
                        != "not_applicable"
                        and cause_problems
                    ):
                        original_analysis = review_cause(
                            original_analysis, cause_problems
                        )
                    p = {
                        **legacy,
                        "analysis": resolve_routing(r["민원내용"], original_analysis),
                        "cache_revalidated_from": "web-v2-strict",
                    }
                    self.store.record_recommendation(r["번호"], self.signature, p)
            if p and p.get("analysis", {}).get("semantic_issues"):
                self.history_quality_excluded += 1
            if (
                p
                and p["analysis"].get("분석상태") == "분석완료"
                and not p["analysis"].get("semantic_issues")
                and r["handling_team"]
            ):
                records.append({**r.to_dict(), **p["analysis"]})
        self.history_progress = len(records)
        if not records:
            logic.history_df = logic.attach_department_attributes(
                logic.df.iloc[:0]
            ).reset_index(drop=True)
            logic.history_embeddings = np.zeros((0, 384))
            return
        frame = logic.attach_department_attributes(pd.DataFrame(records))
        self.department_mapping_audit = (
            frame.groupby(["handling_team", "dept_mapping_status"], dropna=False)
            .size()
            .rename("history_count")
            .reset_index()
            .to_dict("records")
        )
        audit_path = settings.output / "department_mapping_audit.json"
        audit_path.write_text(
            json.dumps(self.department_mapping_audit, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        frame = frame.loc[frame.dept_mapping_status.eq("매핑완료")].reset_index(
            drop=True
        )
        texts = frame.apply(logic.embedding_text, axis=1).tolist()
        key = hashlib.sha256(
            json.dumps(
                [self.signature, texts, frame.번호.tolist()], ensure_ascii=False
            ).encode()
        ).hexdigest()
        cache = settings.output / ("embedding-" + key + ".npz")
        if cache.exists():
            embeddings = np.load(cache, allow_pickle=False)["vectors"]
        else:
            embeddings = self.embedding.encode(
                texts,
                batch_size=16,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            temp = cache.with_suffix(".tmp.npz")
            np.savez_compressed(temp, vectors=embeddings)
            temp.replace(cache)
        logic.history_df = frame
        logic.history_embeddings = embeddings

    def prepare_history(self, limit=None):
        self.qwen.load()
        self.embedding.load()
        self.ready = True
        rows = logic.df.loc[logic.df.데이터역할.eq("검색이력")]
        if limit is not None:
            rows = rows.head(limit)
        for i, (_, r) in enumerate(rows.iterrows()):
            with self.lock:
                self.analyze(r.drop(labels=["handling_team"]).to_dict())
                if (i + 1) % 10 == 0:
                    self.rebuild_index()
            if (i + 1) % 10 == 0:
                log.info("과거 이력 분석 %s/%s", i + 1, len(rows))
            time.sleep(0.01)
        with self.lock:
            self.rebuild_index()
        self.history_complete = limit is None
        self.history_preparation_done = limit is None
        self.history_failed = (
            sum(
                (self.store.analysis(id, self.signature) or {})
                .get("analysis", {})
                .get("분석상태")
                != "분석완료"
                for id in rows["번호"]
            )
            if limit is None
            else 0
        )

    def start(self):
        try:
            self.prepare_history()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("서버 모델/이력 초기화 실패")

    def recommend(self, id, mode="C", force=False, source="evaluation"):
        with self.lock:
            row = self.row(id)
            if row["데이터역할"] != "검토대상" and settings.split_mode == "holdout":
                raise ValueError("holdout 평가 VOC만 추천 가능합니다")
            if mode != "C" and logic.history_df.empty:
                raise RuntimeError(
                    "분석 완료된 과거 이력이 없습니다. 이력 준비 상태를 확인하세요."
                )
            t = time.perf_counter()
            result = self.analyze(row, force)
            result = {
                **result,
                "execution_source": source,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
            if mode != "C" and result["analysis"].get("분석상태") != "분석완료":
                if source == "manual":
                    self.store.save_manual_analysis(id, self.signature, result)
                return result
            original = getattr(
                logic, "restrict_routing_candidates", restrict_routing_candidates
            )
            if mode == "A":
                logic.restrict_routing_candidates = lambda r: (
                    logic.history_df,
                    "A: 전체 검색",
                )
            elif mode == "B":

                def regional(r):
                    return restrict_routing_candidates({**r, "업무기능후보": []})

                logic.restrict_routing_candidates = regional
            try:
                rec = (
                    dual_recommend(self, {**row, **result["analysis"]})
                    if mode == "C"
                    else logic.recommend_department({**row, **result["analysis"]})
                )
            finally:
                logic.restrict_routing_candidates = original
            ranking = rec["top_departments"].head(settings.top_n).to_dict("records")
            for i, x in enumerate(ranking, 1):
                attrs = logic.department_master.loc[
                    logic.department_master.department.eq(x["department"])
                ].iloc[0]
                x.update(
                    ranking=i,
                    support_count=x["count"],
                    business_function=attrs.business_function,
                    region_code=attrs.region_code,
                    scope=attrs.scope,
                    parent_org=attrs.parent_org,
                    department_source="더미 VOC 과거 처리부서 · 최신 공식 명칭 미검증",
                    master_matched=True,
                    jurisdiction_match=(
                        (attrs.region_code == result["analysis"].get("관할지역코드"))
                        if result["analysis"].get("routing_scope") == "지역형"
                        else None
                    ),
                )
            rec = recommendation_guard(result["analysis"], rec, ranking, mode)
            result = {
                **result,
                "recommendation": {
                    k: v
                    for k, v in rec.items()
                    if k not in {"top_departments", "similar_vocs"}
                },
                "ranking": ranking,
                "evidence": rec["similar_vocs"][
                    [
                        c
                        for c in [
                            "번호",
                            "handling_team",
                            "similarity",
                            "민원내용",
                            "raw_similarity",
                            "analysis_similarity",
                            "search_source",
                            "중복그룹",
                        ]
                        if c in rec["similar_vocs"]
                    ]
                ]
                .head(settings.top_k)
                .to_dict("records"),
                "total_seconds": time.perf_counter() - t,
                "history_count": len(logic.history_df),
                "history_complete": self.history_complete,
                "mode": mode,
            }
            if source == "manual":
                self.store.save_manual_analysis(id, self.signature, result)
            return result

    def detail(self, id):
        row = self.row(id)
        result = self.store.manual_analysis(str(id), self.signature) or {}
        a = result.get("analysis", {})
        rec = result.get("recommendation", {})
        saved = self.store.load_approvals().get(str(id))
        saved = saved if saved and saved.get("signature") == self.signature else None
        status = (
            saved["status"]
            if saved
            else (
                "확인대기"
                if rec
                else (
                    "분석완료"
                    if a.get("분석상태") == "분석완료"
                    else "분석오류" if result.get("error") else "분석대기"
                )
            )
        )
        return dict(
            id=str(id),
            title=logic.clean_text(row["subject"]),
            body=row["민원내용"],
            channel=self.parse_channel(row["intake_channel"])["label"],
            channel_info=self.parse_channel(row["intake_channel"]),
            date="미제공",
            topic=(
                (str(a.get("주요지코드", "")) + " · " + str(a.get("주요지", "")))
                if a
                else "미분석"
            ),
            sub=a.get("부요지") or "없음",
            cause=(
                "원인 확인 필요"
                if a.get("cause_analysis_status") == "review_required"
                else logic.cause_text(a) or "미분석"
            ),
            causeStatus=a.get("cause_analysis_status"),
            causeValidationNotes=a.get("cause_validation_issues", []),
            intent=a.get("voc_intent", "확인필요"),
            requestSummary=a.get("request_summary"),
            intentEvidence=a.get("intent_evidence"),
            keywords=a.get("핵심키워드", "").split(", ") if a else [],
            location=a.get("location_candidate"),
            hq=a.get("관할본부"),
            function=a.get("업무기능") or "확인 필요",
            scope=a.get("routing_scope", "미분석"),
            locationStatus=a.get("위치매핑상태", "미분석"),
            locationRaw=a.get("location_candidate_raw"),
            locationRole=a.get("location_role", "unknown"),
            validationNotes=a.get("semantic_issues", [])
            + a.get("routing_validation_notes", []),
            retrievalComparison=rec.get("retrieval_comparison"),
            routingConstraints=rec.get("routing_constraints", {}),
            candidateRole=rec.get("candidate_role", "reference"),
            routing=rec.get("routing_filter_info", "미분석"),
            recs=[
                dict(
                    name=x["department"],
                    fn=str(x.get("scope", "확인 필요"))
                    + " · "
                    + str(x.get("business_function", "확인 필요")),
                    score=x["score"],
                    similarity=x["mean_similarity"],
                    count=x["support_count"],
                    source=x.get("department_source", "과거 VOC 원본 라벨"),
                    candidate_role=rec.get("candidate_role", "reference"),
                    region=x.get("region_code"),
                    jurisdiction_match=x.get("jurisdiction_match"),
                    routing_eligibility=x.get("routing_eligibility", {}),
                )
                for x in result.get("ranking", [])
            ],
            reason=rec.get("reason") or result.get("error") or "분석을 실행하세요.",
            scopeNote=(
                f"과거 이력 준비 완료: 분석 오류 {self.history_failed}건 · 의미 검증 검색제외 {getattr(self, 'history_quality_excluded', 0)}건"
                if self.history_preparation_done
                else f"이력 준비 중: 현재 {len(logic.history_df)}건 검색 가능"
            ),
            hold=rec.get("status") != "추천가능",
            status=status,
            decision=saved,
            result=result,
        )

    def evaluate(self, limit=None):
        if settings.split_mode != "holdout":
            raise ValueError("평가는 holdout에서만 가능합니다")
        with self.lock:
            ids = logic.df.loc[logic.df.데이터역할.eq("검토대상"), "번호"].tolist()
            if limit is not None:
                ids = ids[:limit]
            return [
                dict(id=id, mode=mode, output=self.recommend(id, mode))
                for id in ids
                for mode in ["A", "B", "C"]
            ]

    def save_decision(self, id, department, status, memo):
        detail = self.detail(id)
        if not detail["result"].get("recommendation"):
            raise ValueError("분석과 추천을 완료한 뒤 승인/보류할 수 있습니다")
        return self.store.save_decision(
            str(id),
            department,
            status,
            memo,
            self.teams,
            detail["result"]["recommendation"].get("recommended_department"),
            self.signature,
        )
