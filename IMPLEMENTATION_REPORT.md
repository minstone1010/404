# 통합 구현 결과 (2026-10-06)

실제 실행 환경: WSL Ubuntu, Conda voc, Python 3.11, NVIDIA RTX 4060 8GB, Driver 595.95, PyTorch 2.14.1+cu130(CUDA 13.0 사용 가능), Transformers 5.18.0. nvidia-smi CUDA 13.2는 드라이버 지원 상한이며 실제 PyTorch 런타임은 13.0입니다.

1. 기존 구조 분석: Notebook 셀/함수 의존성을 추출했습니다. 원본(DB형식) 2,500행·23컬럼, 요지코드 40개, Master 7시트, 정적 voc-ui의 하드코딩·localStorage 흐름을 확인했습니다. 전체 시트 컬럼은 outputs/structure_report.json에 보존했습니다.
2. 생성 파일: backend의 설정·Notebook 추출 로직·모델·검증·routing·service·SQLite·API·CLI 모듈, 환경 파일, .env, tests 및 scripts, README, 본 보고서, 실행 결과/캐시.
3. 수정 파일: 압축에서 가져온 voc-ui/dist/app.js와 index.html. CSS는 바이트 단위로 원본과 동일합니다. 원본 파일 네 개는 덮어쓰지 않았습니다.
4. 대체 코드: Colab/Drive/content/pip/display/ipywidgets/셀 순서를 Python 설정·모듈·웹으로 대체했습니다. samples는 빈 목록으로 시작해 API로 채우며 localStorage 승인 저장과 샘플 초기화는 제거했습니다. 승인 CSV는 동시 쓰기에 적합한 SQLite 트랜잭션·이벤트 저장으로 대체했습니다.
5. 최종 구조: backend/, voc-ui/dist/, data/, reference/, scripts/, tests/, outputs/ + 환경·README 파일. 상세 트리는 README에 있습니다.
6. Conda 생성: conda env create -f environment.yml. 이번 PC에서는 기존 WSL voc(Python 3.11)을 재사용했습니다.
7. 설치: conda activate voc 후 python -m pip install -r requirements.txt. pip check 통과. 실행 중인 환경을 재설치할 필요는 없습니다.
8. Backend: 프로젝트 루트에서 python -m backend 또는 uvicorn backend.main:app --host 127.0.0.1 --port 8001 --workers 1.
9. 웹: http://127.0.0.1:8001. 별도 frontend 서버/빌드 없이 기존 dist를 FastAPI가 제공합니다.
10. 모델 변경: .env의 QWEN_MODEL. 기본 Qwen/Qwen3.5-2B + NF4 4bit. 임의 다른 모델 전환은 없습니다. 임베딩 모델은 기존 multilingual MiniLM 그대로이며 CPU 실행입니다.
11. 데이터 변경: .env의 VOC_PATH와 ROUTING_MASTER_PATH 후 서버 재시작. 입력 파일 해시/코드북/Master/모델 설정이 변경되면 캐시가 구분됩니다. 원본은 수정하지 않습니다.
12. 평가: python -m backend.cli prepare-history 후 python -m backend.cli evaluate. 제한 시험은 --limit 3 --allow-partial이며 API 서버 이용 시 --api-url http://127.0.0.1:8001. A/B/C 비교는 동일 인덱스 잠금으로 실행되며 최종 제한 평가의 comparison_index_consistent=true입니다.
13. 한계: 전체 1,988건 과거 이력 준비와 512건 전체 평가는 아직 완료하지 않았습니다. 부분 이력 상태로 사용 가능하며 서버가 백그라운드 준비를 이어갑니다. Master 미매칭과 Qwen 구조/의미 오류가 발생할 수 있습니다. 지역·기능·scope 지표는 독립 정답이 없어 부서 Master 속성 기반 proxy입니다. 로컬 단일 프로세스, 외부 전송 없음, Windows native 실행 미검증. 선택적 GPU 커널 없이 정상 PyTorch 구현을 사용하므로 최초 준비 시간이 깁니다.
14. 실제 테스트: 회귀 6 passed, pip check 정상, Python compileall/JS 문법 정상, 실제 Chromium 512건 렌더/검색/분석 전 승인 차단과 실제 Qwen·Embedding 분석→추천→승인→새로고침→보류→새로고침 통과. 브라우저 오류 0. Excel export API 200. 시험 결정은 별도 JSON 이벤트 파일에 보존한 뒤 활성 테이블에서 제거했습니다.

최종 제한 평가는 과거 65건·검토 VOC 3건으로 수행했습니다. 주요지 Accuracy 33.3%, Macro-F1 0.20, 부서 Top-1 0.0%, Top-3 0.0%. Coverage A/B/C는 33.3%/33.3%/100.0%입니다. **추천 가능 판정이 정답이라는 뜻은 아니며, 이 제한 시험으로 Routing의 성능 향상을 주장하지 않습니다.** 실제 E2E에서 에어컨 민원을 열차지연으로 분류한 오분류가 확인되었습니다. 의미 정확도 개선 및 전체 데이터 평가가 필요합니다.

분석 원 측정 평균 9.37초. 평가 중 현재 요청은 이미 저장된 분석을 재사용하여 평균 0.084초였습니다. 이 값은 최초 전체 분석시간과 다릅니다. 실측 GPU 메모리와 현재 진행률은 outputs/final_runtime_stats.json을 참조합니다.

보고서 작성 시 서버 상태: 검색 가능한 과거 76/1988건, 모델 준비 True, 초기화 오류 None, 활성 시험 결정 0건. 이후 계속 변하는 진행률은 /api/stats에 있습니다.

## 추가 수정: 분석 버튼 실행과 평가 캐시 분리

원인: 기존 GET 목록/상세가 analyses 테이블의 평가·시험 캐시까지 화면 결과로 복원했습니다. 서버 백그라운드 준비 대상은 과거 검색 이력이며 검토 VOC를 자동 실행하는 경로는 없었지만, 저장 출처를 구분하지 않아 미실행처럼 보이는 VOC에도 결과가 표시됐습니다.

수정: 사용자 분석을 manual_analyses 테이블에 별도 저장합니다. 화면 조회는 이 테이블만 사용하고 평가 API/CLI는 화면 결과를 변경하지 않습니다. 분석 버튼은 새 Qwen 분석을 실행하고 실행 출처·UTC 시각을 보존합니다. 저장된 사용자 결과는 새로고침에서 복원하며 재분석 버튼으로 구분합니다. 이전 출처 미기록 캐시와 승인 기록은 삭제하지 않았습니다. 재분석 실패 시 이전 성공 결과를 그대로 표시하지 않고 새 오류 결과를 표시합니다.

검증: 8 passed. 실제 Chromium에서 페이지 열기·선택·검색·새로고침 동안 분석 POST 0회, 버튼 클릭 후 정확히 1회, 실제 Qwen 실행, 결과의 새로고침 유지, 자동 승인 없음, 브라우저 오류 0건. Windows localhost에서 API 및 export HTTP 200 확인. 분실물 VOC 900010의 검증용 화면 결과는 보고서에 보존 후 제거했으며 분석대기/빈 결과 상태를 확인했습니다. 검증 기록: outputs/manual_analysis_browser_report.json.
