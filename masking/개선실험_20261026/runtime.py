"""Candidate runtime: five-type adapted BERT + validated railway rules; optional local LLM."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import engine
from improved_rules import improved_rules
from variants import Performance
class FloatLogits:
    def __init__(self,model):self.model=model;self.config=model.config
    def __call__(self,**inputs):
        from types import SimpleNamespace
        return SimpleNamespace(logits=self.model(**inputs).logits.float())
class Candidate(engine.Masker):
    def __init__(self):
        super().__init__(HERE/'candidate_ner',device='cuda')
        self.model.to(dtype=self.torch.bfloat16 if self.torch.cuda.is_bf16_supported() else self.torch.float16)
        self.model=FloatLogits(self.model)
        self.settings=json.loads((HERE/'선택설정.json').read_text(encoding='utf-8'))
        self.allowed_types=set(engine.PRIORITY)
        if self.settings['rules']=='ticket_variants':engine.rules=improved_rules
    def model_spans(self,text):
        return [s for s in super().model_spans(text) if s.type in self.allowed_types and s.score>=self.settings['thresholds'][s.type]]
    def hybrid_spans(self,text):
        model=[s for s in self.model_spans(text) if s.type in self.allowed_types and s.score>=self.settings['thresholds'][s.type]]
        fn=improved_rules if self.settings['rules']=='ticket_variants' else engine.rules
        return model+[s for s in fn(text) if s.type in self.allowed_types]
class CandidateLLM(Performance):
    def __init__(self):
        super().__init__(HERE/'candidate_ner',ROOT/'models/llm',device='cuda',llm_batch=8,support_min=.01,model_min_score=0.,mask_types=engine.PRIORITY,ner_dtype='bfloat16')
        self.settings=json.loads((HERE/'선택설정.json').read_text(encoding='utf-8'))
        self.model=FloatLogits(self.model)
    def model_spans(self,text):
        return [s for s in super().model_spans(text) if s.type in self.allowed_types and s.score>=self.settings['thresholds'][s.type]]
def main():
    import app
    use_llm='--with-llm' in sys.argv
    if use_llm:
        sys.argv.remove('--with-llm');engine.rules=improved_rules
    app.ROOT=HERE
    app.load_engine=CandidateLLM if use_llm else Candidate
    app.main()
if __name__=='__main__':main()
