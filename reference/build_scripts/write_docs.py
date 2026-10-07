from pathlib import Path
import json,hashlib,zipfile
import openpyxl
report={'files':{},'source_preservation':{}}
for p in Path('data').glob('*.xlsx'):
 workbook=openpyxl.load_workbook(p,read_only=True,data_only=True); sheets={}
 for sheet in workbook:
  iterator=sheet.values; headers=next(iterator); count=sum(1 for _ in iterator); sheets[sheet.title]={'data_rows':count,'columns':list(headers)}
 report['files'][p.name]=sheets
 original=Path('/mnt/c/Users/win/Desktop')/p.name
 report['source_preservation'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(original.read_bytes()).hexdigest()
with zipfile.ZipFile('/mnt/c/Users/win/Desktop/voc-ui.zip') as z:
 report['source_preservation']['styles.css']=z.read('voc-ui/dist/styles.css')==Path('voc-ui/dist/styles.css').read_bytes()
Path('outputs/structure_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
Path('README.md').write_text('''# VOC Desk: 기존 Notebook + Routing Master + voc-ui 통합

현재 PC의 **WSL Ubuntu / Conda voc / Python 3.11**에서 실행하도록 구성했습니다. Windows 브라우저는 http://127.0.0.1:8001 에 접속합니다. 네 원본 파일은 유지했고 UI의 기존 CSS를 변경하지 않았습니다. 최신 공식 조직 조회 시스템이 아니라 제공된 더미 라벨을 검증하는 프로젝트입니다.

## 실행

WSL Ubuntu 터미널에서:

```bash
cd /home/ubuntu/VOC-System_2안
source ~/miniconda3/etc/profile.d/conda.sh
conda activate voc
python -m backend
```

현재 voc 환경은 설치되어 있습니다. 새 PC/환경에서는 다음 중 하나를 사용합니다:

```bash
conda env create -f environment.yml
conda activate voc
# 또는
conda create -n voc python=3.11 pip -y
conda activate voc
python -m pip install -r requirements.txt
cp .env.example .env
python -m backend
```

직접 Uvicorn으로 실행할 수도 있습니다:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --workers 1
```

`python -m backend`는 .env HOST/PORT를 읽습니다. Uvicorn 명령의 host/port는 명령 인수를 따릅니다. 모델 중복 로딩과 전역 Notebook 데이터 충돌 방지를 위해 **workers=1**, `--reload` 미사용을 권장합니다. 현재 8000 포트에는 사용자의 다른 서비스가 실행 중이므로 기본 포트는 8001입니다. 이미 VOC 서버가 실행 중이면 새 서버를 중복 실행하지 말고 브라우저를 엽니다. 종료는 실행 터미널에서 Ctrl+C입니다.

## 최초 시작과 과거 이력

Excel과 Master를 읽고 캐시된 과거 이력을 인덱싱합니다. 모델은 프로세스에서 한 번 로딩하며 새 과거 VOC 분석은 백그라운드에서 이어집니다. 검토대상 목록은 즉시 사용할 수 있고 이력이 준비되면 추천을 실행할 수 있습니다. 상단에 현재 검색 가능한 이력 수가 표시됩니다. **부분 이력 추천은 전체 이력 평가가 아닙니다.** 추천 상세에도 당시 history_count를 저장합니다.

과거 1,988건의 Qwen 분석은 처음에 시간이 오래 걸립니다. 세 단계 프롬프트와 strict JSON 검증을 적용하며 검증 실패 시 오류를 전달해 한 번 재시도합니다. 끝까지 실패한 건은 분석오류로 보존하고 검색 이력에서 제외합니다. 준비가 끝났더라도 성공/실패 건수는 구분됩니다. 중단 후 재시작하면 완료된 분석을 재사용합니다. 기본 서버는 시작할 때 미완료/오류 이력을 재시도합니다.

전체 캐시를 먼저 준비하려면 서버를 종료하고:

```bash
python -m backend.cli prepare-history
python -m backend
```

제한 시험은 `python -m backend.cli prepare-history --limit 12`입니다. 이를 전체 준비 완료로 취급하지 않습니다. 데이터·Master·모델·주요 검색 설정이 바뀌면 signature가 바뀌어 기존 분석 캐시를 재사용하지 않습니다. 인덱스 캐시는 내용과 ID 순서 해시로 구분합니다. 이력은 startup에서 메모리에 유지하고 신규 분석 누적 시 갱신하며, 웹 추천 요청마다 전체 임베딩을 다시 계산하지 않습니다.

## 기존 구조 분석과 재사용

- Notebook: 21개 셀. 데이터 검증, 중복 ID/동일 본문 union-find 그룹, SHA256 기반 80/20 holdout, topic/cause/routing 세 번의 Qwen 호출, Master 조회, SentenceTransformer 검색, 가중 점수, CSV 승인과 ipywidgets UI.
- VOC Excel: 읽는 법 / 데이터 / 요약 / 분포검증(1만건) / 개인정보 / 요지코드 / 원본(DB형식). 실행 입력은 원본(DB형식) 2,500행·23컬럼과 요지코드 40개. 데이터 시트에는 설명 행도 있어 실행 입력으로 사용하지 않습니다.
- Master: README / regional_hq_master(12) / location_master(58) / department_master(60) / channel_master(8) / topic_function_map(40) / routing_rules(8). 실제 필수 컬럼을 검증합니다. README와 routing_rules의 설명은 참조자료로 다루며 사용자 요청의 모델명·fallback 요구사항을 우선합니다.
- UI zip: voc-ui/dist/index.html, styles.css, app.js + preview.jpg + README.md. app.js의 samples와 localStorage 승인 상태를 API 호출로 대체했습니다. 기존 화면 렌더러와 CSS·레이아웃·색상을 유지합니다.

`backend/notebook_logic.py`는 원본 소스에서 함수와 초기화 로직을 추출한 모듈입니다. `clean_text`, `clean_id`, `assert_columns`, `complaint_text`, `lookup_location`, `lookup_function`, `attach_department_attributes`, `parse_topic/cause/routing`, `analyze_topic/cause/routing`, `cause_text`, `embedding_text`, `retrieve_similar_vocs`, `rank_departments`, `recommend_department`, `record_recommendation`을 재사용했습니다. 원본 셀 소스는 reference/에서 비교할 수 있습니다.

변경한 부분: 모델 로더, strict JSON 검증 및 재시도, `parse_channel` Master 조회, 단계적 후보 fallback, 서버 캐시, SQLite `load_approvals/save_decision/export_results`, API 어댑터. Notebook의 score=`0.7 * mean_similarity + 0.3 * frequency`와 유사도/근거 건수/점수 차이 보류 기준은 유지합니다. UI는 최대 TOP_N(기본 3) 부서 후보를 표시하며 근거 부족이면 추천 보류로 표시합니다. 후보가 3개 미만이면 실제 후보만 표시합니다.

Colab mount, /content, %pip, Jupyter display, ipywidgets 승인창, 셀 실행 순서, 모델 삭제 후 임베딩 로딩, 테스트 print는 웹 실행 경로에서 제거/대체했습니다. 원본 Notebook을 수정하거나 삭제하지 않았습니다.

## 데이터 누수 방지와 Routing

원본 handling_team과 topic_code는 evaluation_truth_df에 격리합니다. Service.row()와 analyze() 경계에서 평가 대상 handling_team, 원본 topic_code, 출발/도착역을 전달하지 않습니다. Qwen에는 본문·코드북·직전 분석만 전달합니다. 과거 이력의 handling_team만 부서 속성 연결과 Ranking 라벨로 사용합니다. 중복그룹이 검색/평가 양쪽에 존재하지 않으며 검색 함수는 자기 ID·동일 그룹·같은 본문을 추가 제외합니다. 원본 더미 부서명을 수정하지 않습니다.

Qwen은 위치 후보/범위와 의미만 판단합니다. 관할본부·조직·업무기능은 Master에서 조회합니다. 위치 조회는 원본 Notebook의 정확 일치 방식으로 광주/광주송정 같은 오매칭을 방지합니다. 미매칭/모호한 위치는 화면에 표시하고 검색은 계속합니다.

fallback: 지역+기능 후보가 충분하면 사용 → 부족하면 같은 지역/scope → 지역 불확실하면 기능 중심 → 모두 불명확하거나 후보가 없으면 검색 가능한 전체 이력. 전국형은 우선 본사/전국 조직을 사용합니다. fallback 단계는 추천 근거에 기록합니다. 접수경로는 원본 intake_channel을 보존하고 channel_master로 정규화하며 미입력/미매핑은 확인 필요입니다.

JSON null, 문자열 "null", 빈 문자열, 누락, 파싱 실패, 모델 오류를 구분합니다. 선택적 부요지/위치만 실제 JSON null을 허용합니다. 분석 실패는 error, failed_stage, raw response, validation_errors로 남기며 0/빈 정상 결과로 바꾸지 않습니다.

## 파일 구조

```text
backend/
  __main__.py       .env 기반 서버 실행
  main.py           FastAPI + 기존 정적 UI
  config.py         한 곳에서 설정 관리
  notebook_logic.py 원본 Notebook 추출 로직
  models.py         Qwen / SentenceTransformer 단일 로딩
  validation.py     구조 검증
  routing.py        원본 후보 제한의 fallback 개선
  service.py        분석·캐시·검색·추천 통합
  decision.py       SQLite 영속 저장 및 Excel export
  cli.py            이력 준비·A/B/C 평가·export
voc-ui/dist/        기존 UI(index.html/app.js 수정, styles.css 유지)
data/               원본 Excel 두 개의 동일 복사본
reference/          원본 Notebook, 원본 UI JS/HTML, 추출 셀, 분석 과정 스크립트
scripts/            재실행 가능한 smoke/E2E 테스트
 tests/             데이터 누수·파싱·Master·fallback·저장 테스트
outputs/            voc.sqlite3, embedding-*.npz, 평가 JSON, 테스트 보고서/화면
.env.example / .env / requirements.txt / requirements-test.txt / environment.yml
README.md / IMPLEMENTATION_REPORT.md
```

## 설정 변경

`.env`의 `QWEN_MODEL=Qwen/Qwen3.5-2B` 한 곳에서 모델명을 바꾸고 서버를 재시작합니다. 기본 `QWEN_QUANTIZATION=4bit`, `QWEN_DEVICE=cuda`, `EMBEDDING_DEVICE=cpu`입니다. 4bit를 해제하려면 `none`을 사용합니다. CPU Qwen은 device=cpu, quantization=none을 함께 설정해야 하며 느립니다. 모델 오류 시 다른 모델로 자동 전환하지 않습니다. 모델 계열 config에 따라 Qwen3.5의 multimodal 로더 또는 causal LM 로더를 선택합니다.

`VOC_PATH`, `ROUTING_MASTER_PATH`, `OUTPUT_PATH`를 변경하고 서버를 재시작합니다. 상대경로 기준은 프로젝트 루트이고 절대경로도 가능합니다. WSL에서는 Windows 파일을 `/mnt/c/Users/win/Desktop/...`로 지정합니다. 원본 Excel/Master를 쓰거나 덮어쓰는 코드는 없습니다. 결과는 별도 SQLite에 보존하고 `http://127.0.0.1:8001/api/export`에서 Excel을 내려받습니다.

TOP_K, TOP_N, MIN_SIMILARITY, MIN_SUPPORT, MIN_SCORE_MARGIN, HISTORY_FRACTION, SPLIT_MODE, HOST, PORT도 .env에서 관리합니다. holdout이 기본이며 demo는 자기/중복을 제외한 데모 검색 용도로만 사용합니다. demo에서는 holdout 평가를 하지 않습니다.

## API / 승인

GET /api/vocs, /api/vocs/{id}, /api/vocs/{id}/recommendations, /api/departments, /api/stats, /api/export.
POST /api/vocs/{id}/analyze, /api/vocs/{id}/decision. 분석 API의 mode=A/B/C는 비교 평가용이며 UI는 C를 사용합니다.

상태: 분석대기 → 분석완료 → 확인대기 → 사용자 클릭 후 승인완료 또는 보류. 실패한 분석은 별도 분석오류입니다. 저장실패는 웹 메시지로 표시하고 서버 상태를 승인으로 변경하지 않습니다. 저장되는 AI 결과에는 분석, 위치·Master 매핑, scope, Top-3, 점수·근거, 필터, 추천 보류 이유, raw output, 처리시간과 모델 정보를 포함합니다. 결정은 최종부서·상태·메모·UTC 시각·AI 추천·signature와 이벤트 이력을 별도로 저장합니다. 외부 부서 전달 기능은 없습니다.

## 평가

서버를 종료한 상태에서 전체 이력을 준비한 후:

```bash
python -m backend.cli prepare-history
python -m backend.cli evaluate
```

평가 VOC 일부만: `python -m backend.cli evaluate --limit 20`.
이력 일부로 기능 시험: `python -m backend.cli evaluate --limit 3 --allow-partial`.
실행 중 서버를 이용해 두 번째 GPU 모델 로딩을 피하는 시험: `python -m backend.cli evaluate --limit 3 --allow-partial --api-url http://127.0.0.1:8001`.

결과: outputs/evaluation.json 및 evaluation_records.json. A=전체, B=지역/scope, C=지역+기능+scope 검색 비교. 주요지 Accuracy/Macro-F1, 부서 Top-1/Top-3 Accuracy, Coverage, 보류율, 분석/전체 처리시간, GPU peak allocated를 기록합니다. Top-1 후보 정확도와 실제 추천 Coverage는 분리합니다. API 모드는 서버 /api/stats의 GPU 값을 참조합니다. 서버가 이력을 늘리는 중인 제한 평가는 비교 인덱스가 달라질 수 있으므로 완성된 이력과 고정 인덱스에서 최종 비교하세요.

**원본에 독립적인 관할지역/업무기능/scope 정답 컬럼은 없습니다.** 해당 항목은 실제 handling_team을 Master에 연결해서 얻은 proxy 정답으로만 보고하고 지표 이름에 proxy를 붙입니다. 독립적인 정답 정확도라고 주장하지 않습니다. 전체 성능 평가를 완료하기 전에는 제한 시험 수치를 일반화하지 않습니다.

## 실제 검증

검증 결과와 한계는 IMPLEMENTATION_REPORT.md와 outputs/e2e_report.json에 기록합니다. 회귀 테스트:

```bash
python -m pytest -q
# 브라우저 테스트 도구는 실행 의존성과 별도
python -m pip install -r requirements-test.txt
python -m playwright install --with-deps chromium
python scripts/browser_smoke.py
# 실제 분석 + 시험 승인/보류를 저장하는 테스트(더미 VOC 900001 사용)
python scripts/e2e_real.py
```

E2E는 실험용 결정 이벤트를 생성하므로 별도 OUTPUT_PATH 사용을 권장합니다. 이번 작업의 시험 결정은 e2e_decision_events.json에 보존하고 활성 결정 테이블에서 제거했습니다. 분석은 승인 없이도 저장되지만 승인 상태는 명시적 버튼 클릭 때만 저장됩니다.

## 알려진 한계

Master는 프로젝트용 제한 기준표이며 최신 코레일 전체 조직/역을 보장하지 않습니다. Qwen 분석이 구조적으로 유효해도 의미 오분류나 근거 없는 설명이 나올 수 있어 최종 담당자 검토가 필요합니다. 임시 보류 기준을 성능 확률로 표시하지 않습니다. 현재는 로컬 단일 사용자·단일 프로세스용이며 인증·외부 전달 기능을 추가하지 않았습니다. Qwen3.5의 선택적 CUDA 가속 커널(causal-conv1d/flash-linear-attention)이 없는 환경에서는 정상적인 PyTorch 구현으로 동작하지만 느립니다. 이번 설치에서 실제 CPU fallback 임베딩과 4bit Qwen GPU 실행을 검증했습니다. Windows native Conda 실행은 별도 검증하지 않았습니다.
''',encoding='utf-8')
