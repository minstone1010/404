from pathlib import Path
p=Path('backend/config.py'); s=p.read_text().replace("os.getenv('PORT','8000')","os.getenv('PORT','8001')"); p.write_text(s)
p=Path('.env.example'); s=p.read_text().replace('PORT=8000','PORT=8001'); p.write_text(s); Path('.env').write_text(s)
Path('backend/__main__.py').write_text('from backend.config import settings\nimport uvicorn\nif __name__=="__main__": uvicorn.run("backend.main:app",host=settings.host,port=settings.port,workers=1)\n')
p=Path('backend/service.py'); s=p.read_text().replace("'total_seconds':time.perf_counter()-t","'total_seconds':result['analysis_seconds']+time.perf_counter()-t")
s=s.replace('self.history_complete=limit is None','self.history_complete=self.history_progress==self.history_total')
p.write_text(s)
Path('requirements.txt').write_text('''torch==2.14.1
transformers==5.18.0
sentence-transformers==6.1.0
accelerate==1.15.0
bitsandbytes==0.50.2
pandas==3.0.6
openpyxl==3.1.5
fastapi==0.142.2
uvicorn==0.54.0
python-dotenv==1.2.4
scikit-learn==1.9.1
numpy==2.4.6
httpx==0.28.1
pytest==9.1.1
''')
Path('environment.yml').write_text('''name: voc
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
      - -r requirements.txt
''')
Path('requirements-test.txt').write_text('-r requirements.txt\nplaywright==1.63.0\n')
Path('.gitignore').write_text('.env\n__pycache__/\n.pytest_cache/\noutputs/*\n!outputs/.gitkeep\n')
Path('outputs/.gitkeep').touch()
