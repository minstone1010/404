from pathlib import Path
Path('pytest.ini').write_text('[pytest]\ntestpaths = tests\npython_files = test_*.py\n')
Path('tests/conftest.py').write_text('import os\nos.environ.setdefault("HF_HUB_OFFLINE","1")\n')
for name in ['finalize_code.py','fix_ready_state.py']:
 p=Path(name)
 if p.exists(): p.replace(Path('reference/build_scripts')/name)
