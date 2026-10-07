import json, os, subprocess, sys, threading, fcntl
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.config import ROOT, settings
from backend.analytics.config import AnalyticsConfig, cache_root
from backend.analytics.bertopic_service import current, atomic_json
from backend.analytics.topic_validation import warnings

router = APIRouter(prefix="/api/topics", tags=["Offline VOC analytics"])
_launch_lock = threading.Lock()
_process = None


def read(mode):
    try:
        return current(mode)
    except Exception as exc:
        raise HTTPException(
            503, f"Topic 분석 결과 읽기 실패: {type(exc).__name__}: {exc}"
        ) from exc


def job():
    if _process is not None:
        _process.poll()  # Reap completed child before checking its PID.
    root = cache_root()
    path = root / "job.json"
    try:
        value = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else {"status": "idle"}
        )
        launch = root / "launch.json"
        pending = (
            json.loads(launch.read_text(encoding="utf-8")) if launch.exists() else {}
        )
        if pending.get("pid"):
            try:
                os.kill(pending["pid"], 0)
                if value.get("pid") != pending["pid"] or value.get("status") not in {
                    "running",
                    "failed",
                }:
                    return {**pending, "status": "starting"}
            except ProcessLookupError:
                pass
        if value.get("status") in {"running", "starting"} and value.get("pid"):
            try:
                os.kill(value["pid"], 0)
            except ProcessLookupError:
                value = {
                    **value,
                    "status": "failed",
                    "error": "배치 프로세스가 종료되었습니다. 로그를 확인하세요.",
                }
        return value
    except (OSError, ValueError) as exc:
        return {"status": "failed", "error": str(exc)}


@router.get("")
def list_topics(mode: Literal["all", "z1"] = "all"):
    result = read(mode)
    return {
        **{k: v for k, v in result.items() if k != "document_mapping"},
        "job": job(),
    }


@router.get("/z1")
def z1():
    return list_topics("z1")


@router.get("/trends")
def topic_trends(mode: Literal["all", "z1"] = "all"):
    return read(mode).get(
        "trends", {"enabled": False, "reason": "미학습", "topics": []}
    )


@router.get("/emerging")
def emerging(mode: Literal["all", "z1"] = "all"):
    trend = topic_trends(mode)
    return {**trend, "topics": [r for r in trend.get("topics", []) if r["emerging"]]}


@router.get("/warnings")
def review_candidates(request: Request, mode: Literal["all", "z1"] = "all"):
    result = read(mode)
    if result["status"] != "ready":
        return {"status": result["status"], "candidates": []}
    try:
        found = warnings(
            result,
            request.app.state.service.signature,
            settings.output / "voc.sqlite3",
            AnalyticsConfig().validate(),
        )
        return {
            "status": "ready",
            "candidates": found,
            "automatic_label_change": False,
            "recommendation_override": False,
        }
    except Exception as exc:
        raise HTTPException(503, f"분류 재검토 통계 오류: {exc}") from exc


@router.get("/documents/{voc_id}")
def document_topic(voc_id: str, mode: Literal["all", "z1"] = "all"):
    result = read(mode)
    rows = [r for r in result.get("document_mapping", []) if r["id"] == voc_id]
    return {
        "status": result["status"],
        "mapping": rows,
        "fingerprint": result["fingerprint"],
    }


class Rebuild(BaseModel):
    mode: Literal["all", "z1", "both"] = "both"
    force: bool = False


@router.post("/rebuild", status_code=202)
def rebuild(body: Rebuild):
    global _process
    try:
        AnalyticsConfig().validate()
        root = cache_root()
        root.mkdir(parents=True, exist_ok=True)
        with _launch_lock, (root / "launch.lock").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            if _process is not None and _process.poll() is None:
                raise HTTPException(409, "Topic 배치가 이미 실행 중입니다")
            if job().get("status") in {"running", "starting"}:
                raise HTTPException(409, "Topic 배치가 이미 실행 중입니다")
            args = [
                sys.executable,
                "-m",
                "backend.analytics.run_bertopic",
                "--mode",
                body.mode,
            ]
            if body.force:
                args.append("--force")
            env = {
                **os.environ,
                "OMP_NUM_THREADS": "2",
                "NUMBA_NUM_THREADS": "2",
                "TOKENIZERS_PARALLELISM": "false",
                "CUDA_VISIBLE_DEVICES": "",
            }
            with (root / "batch.log").open("a", encoding="utf-8") as log:
                _process = subprocess.Popen(
                    args,
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            atomic_json(
                root / "launch.json",
                {"status": "starting", "mode": body.mode, "pid": _process.pid},
            )
            return {"status": "accepted", "mode": body.mode, "pid": _process.pid}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Topic 배치 실행 실패: {exc}") from exc


@router.get("/{topic_id}")
def topic_detail(topic_id: int, mode: Literal["all", "z1"] = "all"):
    result = read(mode)
    found = next(
        (x for x in result.get("topics", []) if x["topic_id"] == topic_id), None
    )
    if found is None:
        raise HTTPException(404, "현재 분석 결과에 Topic이 없습니다")
    return {
        **found,
        "mode": mode,
        "fingerprint": result["fingerprint"],
        "documents": [
            r for r in result["document_mapping"] if r["topic_id"] == topic_id
        ],
    }
