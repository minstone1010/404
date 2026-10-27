---
license: mit
task_categories:
- token-classification
- named-entity-recognition
tags:
- korean
- pii
- privacy
- masking
- bert
language:
- ko
pipeline_tag: token-classification
---

# Korean PII Masking BERT

한국어 개인정보(PII, Personally Identifiable Information) 마스킹을 위한 BERT 기반 토큰 분류 모델입니다.

## 모델 설명

이 모델은 한국어 텍스트에서 개인정보를 자동으로 감지하고 마스킹하는 용도로 사용됩니다. BERT 기반 아키텍처를 사용하여 14가지 유형의 한국어 PII를 식별합니다.

## 모델 세부 정보

- **아키텍처**: BertForTokenClassification
- **기본 모델**: BERT (Korean)
- **Hidden Size**: 1024
- **Num Hidden Layers**: 24
- **Num Attention Heads**: 16
- **Max Position Embeddings**: 300
- **Vocab Size**: 30,000

## 지원하는 PII 유형

모델은 다음 14가지 PII 유형을 인식합니다:

1. **가맹점명** (Business Name)
2. **결제금액** (Payment Amount)
3. **계좌번호** (Account Number)
4. **로그인ID** (Login ID)
5. **상세주소** (Detailed Address)
6. **신용점수** (Credit Score)
7. **여권번호** (Passport Number)
8. **우편번호** (Postal Code)
9. **운전면허번호** (Driver's License Number)
10. **이름** (Name)
11. **전자메일** (Email)
12. **전화번호** (Phone Number)
13. **주민등록번호** (Resident Registration Number)
14. **카드번호** (Card Number)
15. **휴대전화번호** (Mobile Phone Number)

각 PII는 BIO 태깅 방식을 사용합니다 (B-, I-, O).

## 사용법

### 기본 사용법

```python
from transformers import BertForTokenClassification, BertTokenizer
import torch

# 모델 및 토크나이저 로드
model = BertForTokenClassification.from_pretrained("your-username/korean-pii-masking-bert")
tokenizer = BertTokenizer.from_pretrained("your-username/korean-pii-masking-bert")

# 텍스트 토크나이징
text = "안녕하세요, 제 이름은 김민수이고 전화번호는 010-1234-5678입니다."
inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

# 예측
with torch.no_grad():
    outputs = model(**inputs)
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
    predicted_labels = torch.argmax(predictions, dim=-1)[0]
```

### 파이프라인을 통한 사용

원본 저장소의 `inference_pipeline.py`를 사용하면 더 간편하게 사용할 수 있습니다:

```python
from inference_pipeline import PIIInferencePipeline

# 파이프라인 초기화
pipeline = PIIInferencePipeline()

# 텍스트 예측
text = "안녕하세요, 제 이름은 김민수이고 전화번호는 010-1234-5678입니다."
result = pipeline.predict(text)

print(f"원본 텍스트: {result.original_text}")
print(f"마스킹 텍스트: {result.masked_text}")
print(f"발견된 PII: {len(result.entities)}개")
```

## 예시

```
입력: "8월 10일 14:32에 백다방 코엑스점에서 9,910원 승인 내역 확인됩니다."

출력:
- 발견된 PII:
  - 백다방 코엑스점 -> [가맹점명]
  - 9,910원 -> [결제금액]
```

## 데이터 전처리

모델은 한국어 텍스트를 입력으로 받으며, 최대 길이는 300 토큰입니다.

## 제한 사항

- 최대 입력 길이: 300 토큰
- 한국어 텍스트에 최적화됨
- 텍스트에서의 PII 인식에 특화 (이미지나 음성 미지원)

## 참고 문헌

이 모델은 한국어 개인정보 마스킹을 위해 학습되었습니다.

## 라이센스

MIT License


