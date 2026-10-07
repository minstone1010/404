"""Isolated CPU batch fitting and fingerprinted, atomic artifacts."""

import hashlib, json, os, sys, sqlite3, tempfile, time, uuid, shutil, fcntl
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import numpy as np
import pandas as pd
from backend.config import settings
from backend.analytics.config import AnalyticsConfig, cache_root
from backend.analytics.topic_discovery import preprocess, discover, STOPWORDS
from backend.analytics.topic_trend import trends

VERSION = "analytics-v3-multilingual-keywords"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def fingerprint(config):
    config.validate()
    return digest(
        dict(
            python=sys.version.split()[0],
            data_hash=hashlib.sha256(settings.voc_path.read_bytes()).hexdigest(),
            embedding_model=settings.embedding_model,
            split_mode=settings.split_mode,
            history_fraction=settings.history_fraction,
            config=config.fingerprint_config(),
            vectorizer_stopwords=STOPWORDS,
            version=VERSION,
            packages={
                p: version(p)
                for p in [
                    "bertopic",
                    "umap-learn",
                    "hdbscan",
                    "sentence-transformers",
                    "scikit-learn",
                    "numpy",
                    "pandas",
                    "numba",
                    "torch",
                    "transformers",
                ]
            },
        )
    )


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    temp.replace(path)


def current(mode="all"):
    if mode not in {"all", "z1"}:
        raise ValueError("mode는 all 또는 z1이어야 합니다")
    key = fingerprint(AnalyticsConfig())
    pointer = cache_root() / key / (mode + ".json")
    if not pointer.exists():
        return dict(
            status="not_built",
            mode=mode,
            fingerprint=key,
            message="관리자 배치 분석을 실행하세요.",
        )
    ref = json.loads(pointer.read_text(encoding="utf-8"))
    return json.loads(
        (cache_root() / key / ref["result_path"]).read_text(encoding="utf-8")
    )


def load_frame():
    from backend import notebook_logic as logic

    frame = (
        logic.df[["번호", "중복그룹", "데이터역할", "민원내용"]]
        .rename(
            columns={
                "번호": "id",
                "중복그룹": "case_group_id",
                "데이터역할": "role",
                "민원내용": "text",
            }
        )
        .copy()
    )
    frame["source_topic_code"] = (
        logic.db_df.set_index("번호")
        .topic_code.reindex(frame.id)
        .fillna("")
        .astype(str)
        .to_numpy()
    )
    config = AnalyticsConfig()
    if config.date_column and config.date_column not in logic.db_df:
        raise ValueError("BER_TOPIC_DATE_COLUMN이 원본에 없습니다")
    candidates = (
        [config.date_column]
        if config.date_column
        else [
            c
            for c in [
                "received_at",
                "intake_date",
                "created_at",
                "접수일시",
                "접수일자",
            ]
            if c in logic.db_df
        ]
    )
    frame["date"] = None
    if candidates:
        dates = pd.to_datetime(
            logic.db_df.set_index("번호")[candidates[0]].reindex(frame.id),
            errors="coerce",
            utc=True,
        )
        frame["date"] = [x.isoformat() if pd.notna(x) else None for x in dates]
    frame["text"] = frame.text.map(preprocess)
    return frame.loc[frame.text.ne("")].copy()


