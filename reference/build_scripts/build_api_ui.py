from pathlib import Path
files={}
files['backend/main.py']='''from contextlib import asynccontextmanager
import threading,logging
from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from backend.config import settings,ROOT
from backend.service import Service
from backend import notebook_logic as logic
logging.basicConfig(level=logging.INFO)
@asynccontextmanager
async def lifespan(app):
 app.state.service=Service()
 if settings.startup_models:
  worker=threading.Thread(target=app.state.service.start,name='history-preparation',daemon=True); worker.start()
 yield
app=FastAPI(title='VOC Desk API',lifespan=lifespan)
def svc(): return app.state.service
def safe(call):
 try: return call()
 except KeyError as e: raise HTTPException(404,'VOC를 찾을 수 없습니다') from e
 except ValueError as e: raise HTTPException(422,str(e)) from e
 except RuntimeError as e: raise HTTPException(503,str(e)) from e
class Decision(BaseModel):
 department: str=''
 status: str
 memo: str=Field(default='',max_length=500)
@app.get('/api/vocs')
def vocs():
 ids=logic.df.loc[logic.df.데이터역할.eq('검토대상' if settings.split_mode=='holdout' else '검색이력'),'번호']
 return [svc().detail(id) for id in ids]
@app.get('/api/vocs/{id}')
def detail(id:str): return safe(lambda:svc().detail(id))
@app.post('/api/vocs/{id}/analyze')
def analyze(id:str,force:bool=False): return safe(lambda:svc().recommend(id,force=force))
@app.get('/api/vocs/{id}/recommendations')
def recommendations(id:str): return safe(lambda:svc().detail(id)['result'])
@app.post('/api/vocs/{id}/decision')
def decision(id:str,body:Decision):
 safe(lambda:svc().save_decision(id,body.department,body.status,body.memo)); return svc().detail(id)
@app.get('/api/departments')
def departments(): return svc().teams
@app.get('/api/stats')
def stats():
 return dict(total=len(logic.df),history_total=svc().history_total,history_analyzed=svc().history_progress,history_searchable=len(logic.history_df),history_complete=svc().history_complete,model_ready=svc().ready,initialization_error=svc().error,model=settings.qwen_model,decisions=len(svc().store.load_approvals()))
@app.get('/api/export')
def export(): return FileResponse(svc().store.export_results(),filename='voc_results.xlsx')
app.mount('/',StaticFiles(directory=ROOT/'voc-ui'/'dist',html=True),name='ui')
'''
files['backend/cli.py']='''import argparse,json,time
from backend.service import Service
from backend import notebook_logic as logic
from backend.config import settings

def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=['prepare-history','evaluate','export']); p.add_argument('--limit',type=int); p.add_argument('--allow-partial',action='store_true'); args=p.parse_args()
 s=Service()
 if args.command=='prepare-history':
  s.prepare_history(args.limit); print(json.dumps(dict(analyzed=s.history_progress,searchable=len(logic.history_df)),ensure_ascii=False)); return
 if args.command=='export': print(s.store.export_results()); return
 missing=[r['번호'] for _,r in logic.df.loc[logic.df.데이터역할.eq('검색이력')].iterrows() if not (s.store.analysis(r['번호'],s.signature) or {}).get('analysis',{}).get('분석상태')=='분석완료']
 if missing and not args.allow_partial: raise RuntimeError(f'과거 이력 {len(missing)}건 미완료. prepare-history를 먼저 실행하세요. 시험 평가는 --allow-partial로 명시하세요.')
 s.history_complete=not missing; s.qwen.load()
 rows=logic.df.loc[logic.df.데이터역할.eq('검토대상')]
 if args.limit: rows=rows.head(args.limit)
 truth=logic.evaluation_truth_df.set_index('번호'); results=[]
 for _,row in rows.iterrows():
  for mode in ['A','B','C']:
   output=s.recommend(row['번호'],mode); results.append(dict(id=row['번호'],mode=mode,output=output))
   print(row['번호'],mode,output.get('recommendation',{}).get('status'),flush=True)
 from sklearn.metrics import accuracy_score,f1_score
 import torch,numpy as np
 report={'history_complete':not missing,'history_count':len(logic.history_df),'model':settings.qwen_model,'ground_truth_limitations':'지역/function/scope 정답 컬럼 없음. 부서 Master 속성에서 얻은 proxy만 제공하며 독립 정답 정확도가 아님','modes':{}}
 for mode in ['A','B','C']:
  items=[x for x in results if x['mode']==mode]; gold=[]; pred=[]; top1=[]; top3=[]; coverage=[]; regions=[]; functions=[]; scopes=[]; analysis_times=[]; total_times=[]
  for x in items:
   o=x['output']; a=o['analysis']; t=truth.loc[x['id']]; ranking=o.get('ranking',[]); names=[r['department'] for r in ranking]
   gold.append(t['topic_code']); pred.append(a.get('주요지코드','분석실패')); top1.append(bool(names and names[0]==t['handling_team'])); top3.append(t['handling_team'] in names); coverage.append(o.get('recommendation',{}).get('status')=='추천가능'); analysis_times.append(o['analysis_seconds']); total_times.append(o.get('total_seconds',o['analysis_seconds']))
   dept=logic.department_master.loc[logic.department_master.department.eq(t['handling_team'])]
   if len(dept)==1:
    d=dept.iloc[0]
    if d.scope=='지역': regions.append(a.get('관할지역코드')==d.region_code)
    functions.append(d.business_function in a.get('업무기능후보',[])); scopes.append(a.get('routing_scope')==('지역형' if d.scope=='지역' else '전국형'))
  avg=lambda xs:float(np.mean(xs)) if xs else None
  report['modes'][mode]=dict(count=len(items),topic_accuracy=accuracy_score(gold,pred),topic_macro_f1=f1_score(gold,pred,average='macro',zero_division=0),region_proxy_accuracy=avg(regions),function_proxy_accuracy=avg(functions),scope_proxy_accuracy=avg(scopes),department_top1_accuracy=avg(top1),department_top3_accuracy=avg(top3),coverage=avg(coverage),defer_rate=1-avg(coverage),mean_analysis_seconds=avg(analysis_times),mean_total_seconds=avg(total_times))
 report['gpu_peak_allocated_mb']=torch.cuda.max_memory_allocated()/1024**2 if torch.cuda.is_available() else 0
 (settings.output/'evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)); (settings.output/'evaluation_records.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
'''
files['.env.example']='''QWEN_MODEL=Qwen/Qwen3.5-2B
QWEN_DEVICE=cuda
QWEN_QUANTIZATION=4bit
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DEVICE=cpu
VOC_PATH=data/voc_dummy_2500_v3_해설판.xlsx
ROUTING_MASTER_PATH=data/korail_voc_routing_master.xlsx
OUTPUT_PATH=outputs
TOP_K=10
TOP_N=3
MIN_SIMILARITY=0.55
MIN_SUPPORT=2
MIN_SCORE_MARGIN=0.03
SPLIT_MODE=holdout
HISTORY_FRACTION=0.8
STARTUP_MODELS=true
HOST=127.0.0.1
PORT=8000
'''
for n,c in files.items(): Path(n).write_text(c,encoding='utf-8')
# Preserve original renderer; replace data/persistence and add analysis action.
p=Path('voc-ui/dist/app.js'); js=p.read_text(); Path('reference/original_app.js').write_text(js)
start=js.index('const esc='); js=js[start:js.index('// Optional structured access')]
js=js[:js.index('function saveDecision')]+'''async function api(path,options={}){const response=await fetch(path,{headers:{'Content-Type':'application/json'},...options});if(!response.ok){let body=await response.text();throw new Error(body);}return response.json();}
async function reload(){const rows=await api('/api/vocs');samples=rows;decisions={};for(const v of samples){if(v.decision)decisions[v.id]={status:v.decision.status==='승인완료'?'approved':'held',department:v.decision.department,memo:v.decision.memo};}if(!samples.some(v=>v.id===selectedId))selectedId=samples[0]?.id;renderMetrics();renderList();renderDetail();const stats=await api('/api/stats');document.querySelector('.demo-badge').textContent=stats.initialization_error?'초기화 실패':`과거 이력 ${stats.history_searchable}/${stats.history_total}건${stats.history_complete?' · 준비 완료':' · 준비 중'}`;if(stats.initialization_error)notify(stats.initialization_error);}
async function saveDecision(status){const id=selectedId,department=document.getElementById('department').value,memo=document.getElementById('memo').value.trim();if(status==='approved'&&!departments.includes(department)){notify('최종 부서를 선택하세요.');return;}document.getElementById('approve').disabled=true;document.getElementById('hold').disabled=true;try{await api(`/api/vocs/${encodeURIComponent(id)}/decision`,{method:'POST',body:JSON.stringify({status:status==='approved'?'승인완료':'보류',department,memo})});await reload();notify('결과를 Backend에 저장했습니다.');}catch(e){notify('저장실패: '+e.message);document.getElementById('approve').disabled=false;document.getElementById('hold').disabled=false;}}
async function analyzeSelected(){const id=selectedId;document.getElementById('analyze').disabled=true;notify('AI 분석 중입니다.');try{const result=await api(`/api/vocs/${encodeURIComponent(id)}/analyze`,{method:'POST'});await reload();notify(result.error?'분석실패: '+result.error:'분석과 추천을 완료했습니다.');}catch(e){notify('분석실패: '+e.message);document.getElementById('analyze').disabled=false;}}
document.getElementById('search').addEventListener('input',e=>{search=e.target.value;renderList();});document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;document.querySelectorAll('.filter').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});renderList();}));document.getElementById('reset').addEventListener('click',()=>reload().catch(e=>notify(e.message)));
(async()=>{try{departments=await api('/api/departments');await reload();}catch(e){document.getElementById('detail-area').textContent='Backend 연결 실패: '+e.message;}})();
'''
js=js.replace("const statusOf=id=>decisions[id]?.status||'pending';","const statusOf=id=>decisions[id]?.status||({'분석대기':'waiting','분석완료':'analyzed','분석오류':'failed'}[samples.find(v=>v.id===id)?.status]||'pending');")
js=js.replace("const statusNames={pending:'확인 대기',approved:'승인 완료',held:'보류'};","const statusNames={pending:'확인대기',approved:'승인완료',held:'보류',waiting:'분석대기',analyzed:'분석완료',failed:'분석오류'};")
js=js.replace("const departments=[...new Set(samples.flatMap(v=>v.recs.map(r=>r.name)))].sort((a,b)=>a.localeCompare(b,'ko'));",'')
js=js.replace("'샘플 민원'","'평가 VOC'").replace("statusOf(v.id)==='pending'","['pending','waiting','analyzed','failed'].includes(statusOf(v.id))")
js=js.replace("filter==='all'||statusOf(v.id)===filter","filter==='all'||statusOf(v.id)===filter||(filter==='pending'&&['waiting','analyzed','failed'].includes(statusOf(v.id)))")
js=js.replace('data-id="${v.id}"','data-id="${esc(v.id)}"').replace('${v.scope}','${esc(v.scope)}').replace('${v.date}','${esc(v.date)}').replace('${v.id} ·','${esc(v.id)} ·')
js=js.replace("const v=samples.find(x=>x.id===selectedId),saved=decisions[v.id];","const v=samples.find(x=>x.id===selectedId);if(!v){document.getElementById('detail-area').textContent='검토 대상이 없습니다.';return;}const saved=decisions[v.id];")
js=js.replace('<h2>${esc(v.title)}</h2>','<h2>${esc(v.title)}</h2><button class="button primary" id="analyze">AI 분석 · 추천 실행</button>')
js=js.replace("document.getElementById('approve').addEventListener", "document.getElementById('analyze').addEventListener('click',analyzeSelected);document.getElementById('approve').disabled=!v.result.recommendation;document.getElementById('hold').disabled=!v.result.recommendation;document.getElementById('approve').addEventListener")
js=js.replace('위치가 확인되지 않아 추천 후보가 없습니다.','추천 후보가 없습니다. 분석 상태와 검색 근거를 확인하세요.')
js='let samples=[],decisions={},departments=[],selectedId=null,filter="all",search="",selectedDepartment="",toastTimer;\n'+js
p.write_text(js)
p=Path('voc-ui/dist/index.html'); html=p.read_text(); Path('reference/original_index.html').write_text(html)
for a,b in [('PROTOTYPE','LOCAL AI'),('샘플 데이터로 화면 흐름을 확인합니다.','원본 Excel 기반 분석 결과를 검토합니다.'),('Qwen · Excel · 업무 시스템 연동 전','Qwen · Routing Master · 과거 VOC 검색'),('UI 초안 · 샘플 6건','Backend 연결 중'),('샘플 초기화','상태 새로고침'),('샘플 검토 현황','VOC 검토 현황'),('화면에 표시되는 민원은 UI용 예시입니다.','holdout 분리된 검토 대상 VOC입니다.'),('VOC Desk · UI prototype','VOC Desk · Local AI'),('승인·보류 내용은 이 브라우저에만 저장됩니다.','승인·보류 결과는 Backend SQLite에 저장됩니다.')]: html=html.replace(a,b)
html=html.replace('id="nav-count">6','id="nav-count">0'); p.write_text(html)
