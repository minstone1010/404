from pathlib import Path
import ast
root=Path.cwd(); (root/'backend').mkdir(exist_ok=True); (root/'outputs').mkdir(exist_ok=True)
def cell(i): return (root/'reference'/f'cell_{i}.py.txt').read_text()
def defs(i,names=None):
 s=cell(i); return '\n\n'.join(ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and (names is None or n.name in names))
def statements(i,skip=()):
 s=cell(i); return '\n\n'.join(ast.get_source_segment(s,n) for n in ast.parse(s).body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id in ['print','display']) and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in skip for t in n.targets)) and not isinstance(n,ast.If) or False)
# Keep cell 5's initialization including validation/duplicate union-find.
s=cell(5); nodes=ast.parse(s).body
s='\n\n'.join(ast.get_source_segment(s,n) for n in nodes if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id in ['print','display']))
r=cell(7); r=r[r.index('location_master ='):r.index("print('라우팅 기준표:")]
preamble='''"""Refactored from supplied Notebook; see reference/cell_*.py.txt for provenance."""
from pathlib import Path
import json, hashlib, os, re, unicodedata
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from backend.config import settings
SOURCE_PATH=settings.voc_path
ROUTING_MASTER_PATH=settings.master_path
MODEL_NAME=settings.qwen_model
EMBED_MODEL_NAME=settings.embedding_model
SPLIT_MODE=settings.split_mode
HISTORY_FRACTION=settings.history_fraction
SPLIT_SEED='voc-split-v1'
TOP_K=settings.top_k
TOP_N=settings.top_n
MIN_SIMILARITY=settings.min_similarity
MIN_SUPPORT=settings.min_support
MIN_SCORE_MARGIN=settings.min_score_margin
'''
code=preamble+s+'\n\n'+r+'\n\n'+defs(11,{'parse_json_object','optional_code','parse_topic','parse_cause','analyze_topic','analyze_cause'})+'\n\n'+defs(14,{'parse_routing','analyze_routing'})+'\n\n'+defs(16)+'\n\n'+"RANK_COLUMNS = ['department','count','frequency','mean_similarity','max_similarity','score']\n"+defs(17,{'empty_ranking','retrieve_similar_vocs','rank_departments','recommend_department','record_recommendation'})
(root/'backend'/'notebook_logic.py').write_text(code+'\n',encoding='utf-8'); (root/'backend'/'__init__.py').write_text('')
