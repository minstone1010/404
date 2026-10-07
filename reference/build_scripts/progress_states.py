from pathlib import Path
p=Path('backend/service.py'); s=p.read_text(); s=s.replace('self.history_complete=False','self.history_complete=False; self.history_preparation_done=False; self.history_failed=0')
s=s.replace('self.history_complete=self.history_progress==self.history_total','self.history_complete=self.history_progress==self.history_total\n  self.history_preparation_done=limit is None\n  self.history_failed=self.history_total-self.history_progress if limit is None else 0')
s=s.replace("scopeNote='전체 과거 이력 준비 완료' if self.history_complete else", "scopeNote=('전체 과거 이력 준비 완료' if self.history_complete else f'이력 준비 종료: 분석 오류 {self.history_failed}건') if self.history_preparation_done else")
p.write_text(s)
p=Path('backend/main.py'); s=p.read_text().replace('history_complete=svc().history_complete,','history_complete=svc().history_complete,history_preparation_done=svc().history_preparation_done,history_failed=svc().history_failed,'); p.write_text(s)
p=Path('voc-ui/dist/app.js'); s=p.read_text(); s=s.replace("stats.history_complete?' · 준비 완료':' · 준비 중'","stats.history_complete?' · 준비 완료':stats.history_preparation_done?` · 종료(오류 ${stats.history_failed}건)`:' · 준비 중'")
s+='''\nsetInterval(async()=>{try{const s=await api('/api/stats');document.querySelector('.demo-badge').textContent=s.initialization_error?'초기화 실패':`과거 이력 ${s.history_searchable}/${s.history_total}건${s.history_complete?' · 준비 완료':s.history_preparation_done?' · 준비 종료':' · 준비 중'}`;}catch(e){console.error(e);}},10000);\n'''; p.write_text(s)
