from typing import Literal
from contextlib import asynccontextmanager
import threading, logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from backend.config import settings, ROOT
from backend.service import Service
from backend import notebook_logic as logic

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    app.state.service = Service()
    if settings.startup_models:
        worker = threading.Thread(
            target=app.state.service.start, name="history-preparation", daemon=True
        )
        worker.start()
    yield


app = FastAPI(title="VOC Desk API", lifespan=lifespan)


def svc():
    return app.state.service


def safe(call):
    try:
        return call()
    except KeyError as e:
        raise HTTPException(404, "VOC를 찾을 수 없습니다") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e


class Decision(BaseModel):
    department: str = ""
    status: str
    memo: str = Field(default="", max_length=500)


@app.get("/api/vocs")
def vocs():
    ids = logic.df.loc[
        logic.df.데이터역할.eq(
            "검토대상" if settings.split_mode == "holdout" else "검색이력"
        ),
        "번호",
    ]
    return [svc().detail(id) for id in ids]


@app.get("/api/vocs/{id}")
def detail(id: str):
    return safe(lambda: svc().detail(id))


@app.post("/api/vocs/{id}/analyze")
def analyze(id: str):
    return safe(lambda: svc().recommend(id, mode="C", force=True, source="manual"))


@app.get("/api/vocs/{id}/recommendations")
def recommendations(id: str):
    return safe(lambda: svc().detail(id)["result"])


@app.post("/api/vocs/{id}/decision")
def decision(id: str, body: Decision):
    safe(lambda: svc().save_decision(id, body.department, body.status, body.memo))
    return svc().detail(id)


@app.get("/api/departments")
def departments():
    return svc().teams


@app.get("/api/stats")
def stats():
    import torch

    gpu = (
        dict(
            allocated_mb=torch.cuda.memory_allocated() / 1024**2,
            peak_allocated_mb=torch.cuda.max_memory_allocated() / 1024**2,
            reserved_mb=torch.cuda.memory_reserved() / 1024**2,
        )
        if torch.cuda.is_available()
        else None
    )
    return dict(
        gpu=gpu,
        total=len(logic.df),
        history_total=svc().history_total,
        history_analyzed=svc().history_progress,
        history_searchable=len(logic.history_df),
        history_complete=svc().history_complete,
        history_preparation_done=svc().history_preparation_done,
        history_failed=svc().history_failed,
        history_quality_excluded=getattr(svc(), "history_quality_excluded", 0),
        model_ready=svc().ready,
        initialization_error=svc().error,
        model=settings.qwen_model,
        decisions=len(svc().store.load_approvals()),
    )


@app.post("/api/evaluate")
def evaluate(limit: int | None = Query(default=None, ge=1)):
    return safe(lambda: svc().evaluate(limit))


@app.get("/api/export")
def export():
    return FileResponse(svc().store.export_results(), filename="voc_results.xlsx")


from backend.analytics.api import router as analytics_router

app.include_router(analytics_router)
app.mount("/", StaticFiles(directory=ROOT / "voc-ui" / "dist", html=True), name="ui")
