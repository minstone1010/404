from pathlib import Path
p=Path('backend/service.py'); s=p.read_text(); marker=' def save_decision(self,id,department,status,memo):'
method=''' def evaluate(self,limit=None):
  if settings.split_mode!='holdout': raise ValueError('평가는 holdout에서만 가능합니다')
  with self.lock:
   ids=logic.df.loc[logic.df.데이터역할.eq('검토대상'),'번호'].tolist()
   if limit is not None: ids=ids[:limit]
   return [dict(id=id,mode=mode,output=self.recommend(id,mode)) for id in ids for mode in ['A','B','C']]
'''
s=s.replace(marker,method+marker); p.write_text(s)
p=Path('backend/main.py'); s=p.read_text().replace('from fastapi import FastAPI,HTTPException','from fastapi import FastAPI,HTTPException,Query'); marker="@app.get('/api/export')"
s=s.replace(marker,"@app.post('/api/evaluate')\ndef evaluate(limit:int | None=Query(default=None,ge=1)): return safe(lambda:svc().evaluate(limit))\n"+marker); p.write_text(s)
p=Path('backend/cli.py'); s=p.read_text(); old="truth=logic.evaluation_truth_df.set_index('번호'); results=[]"
new="""truth=logic.evaluation_truth_df.set_index('번호'); results=[]
 remote={}
 if args.api_url:
  import httpx
  response=httpx.post(args.api_url.rstrip('/')+'/api/evaluate',params={'limit':args.limit} if args.limit else {},timeout=None); response.raise_for_status()
  remote={(x['id'],x['mode']):x['output'] for x in response.json()}
"""
s=s.replace(old,new)
s=s.replace("import httpx\n    response=httpx.post(args.api_url.rstrip('/')+'/api/vocs/'+row['번호']+'/analyze',params={'mode':mode},timeout=600); response.raise_for_status(); output=response.json()","output=remote[(row['番号'] if '番号' in row else row['번호'],mode)]")
s=s.replace("'history_count':len(logic.history_df)","'history_count':results[0]['output'].get('history_count',len(logic.history_df)) if results else 0")
p.write_text(s)
p=Path('README.md'); s=p.read_text().replace('서버가 이력을 늘리는 중인 제한 평가는 비교 인덱스가 달라질 수 있으므로 완성된 이력과 고정 인덱스에서 최종 비교하세요.','API 평가도 한 요청에서 인덱스를 잠가 A/B/C 비교 중 이력이 바뀌지 않도록 합니다. 평가 중에는 분석 요청이 대기할 수 있으므로 전체 평가는 별도 CLI와 준비 완료된 이력을 사용하세요.').replace('POST /api/vocs/{id}/analyze, /api/vocs/{id}/decision.','POST /api/vocs/{id}/analyze, /api/vocs/{id}/decision, /api/evaluate.'); p.write_text(s)
