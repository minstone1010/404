"""Schema-aware handling of structured VOC answer and employee columns.

Free-form complaint text uses the full Performance detector. Answers use BERT,
regular expressions, and known-name occurrences from the input employee field.
No gold annotations are used by these functions.
"""
import re
from engine import Masker,Span,resolve,mask_text

def as_dict(spans):return [s.__dict__ for s in spans]
def answer_and_staff(engine,answer,staff_name,complaint_text,complaint_spans):
    staff=[Span(0,len(staff_name),'name',1.,'staff_column')] if staff_name else []
    answer_detector=getattr(engine,'answer_spans',None)
    spans=list(answer_detector(answer) if answer_detector else Masker.hybrid_spans(engine,answer))
    if staff_name:
        spans.extend(Span(m.start(),m.end(),'name',1.,'staff_column_occurrence') for m in re.finditer(re.escape(staff_name),answer))
    # A response can quote the complaint title; reuse only values already detected.
    for s in complaint_spans:
        value=complaint_text[s['start']:s['end']]
        if value:
            spans.extend(Span(m.start(),m.end(),s['type'],s['score'],'complaint_value_occurrence') for m in re.finditer(re.escape(value),answer))
    spans=resolve(spans,len(answer))
    return ({'masked_text':mask_text(answer,spans),'spans':as_dict(spans)},
            {'masked_text':mask_text(staff_name,staff),'spans':as_dict(staff)})

def combined_answer(engine,fields,complaint_result):
    complaint=fields['제목']+'\n'+fields['질문']
    answer,staff=answer_and_staff(engine,fields['답변'],fields['처리자'],complaint,complaint_result['spans'])
    text=complaint+'\n\n[답변]\n'+fields['답변']+'\n\n[처리자]\n'+fields['처리자']
    answer_start=len(complaint)+len('\n\n[답변]\n');staff_start=answer_start+len(fields['답변'])+len('\n\n[처리자]\n')
    spans=[Span(**s) for s in complaint_result['spans']]
    for offset,part in [(answer_start,answer),(staff_start,staff)]:
        spans.extend(Span(s['start']+offset,s['end']+offset,s['type'],s['score'],s['source']) for s in part['spans'])
    return {'masked_text':mask_text(text,spans),'spans':as_dict(resolve(spans,len(text)))}
