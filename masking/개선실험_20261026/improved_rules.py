"""Rail ticket variants derived from training examples only; offsets stay original."""
import re
from engine import rules,Span
CANONICAL=re.compile(r'(?<!\d)\d{5}\s*[-－–—./]\s*\d{4}\s*[-－–—./]\s*\d{5}\s*[-－–—./]\s*\d{2}(?!\d)')
NUMBER=re.compile(r'(?<!\d)\d(?:[\d \t\r\n./－–—-]*\d)?(?!\d)')
CUE=re.compile(r'(?:승차권|티켓|발권|예약|예매)\s*(?:번호|No\.?|넘버)?\s*[:：=#]?\s*$',re.I)
def improved_rules(text):
    base=rules(text)
    # Replace old unconstrained ticket context spans, which can eat neighboring numbers.
    base=[s for s in base if not(s.type=='ticket_no' and s.source=='context')]
    extra=[Span(m.start(),m.end(),'ticket_no',1.,'ticket_format') for m in CANONICAL.finditer(text)]
    for m in NUMBER.finditer(text):
        value=m.group();digits=sum(c.isdigit() for c in value)
        if digits==16 and len(value)<=35 and CUE.search(text[max(0,m.start()-25):m.start()]):
            extra.append(Span(m.start(),m.end(),'ticket_no',1.,'ticket_context'))
    return base+extra
