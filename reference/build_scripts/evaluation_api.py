from pathlib import Path
p=Path('backend/main.py'); s=p.read_text().replace('from contextlib import asynccontextmanager','from typing import Literal\nfrom contextlib import asynccontextmanager').replace('def analyze(id:str,force:bool=False): return safe(lambda:svc().recommend(id,force=force))',"def analyze(id:str,force:bool=False,mode:Literal['A','B','C']='C'): return safe(lambda:svc().recommend(id,mode=mode,force=force))"); p.write_text(s)
p=Path('backend/cli.py'); s=p.read_text().replace("p.add_argument('--allow-partial',action='store_true');", "p.add_argument('--allow-partial',action='store_true'); p.add_argument('--api-url');")
s=s.replace("if not (s.store.analysis(r['번호'],s.signature) or {}).get('analysis',{}).get('분석상태')=='분석완료'","if s.store.analysis(r['번호'],s.signature) is None")
s=s.replace("s.history_complete=not missing; s.qwen.load()","s.history_complete=not missing\n if not args.api_url: s.qwen.load()")
s=s.replace("output=s.recommend(row['번호'],mode); results.append", "if args.api_url:\n    import httpx\n    response=httpx.post(args.api_url.rstrip('/')+'/api/vocs/'+row['번호']+'/analyze',params={'mode':mode},timeout=600); response.raise_for_status(); output=response.json()\n   else: output=s.recommend(row['번호'],mode)\n   results.append")
s=s.replace("report['gpu_peak_allocated_mb']=torch.cuda.max_memory_allocated()/1024**2 if torch.cuda.is_available() else 0","report['gpu_peak_allocated_mb']=None if args.api_url else torch.cuda.max_memory_allocated()/1024**2 if torch.cuda.is_available() else 0\n report['gpu_measurement_note']='API 서버 모드에서는 서버 /api/stats의 VRAM 값을 참조' if args.api_url else '현재 평가 프로세스 PyTorch peak allocated'")
p.write_text(s)
# Server GPU stats expose real measured memory.
p=Path('backend/main.py'); s=p.read_text().replace("def stats():\n return dict", "def stats():\n import torch\n gpu=dict(allocated_mb=torch.cuda.memory_allocated()/1024**2,peak_allocated_mb=torch.cuda.max_memory_allocated()/1024**2,reserved_mb=torch.cuda.memory_reserved()/1024**2) if torch.cuda.is_available() else None\n return dict(gpu=gpu,")
# Correct replacement: original dict opening gets replaced with dict(gpu=gpu, followed by original '(' remnants? 
s=s.replace('dict(gpu=gpu,(total=', 'dict(gpu=gpu,total=')
p.write_text(s)
