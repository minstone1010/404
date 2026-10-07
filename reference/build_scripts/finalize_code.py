from pathlib import Path
p=Path('backend/service.py'); s=p.read_text().replace("for i,x in enumerate(ranking,1): x.update(ranking=i,support_count=x['count'])","for i,x in enumerate(ranking,1):\n    attrs=logic.department_master.loc[logic.department_master.department.eq(x['department'])].iloc[0]\n    x.update(ranking=i,support_count=x['count'],business_function=attrs.business_function,region_code=attrs.region_code,scope=attrs.scope,parent_org=attrs.parent_org)")
s=s.replace("fn=a.get('업무기능') or '확인 필요',score=x['score']","fn=str(x.get('scope','확인 필요'))+' · '+str(x.get('business_function','확인 필요')),score=x['score']")
p.write_text(s)
p=Path('backend/cli.py'); s=p.read_text(); s=s.replace("report['gpu_peak_allocated_mb']=", "report['comparison_index_consistent']=all(len({x['output'].get('history_count') for x in results if x['id']==id})==1 for id in {x['id'] for x in results})\n report['gpu_peak_allocated_mb']=")
s=s.replace("from backend.config import settings", "from backend.config import settings\nimport argparse as _argparse")
s=s.replace("s=Service()\n if args.command", "if args.limit is not None and args.limit<1: p.error('--limit는 양수여야 합니다')\n if args.command=='evaluate' and settings.split_mode!='holdout': p.error('평가는 SPLIT_MODE=holdout에서만 가능합니다')\n s=Service()\n if args.command")
p.write_text(s)
p=Path('tests/test_system.py'); s=p.read_text()+'''
def test_validation_retry_records_raw(monkeypatch):
 s=Service.__new__(Service)
 calls=[]
 def generate(prompt,tokens):
  calls.append(prompt)
  return '{"main_topic_code":"D1","sub_topic_code":"D1","keywords":["고장","시설","불편"]}' if len(calls)==1 else '{"main_topic_code":"D1","sub_topic_code":null,"keywords":["고장","시설","불편"]}'
 monkeypatch.setattr(l,'qwen_generate',generate)
 raw={}; output=s.analyzed_stage('topic',lambda:l.qwen_generate('원문 프롬프트',128),raw)
 assert output['부요지코드'] is None
 assert len(raw['validation_errors'])==1
 assert '재시도 검증 오류' in calls[1]
 assert l.qwen_generate is generate
'''; p.write_text(s)
Path('scripts').mkdir(exist_ok=True)
for old,new in [('browser_test.py','scripts/browser_smoke.py'),('e2e_real.py','scripts/e2e_real.py'),('smoke_data.py','scripts/smoke_data.py')]:
 p=Path(old)
 if p.exists(): p.replace(new)
Path('reference/build_scripts').mkdir(exist_ok=True)
for name in ['inspect_excel.py','inspect_master.py','refactor.py','build_modules.py','build_service.py','build_api_ui.py','build_tests.py','configure.py','serve_test.py','improve_validation.py','progress_states.py','query_candidates.py','build_e2e.py','evaluation_api.py','archive_test_decisions.py','write_docs.py']:
 p=Path(name)
 if p.exists(): p.replace(Path('reference/build_scripts')/name)
# Entry scripts are imported from scripts/; add project root to sys.path.
for p in Path('scripts').glob('*.py'):
 p.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent.parent))\n'+p.read_text())
p=Path('README.md'); s=p.read_text().replace('Notebook: 21개 셀.','Notebook: '+str(len(__import__('json').loads(next(Path('reference').glob('*.ipynb')).read_text())['cells']))+'개 셀.').replace(' tests/','tests/'); p.write_text(s)
