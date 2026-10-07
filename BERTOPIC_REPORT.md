# BERTopic 구현 및 실제 검증 보고서

작성일: 2026-10-06. 현재 관리자 주소: http://127.0.0.1:8001/topics.html

## 적용 범위

기존 Qwen → Routing → Embedding Top-K → Ranking → 추천 보류 판단 → 사용자 승인 경로의 알고리즘을 변경하지 않았다. BERTopic은 별도 CPU 배치 프로세스와 읽기 전용 결과 API로 추가했다. 실시간 추천·승인에서 BERTopic fit/transform을 호출하지 않으며 라벨·부서·승인을 덮어쓰지 않는다. 서버 시작은 기존 이력 준비를 수행하지만 BERTopic을 학습하지 않는다.

원문 → 기존 MiniLM CPU Embedding → UMAP → HDBSCAN → c-TF-IDF로 학습한다. 한국어 보존을 위해 BERTopic language=multilingual을 명시했다. 기존 retrieval 벡터는 Qwen 요약 기반이므로 원문 벡터로 재사용하지 않는다. 대신 같은 모델로 텍스트 키 캐시를 만들고 전체/Z1/재학습 간 공유한다. 중복그룹마다 한 문서로 fit하며 통계는 원본 행과 독립 사례를 분리한다.

## 추가 파일

- backend/analytics/__init__.py
- backend/analytics/config.py: BER_TOPIC_* 지연 로딩 및 수치 검증
- backend/analytics/bertopic_service.py: 원문/Embedding 캐시, fingerprint, fit, 모델 저장/로드, 명시적 offline transform
- backend/analytics/topic_discovery.py: 원문 정규화, 대표 키워드/문서, raw/unique 통계, diversity/NPMI
- backend/analytics/topic_trend.py: 독립 사례 기준 기간/월별 집계, 증가/감소/신규 등장
- backend/analytics/topic_validation.py: 대상·중복 그룹을 제외한 과거 라벨 기반 Qwen 재검토 신호
- backend/analytics/api.py: 조회 API 및 별도 CPU 배치 실행
- backend/analytics/run_bertopic.py: 배치 CLI
- backend/analytics/evaluate.py: 저장된 Qwen 결과의 재검토 탐지 평가
- voc-ui/dist/topics.html, topics.css, topics.js: 기존 디자인을 사용하는 별도 관리자 화면
- tests/test_analytics.py
- scripts/test_bertopic_e2e.py, check_bertopic_production.py, check_bertopic_originals.py
- BERTOPIC_REPORT.md 및 outputs/bertopic_* 검증 산출물

## 수정한 기존 파일

- backend/main.py: 기존 StaticFiles mount 앞에 analytics router 등록
- backend/service.py: 기존 signature 계산식을 recommendation_signature 함수로 추출. 계산식/값과 추천 로직은 동일
- voc-ui/dist/index.html: 관리자 화면 링크 추가
- requirements.txt: BERTopic 패키지 추가
- .env.example: BER_TOPIC_* 설정 예시 추가
- README.md: 설치/배치/API/캐시/평가/한계 설명 추가

기존 app.js, styles.css, Routing/Ranking 구현은 변경하지 않았다. environment.yml은 requirements.txt를 참조하므로 그대로 사용한다. 원본 데이터 두 개와 원본 zip의 styles.css를 해시/바이트 비교해 동일함을 확인했다.

## 설치한 패키지

직접 추가: bertopic 0.17.4, umap-learn 0.5.12, hdbscan 0.8.44.
전이 의존성: plotly 7.1.0, llvmlite 0.50.0, numba 0.68.0, pynndescent 0.6.0.
Ubuntu Conda voc Python 3.11 환경에 설치했다. 추가 GPU/대형 Embedding 모델은 설치하지 않았다.

## 실행

```bash
conda activate voc
python -m pip install -r requirements.txt
python -m backend
# 관리자: http://127.0.0.1:8001/topics.html
python -m backend.analytics.run_bertopic --mode both
python -m backend.analytics.run_bertopic --mode z1
python -m backend.analytics.run_bertopic --mode both --force
python -m backend.analytics.evaluate
```

기본 배치는 현재 fingerprint 결과가 있으면 fit하지 않는다. --force 또는 관리자 재학습 체크박스는 새 모델을 생성하지만 이미 존재하는 원문 벡터는 재사용한다. 관리자 실행은 즉시 접수하고 별도 프로세스에서 CPU로 진행하며 중복 배치는 거부한다. 오류/진행은 job.json과 batch.log에 저장한다.

캐시: outputs/bertopic/<fingerprint>/{all,z1}.json 및 해당 run_id 디렉터리. 모델(model.pkl), metadata/statistics(result.json), 문서 매핑(document_mapping.json), 학습 벡터(training_vectors.npz)를 보존한다. 원문 Embedding 캐시는 outputs/bertopic/embeddings.sqlite3이다. 데이터 hash, 모델, 분석/전처리 버전, stopword 목록, 군집/UMAP/트렌드/경고 설정, split, Python 및 주요 패키지 버전이 fingerprint를 구성한다. 이전 run은 유지하되 현재 포인터와 다른 fingerprint의 결과를 화면에서 혼합하지 않는다. 로컬 모델 pickle은 동일 환경에서 재사용한다.