def cached_embeddings(texts):
    # Text key, not VOC ID: one vector per exact model/preprocessed text across both modes.
    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    keys = [
        digest([settings.embedding_model, AnalyticsConfig().preprocessing_version, t])
        for t in texts
    ]
    db = sqlite3.connect(root / "embeddings.sqlite3", timeout=30)
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY,dimension INTEGER NOT NULL,vector BLOB NOT NULL)"
        )
        found = {}
        for k in set(keys):
            row = db.execute(
                "SELECT dimension,vector FROM vectors WHERE key=?", (k,)
            ).fetchone()
            if row:
                found[k] = np.frombuffer(row[1], dtype=np.float32).copy()
        missing = list(dict.fromkeys(k for k in keys if k not in found))
        text_by_key = dict(zip(keys, texts))
        if missing:
            from sentence_transformers import SentenceTransformer
            import torch

            torch.set_num_threads(2)
            model = SentenceTransformer(settings.embedding_model, device="cpu")
            vectors = model.encode(
                [text_by_key[k] for k in missing],
                batch_size=32,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for k, v in zip(missing, vectors):
                v = np.asarray(v, dtype=np.float32)
                found[k] = v
                db.execute(
                    "INSERT OR REPLACE INTO vectors VALUES (?,?,?)",
                    (k, len(v), v.tobytes()),
                )
            db.commit()
        return np.stack([found[k] for k in keys]), dict(
            requested=len(keys),
            cached=len(keys) - sum(k in missing for k in keys),
            computed_unique=len(missing),
            input="원문 정규화; retrieval의 Qwen 요약 벡터와 구분",
            device="cpu",
        )
    finally:
        db.close()


def build(mode="all", force=False):
    if mode not in {"all", "z1"}:
        raise ValueError("알 수 없는 분석 mode")
    config = AnalyticsConfig().validate()
    key = fingerprint(config)
    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "rebuild.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("다른 BERTopic 배치가 실행 중입니다")
        existing = current(mode)
        if existing["status"] == "ready" and not force:
            return existing
        started = time.perf_counter()
        atomic_json(
            root / "job.json",
            dict(
                status="running",
                mode=mode,
                pid=os.getpid(),
                started_at=datetime.now(timezone.utc).isoformat(),
                fingerprint=key,
            ),
        )
        staging = None
        try:
            frame = load_frame()
            if mode == "z1":
                frame = frame.loc[frame.source_topic_code.eq("Z1")].copy()
            # One fit document per existing independent case group, deterministic representative.
            reps = (
                frame.sort_values("id")
                .drop_duplicates("case_group_id")
                .reset_index(drop=True)
            )
            if len(reps) < max(config.min_cluster_size + 1, config.components + 2, 4):
                raise ValueError("독립 사례가 너무 적어 BERTopic을 학습할 수 없습니다")
            vectors, embedding_stats = cached_embeddings(reps.text.tolist())
            from bertopic import BERTopic
            from bertopic.vectorizers import ClassTfidfTransformer
            from umap import UMAP
            from hdbscan import HDBSCAN
            from sklearn.feature_extraction.text import CountVectorizer

            model = BERTopic(
                language="multilingual",
                embedding_model=None,
                umap_model=UMAP(
                    n_neighbors=min(config.neighbors, len(reps) - 1),
                    n_components=min(config.components, len(reps) - 2),
                    min_dist=config.min_dist,
                    metric="cosine",
                    random_state=config.seed,
                    n_jobs=1,
                    low_memory=True,
                ),
                hdbscan_model=HDBSCAN(
                    min_cluster_size=config.min_cluster_size,
                    min_samples=config.min_samples,
                    metric="euclidean",
                    cluster_selection_method="eom",
                    prediction_data=True,
                    core_dist_n_jobs=1,
                ),
                vectorizer_model=CountVectorizer(
                    token_pattern=r"(?u)\b[^\W\d_]{2,}\b",
                    ngram_range=(1, 2),
                    stop_words=STOPWORDS,
                ),
                ctfidf_model=ClassTfidfTransformer(reduce_frequent_words=True),
                top_n_words=10,
                calculate_probabilities=False,
                verbose=False,
            )
            assignments, _ = model.fit_transform(reps.text.tolist(), embeddings=vectors)
            topics, mapping, metrics = discover(
                model, frame, reps, vectors, assignments
            )
            dest = root / key
            dest.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix="stage-", dir=dest))
            run_id = mode + "-" + uuid.uuid4().hex
            model.save(
                str(staging / "model.pkl"),
                serialization="pickle",
                save_embedding_model=False,
            )
            np.savez_compressed(staging / "training_vectors.npz", vectors=vectors)
            result = dict(
                status="ready",
                mode=mode,
                fingerprint=key,
                run_id=run_id,
                generated_at=datetime.now(timezone.utc).isoformat(),
                config=config.fingerprint_config(),
                embedding=embedding_stats,
                topics=topics,
                document_mapping=mapping,
                metrics=metrics,
                trends=trends(mapping, config),
                elapsed_seconds=time.perf_counter() - started,
                label_notice="BERTopic ID는 요지코드가 아닙니다. 원본 요지 분포는 참고 통계이며 자동 수정에 사용하지 않습니다.",
            )
            atomic_json(staging / "result.json", result)
            atomic_json(staging / "document_mapping.json", mapping)
            staging.rename(dest / run_id)
            staging = None
            atomic_json(
                dest / (mode + ".json"), dict(result_path=run_id + "/result.json")
            )
            atomic_json(
                root / "job.json",
                dict(status="completed", mode=mode, run_id=run_id, fingerprint=key),
            )
            return result
        except Exception as exc:
            atomic_json(
                root / "job.json",
                dict(
                    status="failed",
                    mode=mode,
                    error=f"{type(exc).__name__}: {exc}",
                    fingerprint=key,
                ),
            )
            if staging:
                shutil.rmtree(staging)
            raise


def transform(texts, mode="all"):
    """Explicit offline use; never called by live routing. Loads only locally built artifacts."""
    result = current(mode)
    if result["status"] != "ready":
        raise RuntimeError("현재 설정의 학습 모델이 없습니다")
    from bertopic import BERTopic

    model = BERTopic.load(
        str(cache_root() / result["fingerprint"] / result["run_id"] / "model.pkl")
    )
    cleaned = [preprocess(x) for x in texts]
    if not cleaned or any(not x for x in cleaned):
        raise ValueError("빈 문서 입력")
    vectors, _ = cached_embeddings(cleaned)
    return [int(t) for t in model.transform(cleaned, embeddings=vectors)[0]]
