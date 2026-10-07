import argparse, json, os

# Independent process uses CPU; bound threads to protect live inference.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
from backend.analytics.bertopic_service import build


def main():
    parser = argparse.ArgumentParser(description="Offline VOC BERTopic batch")
    parser.add_argument("--mode", choices=["all", "z1", "both"], default="both")
    parser.add_argument(
        "--force", action="store_true", help="현재 fingerprint 모델도 재학습"
    )
    args = parser.parse_args()
    for mode in (["all", "z1"] if args.mode == "both" else [args.mode]):
        result = build(mode, args.force)
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in [
                        "mode",
                        "fingerprint",
                        "metrics",
                        "embedding",
                        "elapsed_seconds",
                    ]
                },
                ensure_ascii=False,
            )
        )
    from backend.analytics.bertopic_service import atomic_json, cache_root

    atomic_json(cache_root() / "job.json", dict(status="completed", mode=args.mode))


if __name__ == "__main__":
    main()
