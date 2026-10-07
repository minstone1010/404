from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def path(name, default):
    p = Path(os.getenv(name, default))
    return p if p.is_absolute() else ROOT / p


@dataclass(frozen=True)
class Settings:
    qwen_model: str = os.getenv("QWEN_MODEL", "Qwen/Qwen3.5-2B")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    voc_path: Path = path("VOC_PATH", "data/voc_dummy_2500_v3_해설판.xlsx")
    master_path: Path = path(
        "ROUTING_MASTER_PATH", "data/korail_voc_routing_master.xlsx"
    )
    output: Path = path("OUTPUT_PATH", "outputs")
    device: str = os.getenv("QWEN_DEVICE", "cuda")
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    quantization: str = os.getenv("QWEN_QUANTIZATION", "4bit")
    split_mode: str = os.getenv("SPLIT_MODE", "holdout")
    history_fraction: float = float(os.getenv("HISTORY_FRACTION", "0.8"))
    top_k: int = int(os.getenv("TOP_K", "10"))
    top_n: int = int(os.getenv("TOP_N", "3"))
    min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.55"))
    min_support: int = int(os.getenv("MIN_SUPPORT", "2"))
    min_score_margin: float = float(os.getenv("MIN_SCORE_MARGIN", "0.03"))
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8001"))
    startup_models: bool = os.getenv("STARTUP_MODELS", "true").lower() == "true"


settings = Settings()
if settings.top_k < 1 or settings.top_n < 1 or settings.min_support < 1:
    raise ValueError("검색 설정은 양수여야 합니다")
if settings.device not in {"cuda", "cpu"} or settings.quantization not in {
    "4bit",
    "none",
}:
    raise ValueError("모델 설정 오류")
settings.output.mkdir(parents=True, exist_ok=True)
