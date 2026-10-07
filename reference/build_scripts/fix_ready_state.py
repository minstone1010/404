from pathlib import Path
p=Path('backend/service.py'); s=p.read_text().replace("self.history_preparation_done=limit is None", "self.history_preparation_done=limit is None")
# Index completeness indicates a finished preparation pass; errors remain counted separately.
s=s.replace('self.history_complete=self.history_progress==self.history_total','self.history_complete=limit is None')
p.write_text(s)
p=Path('backend/main.py'); s=p.read_text().replace("history_failed=svc().history_failed,", "history_failed=svc().history_failed,")
p.write_text(s)
p=Path('voc-ui/dist/app.js'); s=p.read_text(); s=s.replace("stats.history_complete?' · 준비 완료':stats.history_preparation_done?` · 종료(오류 ${stats.history_failed}건)`:' · 준비 중'", "stats.history_preparation_done?` · 준비 완료(오류 ${stats.history_failed}건)`:' · 준비 중'")
s=s.replace("s.history_complete?' · 준비 완료':s.history_preparation_done?' · 준비 종료':' · 준비 중'", "s.history_preparation_done?` · 준비 완료(오류 ${s.history_failed}건)`:' · 준비 중'")
p.write_text(s)
# Record matched department attributes for persisted results generated before the UI attribute fix.
import sqlite3,json
with sqlite3.connect('outputs/voc.sqlite3') as db:
 for id,signature,payload in db.execute('SELECT id,signature,payload FROM analyses').fetchall():
  result=json.loads(payload)
  if result.get('ranking'):
   from backend import notebook_logic as l
   for item in result['ranking']:
    d=l.department_master.loc[l.department_master.department.eq(item['department'])].iloc[0]
    item.update(business_function=d.business_function,region_code=d.region_code,scope=d.scope,parent_org=d.parent_org)
   db.execute('UPDATE analyses SET payload=? WHERE id=?',(json.dumps(result,ensure_ascii=False),id))
