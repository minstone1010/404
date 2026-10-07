import re, unicodedata, hashlib, json
from collections import Counter
import numpy as np

STOPWORDS = [
    "오늘",
    "문의",
    "요청",
    "확인",
    "답변",
    "주세요",
    "합니다",
    "했습니다",
    "있습니다",
    "그냥",
    "정말",
    "너무",
    "관련",
    "이번",
    "때문",
    "그리고",
    "해서",
    "하는",
    "있는",
    "것으로",
    "저는",
    "제가",
    "이런",
    "해당",
    "다시",
    "대한",
    "이용",
    "코레일",
]
STOPWORDS += [
    "있으면",
    "좋겠습니다",
    "같습니다",
    "안녕하세요",
    "안녕하십니까",
    "싶습니다",
    "좋겠어요",
    "어제",
    "최근",
    "제안",
    "제안드립니다",
    "했는데",
    "있어서",
    "있는지",
    "있는데",
    "있어",
    "이번에",
    "지난",
    "조금",
    "따로",
    "같은",
    "다른",
    "다니면서",
    "다니는",
    "있도록",
    "때마다",
    "열차",
    "기차",
    "서비스",
    "새벽",
    "말씀",
    "부탁드립니다",
    "검토",
    "생각이",
    "드는",
    "때는",
    "하면",
    "좀",
    "더",
    "것",
    "수",
    "많이",
    "혹시",
    "않아",
    "아직",
    "하기",
    "통해",
    "대해",
    "드립니다",
    "가능한",
    "새로운",
]


def preprocess(text):
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", " ", text)
    text = re.sub(r"(?<!\d)0\d{1,2}[- ]\d{3,4}[- ]\d{4}(?!\d)", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def discover(model, frame, representatives, vectors, assignments):
    topics = []
    unique_total = len(representatives)
    mapped = dict(zip(representatives.case_group_id, map(int, assignments)))
    frame = frame.copy()
    frame["topic_id"] = frame.case_group_id.map(mapped)
    from sklearn.feature_extraction.text import CountVectorizer

    analyzer = CountVectorizer(
        token_pattern=r"(?u)\b[^\W\d_]{2,}\b", ngram_range=(1, 2), stop_words=STOPWORDS
    ).build_analyzer()
    token_sets = [set(analyzer(x)) for x in representatives.text]
    coherence = []
    all_words = []
    for topic_id in sorted(set(map(int, assignments))):
        positions = np.flatnonzero(np.asarray(assignments) == topic_id)
        group_rows = representatives.iloc[positions]
        raw = frame.loc[frame.topic_id.eq(topic_id)]
        terms = model.get_topic(topic_id) or []
        words = [w for w, score in terms if w and score > 0][:10]
        all_words.extend(words if topic_id != -1 else [])
        center = vectors[positions].mean(axis=0)
        center /= max(np.linalg.norm(center), 1e-9)
        ordered = positions[np.argsort(-(vectors[positions] @ center), kind="stable")][
            :3
        ]
        docs = [
            dict(
                id=str(representatives.iloc[p].id),
                text=str(representatives.iloc[p].text),
                case_group_id=str(representatives.iloc[p].case_group_id),
            )
            for p in ordered
        ]
        labels = Counter(group_rows.source_topic_code)
        topics.append(
            dict(
                topic_id=topic_id,
                topic_name=(
                    "미군집 (Outlier)"
                    if topic_id == -1
                    else " / ".join(words[:3]) or "대표 키워드 없음"
                ),
                representative_words=words,
                representative_documents=docs,
                document_count=len(group_rows),
                document_ratio=len(group_rows) / unique_total,
                raw_document_count=len(raw),
                unique_case_count=len(group_rows),
                source_label_distribution=dict(labels),
            )
        )
        if topic_id != -1:
            local = []
            for i, a in enumerate(words[:5]):
                for b in words[:5][i + 1 :]:
                    pa = sum(a in s for s in token_sets) / unique_total
                    pb = sum(b in s for s in token_sets) / unique_total
                    pab = sum(a in s and b in s for s in token_sets) / unique_total
                    if pa and pb:
                        local.append(
                            -1.0
                            if pab == 0
                            else (
                                float(np.log(pab / (pa * pb)) / -np.log(pab))
                                if pab < 1
                                else 0.0
                            )
                        )
            coherence.extend(local)
    mapping = [
        dict(
            id=str(r.id),
            case_group_id=str(r.case_group_id),
            topic_id=int(r.topic_id),
            source_topic_code=str(r.source_topic_code),
            role=str(r.role),
            date=r.date,
        )
        for r in frame.itertuples()
    ]
    outlier = sum(x["unique_case_count"] for x in topics if x["topic_id"] == -1)
    metrics = dict(
        topic_count=sum(x["topic_id"] != -1 for x in topics),
        raw_document_count=len(frame),
        unique_case_count=unique_total,
        outlier_unique_count=outlier,
        outlier_raw_count=int(frame.topic_id.eq(-1).sum()),
        outlier_ratio=outlier / unique_total,
        topic_diversity=len(set(all_words)) / len(all_words) if all_words else None,
        coherence_npmi=float(np.mean(coherence)) if coherence else None,
        coherence_method="독립 원문 unigram/bigram 공기 기반 top-5 NPMI; 미공기 -1; 한국어 형태소 분석 미적용",
    )
    return topics, mapping, metrics
