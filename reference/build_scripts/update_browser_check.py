from pathlib import Path
p=Path('scripts/browser_smoke.py'); s=p.read_text().replace("assert page.locator('#approve').is_disabled()", "rows=page.request.get('http://127.0.0.1:8001/api/vocs').json()\n target=next(v['id'] for v in rows if v['status']=='분석대기')\n page.locator(f'.voc-item[data-id=\"{target}\"]').click()\n assert page.locator('#approve').is_disabled()")
p.write_text(s)
