import pandas as pd


def trends(mapping, config):
    frame = pd.DataFrame(mapping)
    if frame.empty or not frame.date.notna().any():
        return dict(enabled=False, reason="날짜 데이터 없음", topics=[])
    frame["date"] = pd.to_datetime(frame.date, errors="coerce", utc=True)
    frame = (
        frame.dropna(subset=["date"])
        .sort_values(["date", "id"])
        .drop_duplicates("case_group_id")
    )
    if frame.empty:
        return dict(enabled=False, reason="유효한 날짜 데이터 없음", topics=[])
    anchor = frame.date.max().normalize() + pd.Timedelta(days=1)
    recent_start = anchor - pd.Timedelta(days=config.trend_days)
    previous_start = recent_start - pd.Timedelta(days=config.trend_days)
    output = []
    for topic_id, rows in frame.groupby("topic_id"):
        if topic_id == -1:
            continue
        recent = int(((rows.date >= recent_start) & (rows.date < anchor)).sum())
        previous = int(
            ((rows.date >= previous_start) & (rows.date < recent_start)).sum()
        )
        growth = (recent - previous) / previous if previous else None
        new = bool(
            recent >= config.trend_min_cases
            and previous == 0
            and not (rows.date < recent_start).any()
        )
        output.append(
            dict(
                topic_id=int(topic_id),
                total_unique_cases=len(rows),
                recent_count=recent,
                previous_count=previous,
                growth_rate=growth,
                decline_rate=max(-growth, 0) if growth is not None else None,
                new_topic=new,
                emerging=bool(
                    recent >= config.trend_min_cases
                    and (new or growth is not None and growth >= config.trend_growth)
                ),
                monthly_counts={
                    str(k): int(v)
                    for k, v in rows.groupby(rows.date.dt.strftime("%Y-%m"))
                    .size()
                    .items()
                },
            )
        )
    return dict(
        enabled=True,
        anchor=anchor.isoformat(),
        recent_start=recent_start.isoformat(),
        previous_start=previous_start.isoformat(),
        date_coverage=len(frame) / max(len({r["case_group_id"] for r in mapping}), 1),
        topics=output,
    )
