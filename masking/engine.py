"""Offline Korean PII detection. Character offsets always refer to original input."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
import re
from dataclasses import dataclass, asdict
from pathlib import Path

PRIORITY = ['name', 'address', 'email', 'phone', 'ticket_no']
TYPES = PRIORITY + ['rrn', 'account_no', 'card_no', 'seat_no', 'birth', 'member_no', 'user_id', 'password', 'passport_no', 'foreign_reg_no', 'driver_lic_no', 'car_no', 'disability_no']
KOREAN = dict(zip(TYPES, ['이름','주소','이메일','휴대폰번호','승차권번호','주민등록번호','계좌번호','카드번호','좌석번호','생년월일','회원번호','아이디','비밀번호','여권번호','외국인등록번호','운전면허번호','차량번호','장애인등록증번호']))
PATTERNS = {
 'email': r'(?<![\w.%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+',
 'phone': r'(?<!\d)(?:\+82[ .\-]?10|01[016789])[ .\-]?\d{3,4}[ .\-]?\d{4}(?!\d)',
 'ticket_no': r'(?<!\d)\d{5}[ \-]\d{4}[ \-]\d{5}[ \-]\d{2}(?!\d)',
 'rrn': r'(?<!\d)\d{6}\s*-\s*[1-8]\d{6}(?!\d)',
 'card_no': r'(?<!\d)\d{4}(?:[ \-]\d{4}){3}(?!\d)',
 'seat_no': r'\d{1,2}\s*호차\s*\d{1,2}\s*[A-D]\s*석',
}
CONTEXT = {
 'name': r'(?:성명|이름|신청인|민원인)\s*[:：=]\s*(?P<value>[가-힣]{2,4})(?![가-힣])',
 'address': r'(?:주소|거주지|배송지)\s*[:：=]\s*(?P<value>[^\n,;]+?)(?=\s+(?:이메일|연락처|전화|이름|성명|승차권)\s*[:：=]|[\n,;]|$)',
 'ticket_no': r'(?:승차권\s*번호|티켓\s*번호)\s*[:：=]?\s*(?P<value>\d(?:[\d \-]{6,24}\d))(?!\d)',
 'account_no': r'(?:계좌\s*번호)\s*[:：=]?\s*(?P<value>\d{2,6}(?:-\d{2,6}){1,3})(?!\d)',
}

@dataclass(frozen=True)
class Span:
    start: int
    end: int
    type: str
    score: float = 1.0
    source: str = 'rule'

def rules(text):
    found = [Span(m.start(), m.end(), kind) for kind, p in PATTERNS.items() for m in re.finditer(p, text)]
    for kind, pattern in CONTEXT.items():
        for m in re.finditer(pattern, text):
            a,b = m.span('value')
            while b>a and text[b-1].isspace(): b-=1
            if b>a: found.append(Span(a,b,kind,1.0,'context'))
    return found

def combine_detections(model_spans, rule_spans):
    """Disambiguate identical 13-digit spans without reducing masked coverage."""
    foreign_model={(s.start,s.end) for s in model_spans if s.type=='foreign_reg_no'}
    return list(model_spans)+[
        s for s in rule_spans
        if not (s.type=='rrn' and (s.start,s.end) in foreign_model)
    ]

def resolve(spans, text_length):
    """Keep the UNION of overlapping PII: priority chooses the label, never drops coverage."""
    ordered = sorted(set(s for s in spans if s.type in TYPES and 0<=s.start<s.end<=text_length), key=lambda s:(s.start,s.end))
    groups=[]
    for s in ordered:
        if groups and s.start < max(x.end for x in groups[-1]): groups[-1].append(s)
        else: groups.append([s])
    result=[]
    for group in groups:
        best=min(group,key=lambda s:(TYPES.index(s.type),-s.score,-(s.end-s.start)))
        result.append(Span(min(s.start for s in group),max(s.end for s in group),best.type,max(s.score for s in group),'+'.join(sorted({s.source for s in group}))))
    return result

def mask_text(text, spans):
    for s in reversed(resolve(spans,len(text))):
        text=text[:s.start]+'['+KOREAN[s.type]+']'+text[s.end:]
    return text

class Masker:
    def __init__(self, model_dir=None, *, rules_only=False, device='cpu', batch_size=8):
        self.model=None
        self.batch_size=batch_size
        if rules_only: return
        if not model_dir or not Path(model_dir).is_dir():
            raise FileNotFoundError('학습 모델 폴더가 필요합니다. README의 학습/반입 절차를 확인하세요. 규칙만 사용하려면 --rules-only를 명시하세요.')
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        self.torch=torch
        self.device=torch.device(device)
        self.tokenizer=AutoTokenizer.from_pretrained(str(model_dir),local_files_only=True,trust_remote_code=False,use_fast=True)
        if not self.tokenizer.is_fast: raise ValueError('문자 위치를 보존하는 Fast tokenizer가 필요합니다.')
        self.model=AutoModelForTokenClassification.from_pretrained(str(model_dir),local_files_only=True,trust_remote_code=False,use_safetensors=True).to(self.device).eval()
        labels=list(self.model.config.id2label.values())
        if not all(x=='O' or x[:2] in ('B-','I-') and x[2:] in TYPES for x in labels):
            raise ValueError('지원하지 않는 라벨입니다. v3 학습 모델을 사용하세요.')
        self.max_length=min(384,self.model.config.max_position_embeddings,self.tokenizer.model_max_length)

    def model_spans(self,text):
        if self.model is None or not text: return []
        torch=self.torch
        encoded=self.tokenizer(text,truncation=True,max_length=self.max_length,stride=min(96,self.max_length//3),return_overflowing_tokens=True,return_offsets_mapping=True)
        # Fuse duplicate token logits across windows BEFORE BIO decoding.
        votes={}
        for start in range(0,len(encoded['input_ids']),self.batch_size):
            features=[{k:encoded[k][i] for k in self.tokenizer.model_input_names if k in encoded} for i in range(start,min(start+self.batch_size,len(encoded['input_ids'])))]
            inputs=self.tokenizer.pad(features,padding=True,return_tensors='pt').to(self.device)
            with torch.inference_mode(): probs=self.model(**inputs).logits.softmax(-1).cpu()
            for j,i in enumerate(range(start,min(start+self.batch_size,len(encoded['input_ids'])))):
                offsets=encoded['offset_mapping'][i]
                for k,(a,b) in enumerate(offsets):
                    if a==b: continue
                    weight=min(k+1,len(offsets)-k,32)
                    old,total=votes.get((a,b),(torch.zeros(probs.shape[-1]),0))
                    votes[a,b]=(old+probs[j,k]*weight,total+weight)
        found=[]; current=None
        for (a,b),(prob,total) in sorted(votes.items()):
            prob=prob/total; idx=int(prob.argmax()); label=self.model.config.id2label[idx]; score=float(prob[idx])
            if label=='O':
                if current: found.append(current); current=None
                continue
            kind=label[2:]
            if label.startswith('I-') and current and current.type==kind and a>=current.end and (not text[current.end:a] or text[current.end:a].isspace()):
                current=Span(current.start,b,kind,min(current.score,score),'model')
            else:
                if current: found.append(current)
                current=Span(a,b,kind,score,'model')
        if current: found.append(current)
        self.last_token_probs={offset:prob/total for offset,(prob,total) in votes.items()}
        return found

    def hybrid_spans(self,text):
        minimum=getattr(self,'model_min_score',0.)
        combined=combine_detections([s for s in self.model_spans(text) if s.score>=minimum],rules(text))
        allowed=getattr(self,'allowed_types',None)
        # Filter BEFORE overlap union so an excluded entity cannot enlarge a mask.
        return combined if allowed is None else [s for s in combined if s.type in allowed]

    def detect(self,text):
        return resolve(self.hybrid_spans(text),len(text))

    def result(self,text):
        spans=self.detect(text)
        return {'masked_text':mask_text(text,spans),'spans':[asdict(s) for s in spans], 'mode':'hybrid' if self.model is not None else 'rules_only'}
