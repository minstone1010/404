from dataclasses import dataclass, asdict, field
from pathlib import Path
import os, math
from backend.config import settings


@dataclass(frozen=True)
class AnalyticsConfig:
    min_cluster_size: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_MIN_CLUSTER_SIZE", "5"))
    )
    min_samples: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_MIN_SAMPLES", "2"))
    )
    neighbors: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_UMAP_NEIGHBORS", "10"))
    )
    components: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_UMAP_COMPONENTS", "5"))
    )
    min_dist: float = field(
        default_factory=lambda: float(os.getenv("BER_TOPIC_UMAP_MIN_DIST", "0.0"))
    )
    seed: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_RANDOM_SEED", "42"))
    )
    dominant_ratio: float = field(
        default_factory=lambda: float(
            os.getenv("BER_TOPIC_DOMINANT_LABEL_RATIO", "0.8")
        )
    )
    warning_threshold: float = field(
        default_factory=lambda: float(os.getenv("BER_TOPIC_WARNING_THRESHOLD", "0.1"))
    )
    warning_min_cases: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_WARNING_MIN_CASES", "5"))
    )
    trend_days: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_TREND_DAYS", "30"))
    )
    trend_min_cases: int = field(
        default_factory=lambda: int(os.getenv("BER_TOPIC_TREND_MIN_CASES", "5"))
    )
    trend_growth: float = field(
        default_factory=lambda: float(os.getenv("BER_TOPIC_TREND_GROWTH", "0.5"))
    )
    date_column: str = field(
        default_factory=lambda: os.getenv("BER_TOPIC_DATE_COLUMN", "")
    )
    preprocessing_version: str = "raw-nfc-pii-v1"

    def validate(self):
        if (
            self.min_cluster_size < 2
            or min(
                self.min_samples,
                self.neighbors,
                self.components,
                self.warning_min_cases,
                self.trend_days,
                self.trend_min_cases,
            )
            < 1
        ):
            raise ValueError("BERTopic 정수 설정 범위 오류")
        for value in [self.min_dist, self.dominant_ratio, self.warning_threshold]:
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("BERTopic 비율 설정 범위 오류")
        if not math.isfinite(self.trend_growth) or self.trend_growth < 0:
            raise ValueError("트렌드 증가율 설정 오류")
        return self

    def fingerprint_config(self):
        return asdict(self)


def cache_root():
    return settings.output / "bertopic"
