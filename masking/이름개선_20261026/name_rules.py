"""Name boundaries and explicit name contexts; never consumes gold annotations."""
import re
from engine import Span
NAME=r'[가-힣](?:[ \t·.]*[가-힣]){1,4}?'
END=r'(?=입\s*니다|입니다|이라고|라고|으로\s*기억|로\s*기억|러\s*기억|\s*(?:씨|님|명의|씀|올림|드림|과장님|직원)\b|[,，;\n)]|\s*$)'
PATTERNS=[
 re.compile(r'(?:이름|성명)(?:은|는)?\s*[:：=]?\s*(?P<value>'+NAME+')'+END),
 re.compile(r'(?:신청인|민원인|작성자|예금주|보호자)\s*[:：=]?\s*(?P<value>'+NAME+')'+END),
 re.compile(r'(?:함께\s*이용한\s*사람|예약\s*또는\s*동행한\s*사람)(?:은|는)\s*(?P<value>'+NAME+')'+END),
]
BAD_VALUES={'이름','성명','신청인','민원인','작성자','예금주','보호자','직원','이용자','이용자의','이룡자들이','안내한','안네한','이보이','감사','감사합','남편','남ㅍ연'}
def compact(v):return re.sub(r'[\s·.]','',v)
def refine(text,model_names,threshold=.8,context=True):
    out=[]
    for s in model_names:
        if s.type!='name' or s.score<threshold:continue
        a,b=s.start,s.end
        # WordPiece may attach the first syllable of the copula to the name.
        if text[a:b].endswith('입') and re.match(r'\s*니다',text[b:]):b-=1
        if b<=a:continue
        value=text[a:b];c=compact(value)
        if len(c)<2 or c in BAD_VALUES:continue
        if value.endswith('의') and text[b:b+1]=='견':continue
        left=text[max(0,a-16):a];right=text[b:b+24]
        explicit=bool(re.search(r'(?:이름|성명|신청인|민원인|작성자|예금주)\s*[:：=은는]*\s*$',left))
        if not explicit and re.match(r'(?:\([^)]*\))?\s*(?:역|가는|행\b|출발|도착)',right):continue
        out.append(Span(a,b,'name',s.score,s.source+'+name_boundary'))
    if context:
        for pattern in PATTERNS:
            for m in pattern.finditer(text):
                a,b=m.span('value');v=compact(text[a:b])
                if 2<=len(v)<=5 and v not in BAD_VALUES:out.append(Span(a,b,'name',1.,'name_context'))
    return out
