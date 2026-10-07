from pathlib import Path
files={}
files['backend/validation.py']='''import json
from backend import notebook_logic as logic

def validate(raw,stage):
 value=logic.parse_json_object(raw)
 required={'topic':['main_topic_code','sub_topic_code','keywords'],'cause':['human_factor','material_factor','other_factor','reason'],'routing':['location_candidate','routing_scope','reason']}[stage]
 for key in required:
  if key not in value: raise ValueError('필드 누락: '+key)
  item=value[key]
  nullable=key in {'sub_topic_code','location_candidate'}
  if item is None and not nullable: raise ValueError('null 금지: '+key)
  if isinstance(item,str) and (not item.strip() or item.strip().lower() in {'null','none','nan'}): raise ValueError('빈 문자열/문자열 null 금지: '+key)
  if key in {'main_topic_code','sub_topic_code','location_candidate','routing_scope','reason'} and item is not None and not isinstance(item,str): raise ValueError('문자열 타입 오류: '+key)
 parser={'topic':logic.parse_topic,'cause':logic.parse_cause,'routing':logic.parse_routing}[stage]
 return parser(raw)
'''
files['backend/service.py']='''import hashlib,json,time,threading,logging
from pathlib import Path
import numpy as np
import pandas as pd
from backend.config import settings
from backend import notebook_logic as logic
from backend.models import Qwen,Embedding
from backend.decision import Store
from backend.routing import restrict_routing_candidates
from backend.validation import validate
log=logging.getLogger(__name__)
class Service:
 def __init__(self):
  self.store=Store(); self.qwen=Qwen(); self.embedding=Embedding(); self.lock=threading.RLock()
  self.ready=False; self.error=None; self.history_progress=0; self.history_total=int(logic.df.데이터역할.eq('검색이력').sum())
  self.history_complete=False
  self.signature=hashlib.sha256(json.dumps([settings.qwen_model,settings.embedding_model,settings.quantization,logic.CODEBOOK_HASH,logic.MASTER_HASH,hashlib.sha256(settings.voc_path.read_bytes()).hexdigest(),'web-v2-strict',settings.split_mode,settings.history_fraction,settings.top_k,settings.min_similarity,settings.min_support,settings.min_score_margin],ensure_ascii=False).encode()).hexdigest()
  self.teams=sorted(logic.department_master.loc[logic.department_master.routing_enabled,'department'].tolist())
  self.channels=pd.read_excel(settings.master_path,sheet_name='channel_master').fillna('')
  logic.assert_columns(self.channels,['raw_channel','code','label','channel_group','enabled'],'channel_master')
  logic.qwen_generate=self.qwen.generate; logic.restrict_routing_candidates=restrict_routing_candidates; logic.embed_model=self.embedding
  self.rebuild_index()
 def parse_channel(self,raw):
  raw=logic.clean_text(raw); code=raw.split()[0].upper() if raw else ''
  rows=self.channels.loc[self.channels.enabled.map(logic.enabled_flag) & (self.channels.raw_channel.eq(raw) | self.channels.code.eq(code))] if raw else self.channels.iloc[:0]
  if len(rows)!=1: return dict(raw=raw,code=code,label='확인 필요',group=None,status='미입력' if not raw else '미매핑')
  row=rows.iloc[0]; return dict(raw=raw,code=row.code,label=row.label,group=row.channel_group,status='DB확인')
 def row(self,id):
  rows=logic.df.loc[logic.df.번호.eq(str(id))]
  if len(rows)!=1: raise KeyError(id)
  return rows.iloc[0].drop(labels=['handling_team']).to_dict()
 def analyze(self,row,force=False):
  # No truth labels, origin/destination or database topic fields cross this boundary.
  assert 'handling_team' not in row and 'topic_code' not in row
  id=row['번호']; saved=self.store.analysis(id,self.signature)
  if saved and saved.get('analysis',{}).get('분석상태')=='분석완료' and not force: return saved
  t=time.perf_counter(); raw={}; stage='input'
  try:
   if not row['민원내용']: raise ValueError('민원내용 없음')
   stage='topic'; raw[stage]=logic.analyze_topic(row['민원내용']); topic=validate(raw[stage],stage)
   stage='cause'; raw[stage]=logic.analyze_cause(row['민원내용'],topic); cause=validate(raw[stage],stage)
   stage='routing'; raw[stage]=logic.analyze_routing(row['민원내용']); routing=validate(raw[stage],stage)
   analysis={**topic,**cause,**routing,**logic.lookup_location(routing['location_candidate']),**logic.lookup_function(topic['주요지코드']),'분석상태':'분석완료','라우팅분석상태':'완료'}
   result=dict(id=id,analysis=analysis,raw=raw,analysis_seconds=time.perf_counter()-t,model=settings.qwen_model)
  except Exception as exc:
   result=dict(id=id,analysis={'분석상태':'분석오류'},failed_stage=stage,error=f'{type(exc).__name__}: {exc}',raw=raw,analysis_seconds=time.perf_counter()-t,model=settings.qwen_model)
   log.exception('VOC %s %s 분석 실패',id,stage)
  self.store.record_recommendation(id,self.signature,result); return result
 def rebuild_index(self):
  records=[]
  for _,r in logic.df.loc[logic.df.데이터역할.eq('검색이력')].iterrows():
   p=self.store.analysis(r['번호'],self.signature)
   if p and p['analysis'].get('분석상태')=='분석완료' and r['handling_team']:
    records.append({**r.to_dict(),**p['analysis']})
  self.history_progress=len(records)
  if not records:
   logic.history_df=logic.attach_department_attributes(logic.df.iloc[:0]).reset_index(drop=True); logic.history_embeddings=np.zeros((0,384)); return
  frame=logic.attach_department_attributes(pd.DataFrame(records)); frame=frame.loc[frame.dept_routing_enabled.eq(True)].reset_index(drop=True)
  texts=frame.apply(logic.embedding_text,axis=1).tolist()
  key=hashlib.sha256(json.dumps([self.signature,texts,frame.번호.tolist()],ensure_ascii=False).encode()).hexdigest(); cache=settings.output/('embedding-'+key+'.npz')
  if cache.exists(): embeddings=np.load(cache,allow_pickle=False)['vectors']
  else:
   embeddings=self.embedding.encode(texts,batch_size=16,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
   temp=cache.with_suffix('.tmp.npz'); np.savez_compressed(temp,vectors=embeddings); temp.replace(cache)
  logic.history_df=frame; logic.history_embeddings=embeddings
 def prepare_history(self,limit=None):
  self.qwen.load(); self.embedding.load(); self.ready=True
  rows=logic.df.loc[logic.df.데이터역할.eq('검색이력')]
  if limit is not None: rows=rows.head(limit)
  for i,(_,r) in enumerate(rows.iterrows()):
   with self.lock:
    self.analyze(r.drop(labels=['handling_team']).to_dict())
    if (i+1)%10==0: self.rebuild_index()
   if (i+1)%10==0: log.info('과거 이력 분석 %s/%s',i+1,len(rows))
  with self.lock: self.rebuild_index()
  self.history_complete=limit is None
 def start(self):
  try: self.prepare_history()
  except Exception as exc: self.error=f'{type(exc).__name__}: {exc}'; log.exception('서버 모델/이력 초기화 실패')
 def recommend(self,id,mode='C',force=False):
  with self.lock:
   row=self.row(id)
   if row['데이터역할']!='검토대상' and settings.split_mode=='holdout': raise ValueError('holdout 평가 VOC만 추천 가능합니다')
   if logic.history_df.empty: raise RuntimeError('분석 완료된 과거 이력이 없습니다. 이력 준비 상태를 확인하세요.')
   t=time.perf_counter(); result=self.analyze(row,force)
   if result['analysis'].get('분석상태')!='분석완료': return result
   original=logic.restrict_routing_candidates
   if mode=='A': logic.restrict_routing_candidates=lambda r:(logic.history_df,'A: 전체 검색')
   elif mode=='B':
    def regional(r): return restrict_routing_candidates({**r,'업무기능후보':[]})
    logic.restrict_routing_candidates=regional
   try: rec=logic.recommend_department({**row,**result['analysis']})
   finally: logic.restrict_routing_candidates=original
   ranking=rec['top_departments'].head(settings.top_n).to_dict('records')
   for i,x in enumerate(ranking,1): x.update(ranking=i,support_count=x['count'])
   result={**result,'recommendation':{k:v for k,v in rec.items() if k not in {'top_departments','similar_vocs'}},'ranking':ranking,'evidence':rec['similar_vocs'][['번호','handling_team','similarity','민원내용']].head(settings.top_k).to_dict('records'),'total_seconds':time.perf_counter()-t,'history_count':len(logic.history_df),'history_complete':self.history_complete,'mode':mode}
   if mode=='C': self.store.record_recommendation(id,self.signature,result)
   return result
 def detail(self,id):
  row=self.row(id); result=self.store.analysis(str(id),self.signature) or {}; a=result.get('analysis',{}); rec=result.get('recommendation',{})
  saved=self.store.load_approvals().get(str(id)); saved=saved if saved and saved.get('signature')==self.signature else None
  status=saved['status'] if saved else '확인대기' if rec else '분석완료' if a.get('분석상태')=='분석완료' else '분석오류' if result.get('error') else '분석대기'
  return dict(id=str(id),title=logic.clean_text(row['subject']),body=row['민원내용'],channel=self.parse_channel(row['intake_channel'])['label'],channel_info=self.parse_channel(row['intake_channel']),date='미제공',topic=(str(a.get('주요지코드',''))+' · '+str(a.get('주요지',''))) if a else '미분석',sub=a.get('부요지') or '없음',cause=logic.cause_text(a) or '미분석',keywords=a.get('핵심키워드','').split(', ') if a else [],location=a.get('location_candidate'),hq=a.get('관할본부'),function=a.get('업무기능') or '확인 필요',scope=a.get('routing_scope','미분석'),locationStatus=a.get('위치매핑상태','미분석'),routing=rec.get('routing_filter_info','미분석'),recs=[dict(name=x['department'],fn=a.get('업무기능') or '확인 필요',score=x['score'],similarity=x['mean_similarity'],count=x['support_count']) for x in result.get('ranking',[])],reason=rec.get('reason') or result.get('error') or '분석을 실행하세요.',scopeNote='전체 과거 이력 준비 완료' if self.history_complete else f'이력 준비 중: 현재 {len(logic.history_df)}건 검색 가능',hold=rec.get('status')!='추천가능',status=status,decision=saved,result=result)
 def save_decision(self,id,department,status,memo):
  detail=self.detail(id)
  if not detail['result'].get('recommendation'): raise ValueError('분석과 추천을 완료한 뒤 승인/보류할 수 있습니다')
  return self.store.save_decision(str(id),department,status,memo,self.teams,detail['result']['recommendation'].get('recommended_department'),self.signature)
'''
for n,s in files.items(): Path(n).write_text(s,encoding='utf-8')
