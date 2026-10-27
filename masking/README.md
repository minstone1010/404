# 로컬 개인정보 마스킹 모델

한국어 민원의 **이름·주소·이메일·휴대폰번호·승차권번호**를 마스킹하는 Windows GPU 실행 버전입니다. 다섯 유형 BERT와 이름 전용 BERT에 규칙 탐지를 결합합니다. 모델 설치 후 실제 마스킹에는 정답 라벨이나 인터넷 연결이 필요하지 않습니다. 현재 기본 실행에는 Qwen이 필요하지 않습니다.

## 설치

검증 환경은 Windows, Python 3.12, RTX 5070 Ti 16GB입니다. CPU 전용 실행 버전은 이 폴더에 포함하지 않았습니다. 저장소를 받은 뒤 `masking` 폴더에서 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_weights.py
```

`setup_weights.py`는 `masking-v2026.10.27` Release가 게시된 후 가중치 두 개를 내려받아 SHA-256과 크기를 검사합니다. 두 파일 합계는 약 2.67GB입니다. 코드만 다운로드한 상태로는 실행할 수 없습니다.

인터넷이 없는 PC에서는 준비 PC에서 받은 가중치와 동일한 Windows/Python 환경용 설치 파일을 반입합니다. Release 파일 두 개가 들어 있는 폴더를 지정해 설치할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe setup_weights.py --from-dir "D:\모델가중치"
.\.venv\Scripts\python.exe setup_weights.py --check-only
```

가중치 배치 경로와 검증값은 `weights_manifest.json`에 있습니다. 토크나이저와 설정 파일은 코드와 함께 제공합니다.

## 실행

`실행.bat`를 실행하거나 다음 명령을 사용합니다.

```powershell
.\.venv\Scripts\python.exe mask.py
```

엑셀 처리:

```powershell
.\.venv\Scripts\python.exe mask.py --input "입력.xlsx" --output "마스킹결과.xlsx" --sheet "시스템 양식" --column full_text
```

지원 입력은 `full_text` 열이 있는 표 또는 `접수번호·제목·질문·답변·처리자` 열이 있는 시스템 양식입니다. 원본 저장은 기본적으로 꺼져 있습니다. 일반 앱 출력은 민원별 합본 마스킹 문장입니다.

제목과 질문은 다섯 유형 탐지를 적용합니다. 처리자 열은 이름 필드 규칙으로 가리고, 답변에는 모델·규칙과 이미 탐지한 개인정보의 재등장 검사를 적용합니다.

## 내부 성능

제목과 질문의 개인정보 유형 및 시작·끝 위치가 정확히 일치해야 정답으로 계산합니다. 아래는 **이전에 결과를 확인했던 내부 테스트 1,706건의 회귀 비교**이며, 새로운 외부 블라인드 평가가 아닙니다. 답변 전체에는 정답이 없어 답변 전체 정확도는 측정하지 않았습니다.

| 항목 | 정밀도 | 재현율 | F1 |
|---|---:|---:|---:|
| 전체 5종 | 96.8% | 95.3% | 96.0% |
| 이름 | 94.9% | 92.5% | 93.7% |
| 주소 | 97.4% | 97.1% | 97.3% |
| 이메일 | 96.2% | 97.6% | 96.9% |
| 휴대폰번호 | 96.3% | 93.0% | 94.6% |
| 승차권번호 | 99.1% | 97.1% | 98.1% |

학습 7,963건·검증 1,706건의 기존 문장 그룹 분할을 유지했습니다. 라벨 잡음 또는 학습 불가 표시 1,125건은 제외했습니다. 이름 전용 모델은 검증셋 이름 F1으로 선택했으며, 네 가지 다른 유형의 탐지 구간은 유지했습니다. 세부 수치와 평가 범위는 `performance.json`에 있습니다. 실제 업무 성능은 별도 데이터로 검증해야 합니다.

## 배포 구성

- 코드·토크나이저·설정·성능 수치: 이 폴더
- 학습 가중치: GitHub Release의 `pii-five-type-model.safetensors`, `pii-name-expert-model.safetensors`
- 원본 모델 출처: [MODEL_SOURCES.md](MODEL_SOURCES.md)

기존 VOC 분석 프로그램과 독립된 마스킹 실행 도구입니다. 기존 웹 화면이나 API에 자동으로 연결하지 않습니다.
