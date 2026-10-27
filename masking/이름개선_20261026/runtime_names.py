"""Offline name specialist over the existing four-type detector."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BASE=ROOT/'개선실험_20261026'
sys.path[:0]=[str(ROOT),str(BASE)]
from runtime import Candidate,FloatLogits
from engine import Masker,Span,resolve,mask_text
from name_rules import refine
class NameImproved(Masker):
    def __init__(self):
        self.base=Candidate();self.settings=json.loads((HERE/'이름선택설정.json').read_text(encoding='utf-8'))
        self.expert=None
        if self.settings['weights']=='name_expert':
            self.expert=Masker(HERE/'name_expert',device='cuda');self.expert.model.to(dtype=self.expert.torch.bfloat16 if self.expert.torch.cuda.is_bf16_supported() else self.expert.torch.float16);self.expert.model=FloatLogits(self.expert.model)
        self.allowed_types=self.base.allowed_types;self.model=self.base.model
    def hybrid_spans(self,text):
        previous=self.base.detect(text);other=[s for s in previous if s.type!='name']
        names=self.expert.model_spans(text) if self.expert else Masker.model_spans(self.base,text)
        candidates=refine(text,names,self.settings['threshold'])
        return other+[s for s in candidates if not any(s.start<t.end and s.end>t.start for t in other)]
    def answer_spans(self,text):return self.hybrid_spans(text)
def main():
    import app
    app.ROOT=HERE;app.load_engine=NameImproved;app.main()
if __name__=='__main__':main()
