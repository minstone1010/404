from pathlib import Path
import sqlite3,json
p=Path('outputs/voc.sqlite3')
with sqlite3.connect(p) as db:
 test=[json.loads(r[0]) for r in db.execute('SELECT payload FROM decision_events WHERE id=?',('900001',))]
 Path('outputs/e2e_decision_events.json').write_text(json.dumps(test,ensure_ascii=False,indent=2))
 db.execute('DELETE FROM decisions WHERE id=?',('900001',)); db.execute('DELETE FROM decision_events WHERE id=?',('900001',))
