import json,pathlib,zipfile,shutil,ast
root=pathlib.Path.cwd()
(root/'reference').mkdir(exist_ok=True); (root/'data').mkdir(exist_ok=True)
for name in ['korail_voc_routing_master.xlsx','voc_dummy_2500_v3_해설판.xlsx']: shutil.copy2(pathlib.Path('/mnt/c/Users/win/Desktop')/name,root/'data'/name)
p=pathlib.Path('/mnt/c/Users/win/Desktop/2안_설계_라우팅개선본.ipynb'); nb=json.loads(p.read_text(encoding='utf-8')); shutil.copy2(p,root/'reference'/p.name)
for i,c in enumerate(nb['cells']):
 if c['cell_type']=='code':
  s=''.join(c['source']); (root/'reference'/f'cell_{i}.py.txt').write_text(s); print(i,len(s),[n.name for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)] if not s.startswith('%') else 'pip')
with zipfile.ZipFile('/mnt/c/Users/win/Desktop/voc-ui.zip') as z:
 print('ZIP',z.namelist())
 for n in z.namelist():
  if not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts: z.extract(n,root)