## 실제 학습 결과

| 범위 | 원본 행 | 독립 사례 | Topic 수 (Outlier 제외) | Outlier 원본 행 | Outlier 독립 사례 | 독립 Outlier 비율 |
|---|---:|---:|---:|---:|---:|---:|
| 전체 | 2500 | 2424 | 150 | 428 | 414 | 17.08% |
| Z1 | 50 | 50 | 4 | 2 | 2 | 4.00% |

Z1 군집은 18/14/9/7건과 Outlier2건이다. Topic2는 충전·콘센트·좌석 화면, Topic3은 아이·가족·유아 동반 패턴이 보인다. Topic0/1은 반려동물·수하물·좌석/편의·업무 공간 등 여러 제안이 섞여 있어 단일 신규 요지로 확정할 수 없다. 군집 ID는 기존 요지코드와 관계없고 재학습 시 달라질 수 있다. 문서를 실제로 검토한 해석이지 정답 라벨이 아니다.

최종 전체 diversity=0.9487, NPMI=0.1563. Z1 diversity=1.0000, NPMI=0.2163. NPMI는 독립 원문 unigram/bigram 공기 기반 top5 지표이며 미공기는 -1로 처리한다. 형태소 분석/전문가 coherence 평가를 대체하지 않는다. 숫자가 높아도 의미 있는 군집이라고 확정하지 않는다.

전체 학습의 최초 원문 벡터 신규 계산은 2424개였다. 이어진 Z1은 50개 모두 캐시를 사용했다. 설정/키워드 개선 및 강제 재학습도 신규 원문 벡터를 계산하지 않았다. 최초 전체 실행 약89초, 벡터 캐시 후 전체 fit 약25초, 같은 프로세스의 Z1 fit 약0.1초였으며 독립 프로세스의 라이브러리/UMAP 초기화 시간은 별도로 추가된다.

날짜 컬럼이 없으므로 트렌드는 '날짜 데이터 없음'으로 비활성화했다. 본문 날짜나 gen_batch를 접수 날짜로 만들어 쓰지 않는다.

## 재검토 신호 평가

현재 저장된 Qwen 결과의 경고 후보는 전체386건(대부분 과거 이력 포함). 이는 실제 오분류386건이라는 뜻이 아니다. 독립 holdout 중 분석된7건에서는 원본 라벨과 불일치4건, 경고1건, 검출된 불일치0건이었다. 이 작은 표본의 recall/precision은 둘 다0이며 현재 경고 기준의 성능 개선은 입증되지 않았다. 원본 더미 라벨도 오류 가능성이 있고 전체 원문 군집 기반 탐색 분석이므로 엄격한 미래 예측 holdout 평가와 다르다.

BERTopic 없음 대비 재검토 표시만 추가된다. 추천부서 변경0건, 자동 라벨 수정0건이며 잘못된 자동추천 감소 여부는 측정하지 않았다. 원본 요지 라벨은 Embedding/군집 학습 입력에 넣지 않았고, 평가 VOC의 라벨은 경고 생성이 끝난 뒤 평가에서만 비교했다.

## 실제 검증

- pytest: 17 passed, Starlette httpx deprecation warning 1개
- 관리자 API8개, 현재 결과 캐시 재사용, force 재학습, 벡터 재사용, 중복 배치409 확인
- 빠른 캐시 실행의 종료 상태가 계속 실행중으로 남던 문제를 수정하고 실제 배치 및 회귀 테스트로 검증
- 잘못된 BERTopic 설정 및 analytics 오류를 주입해도 기존 VOC 상세 API200 확인
- 실제 Chromium: 전체151개 목록(Outlier 포함), Z1 5개 목록, Topic 상세, 범위 변경, 날짜 없음, 새로고침 복원, 기존512개 VOC 목록, 브라우저 오류0
- 테스트가 VOC 분석/승인 POST를 보내지 않음을 확인
- 실제8001 서버 재시작 후 관리자 화면/데이터/API 재확인; Qwen 모델 ready 및 기존 검색 이력 사용 가능. 기존 백그라운드 이력 준비는 재개 중
- 원본 Excel/Master 및 styles.css 동일 확인

검증 자료: outputs/bertopic_e2e.json, bertopic_production_check.json, bertopic_original_checks.json, bertopic_admin.png, bertopic/evaluation.json.

## 현재 한계

한국어 형태소 분석을 사용하지 않아 일부 키워드가 일반 문구 또는 조사 포함 형태이고 군집이 혼합될 수 있다. 초기 min_cluster_size5는 전체에서 작은 군집150개를 생성하며 최적 설정이 아니다. 경고 임계값은 실험용이고 검증된 오분류 탐지기로 사용하면 안 된다. 원본 Z1을 기준으로 분석하며 새로 Qwen이 Z1으로 분류한 VOC만 별도 추적하는 실행 모드는 아직 없다. 일정/신규 건수 자동 배치, Topic ID의 여러 재학습 간 추적, 관리자 수동 Topic 이름 편집은 구현하지 않았다. 기존 VOC 화면에는 과도한 보조 정보를 추가하지 않았고 관리자 화면과 문서 매핑 API에서만 제공한다. 이번 작업은 이전 AUDIT_REPORT.md의 실시간 라우팅/승인 결함을 수정하는 작업과 별개다.
