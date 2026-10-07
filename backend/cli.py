import argparse, json, time
from backend.service import Service
from backend import notebook_logic as logic
from backend.config import settings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["prepare-history", "evaluate", "export"])
    p.add_argument("--limit", type=int)
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument("--api-url")
    args = p.parse_args()
    if args.limit is not None and args.limit < 1:
        p.error("--limit는 양수여야 합니다")
    if args.command == "evaluate" and settings.split_mode != "holdout":
        p.error("평가는 SPLIT_MODE=holdout에서만 가능합니다")
    s = Service()
    if args.command == "prepare-history":
        s.prepare_history(args.limit)
        print(
            json.dumps(
                dict(analyzed=s.history_progress, searchable=len(logic.history_df)),
                ensure_ascii=False,
            )
        )
        return
    if args.command == "export":
        print(s.store.export_results())
        return
    missing = [
        r["번호"]
        for _, r in logic.df.loc[logic.df.데이터역할.eq("검색이력")].iterrows()
        if s.store.analysis(r["번호"], s.signature) is None
    ]
    if missing and not args.allow_partial:
        raise RuntimeError(
            f"과거 이력 {len(missing)}건 미완료. prepare-history를 먼저 실행하세요. 시험 평가는 --allow-partial로 명시하세요."
        )
    s.history_complete = not missing
    if not args.api_url:
        s.qwen.load()
    rows = logic.df.loc[logic.df.데이터역할.eq("검토대상")]
    if args.limit:
        rows = rows.head(args.limit)
    truth = logic.evaluation_truth_df.set_index("번호")
    results = []
    remote = {}
    if args.api_url:
        import httpx

        response = httpx.post(
            args.api_url.rstrip("/") + "/api/evaluate",
            params={"limit": args.limit} if args.limit else {},
            timeout=None,
        )
        response.raise_for_status()
        remote = {(x["id"], x["mode"]): x["output"] for x in response.json()}

    for _, row in rows.iterrows():
        for mode in ["A", "B", "C"]:
            if args.api_url:
                output = remote[(row["번호"], mode)]
            else:
                output = s.recommend(row["번호"], mode)
            results.append(dict(id=row["번호"], mode=mode, output=output))
            print(
                row["번호"],
                mode,
                output.get("recommendation", {}).get("status"),
                flush=True,
            )
    from sklearn.metrics import accuracy_score, f1_score
    import torch, numpy as np

    report = {
        "history_complete": not missing,
        "history_count": (
            results[0]["output"].get("history_count", len(logic.history_df))
            if results
            else 0
        ),
        "model": settings.qwen_model,
        "timing_note": "analysis_seconds는 원래 분석 측정치, total_seconds는 현재 요청 처리시간(분석 캐시 재사용 가능)",
        "ground_truth_limitations": "지역/function/scope 정답 컬럼 없음. 부서 Master 속성에서 얻은 proxy만 제공하며 독립 정답 정확도가 아님",
        "modes": {},
    }
    for mode in ["A", "B", "C"]:
        items = [x for x in results if x["mode"] == mode]
        gold = []
        pred = []
        top1 = []
        top3 = []
        coverage = []
        regions = []
        functions = []
        scopes = []
        analysis_times = []
        total_times = []
        for x in items:
            o = x["output"]
            a = o["analysis"]
            t = truth.loc[x["id"]]
            ranking = o.get("ranking", [])
            names = [r["department"] for r in ranking]
            gold.append(t["topic_code"])
            pred.append(a.get("주요지코드", "분석실패"))
            top1.append(bool(names and names[0] == t["handling_team"]))
            top3.append(t["handling_team"] in names)
            coverage.append(o.get("recommendation", {}).get("status") == "추천가능")
            analysis_times.append(o["analysis_seconds"])
            total_times.append(o.get("total_seconds", o["analysis_seconds"]))
            dept = logic.department_master.loc[
                logic.department_master.department.eq(t["handling_team"])
            ]
            if len(dept) == 1:
                d = dept.iloc[0]
                if d.scope == "지역":
                    regions.append(a.get("관할지역코드") == d.region_code)
                functions.append(d.business_function in a.get("업무기능후보", []))
                scopes.append(
                    a.get("routing_scope")
                    == ("지역형" if d.scope == "지역" else "전국형")
                )
        avg = lambda xs: float(np.mean(xs)) if xs else None
        report["modes"][mode] = dict(
            count=len(items),
            topic_accuracy=accuracy_score(gold, pred),
            topic_macro_f1=f1_score(gold, pred, average="macro", zero_division=0),
            region_proxy_accuracy=avg(regions),
            function_proxy_accuracy=avg(functions),
            scope_proxy_accuracy=avg(scopes),
            department_top1_accuracy=avg(top1),
            department_top3_accuracy=avg(top3),
            coverage=avg(coverage),
            defer_rate=1 - avg(coverage),
            mean_analysis_seconds=avg(analysis_times),
            mean_total_seconds=avg(total_times),
        )
    report["comparison_index_consistent"] = all(
        len({x["output"].get("history_count") for x in results if x["id"] == id}) == 1
        for id in {x["id"] for x in results}
    )
    report["gpu_peak_allocated_mb"] = (
        None
        if args.api_url
        else (
            torch.cuda.max_memory_allocated() / 1024**2
            if torch.cuda.is_available()
            else 0
        )
    )
    report["gpu_measurement_note"] = (
        "API 서버 모드에서는 서버 /api/stats의 VRAM 값을 참조"
        if args.api_url
        else "현재 평가 프로세스 PyTorch peak allocated"
    )
    (settings.output / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    (settings.output / "evaluation_records.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
