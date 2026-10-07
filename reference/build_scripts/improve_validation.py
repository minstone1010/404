from pathlib import Path
p=Path('backend/service.py'); s=p.read_text(); marker=' def analyze(self,row,force=False):'
method=''' def analyzed_stage(self,stage,generate,raw):
  original=logic.qwen_generate
  feedback=''
  try:
   for attempt in range(2):
    logic.qwen_generate=lambda prompt,tokens: original(prompt+feedback,tokens)
    raw[stage]=generate()
    try: return validate(raw[stage],stage)
    except ValueError as exc:
     raw.setdefault('validation_errors',[]).append({'stage':stage,'attempt':attempt+1,'error':str(exc),'response':raw[stage]})
     if attempt==1: raise
     feedback='\\n[재시도 검증 오류] '+str(exc)+'\\n이 오류를 수정하세요. 모든 필수 필드를 포함하고 주·부 요지코드는 서로 달라야 하며 부요지가 없으면 JSON null을 사용하세요.'
  finally: logic.qwen_generate=original
'''
s=s.replace(marker,method+marker)
s=s.replace("raw[stage]=logic.analyze_topic(row['민원내용']); topic=validate(raw[stage],stage)","topic=self.analyzed_stage(stage,lambda:logic.analyze_topic(row['민원내용']),raw)")
s=s.replace("raw[stage]=logic.analyze_cause(row['민원내용'],topic); cause=validate(raw[stage],stage)","cause=self.analyzed_stage(stage,lambda:logic.analyze_cause(row['민원내용'],topic),raw)")
s=s.replace("raw[stage]=logic.analyze_routing(row['민원내용']); routing=validate(raw[stage],stage)","routing=self.analyzed_stage(stage,lambda:logic.analyze_routing(row['민원내용']),raw)")
p.write_text(s)
Path('browser_test.py').write_text('''from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1100}); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8001'); page.wait_for_selector('.voc-item',timeout=120000)
 assert page.locator('.voc-item').count()==512
 assert page.locator('#analyze').count()==1
 assert page.locator('#approve').is_disabled()
 page.locator('#search').fill('900001'); assert page.locator('.voc-item').count()==1
 page.locator('#search').fill(''); page.screenshot(path='outputs/ui_initial.png',full_page=True)
 print(json.dumps({'list_count':512,'search':True,'approve_before_analysis_disabled':True,'browser_errors':errors}))
 assert not errors; browser.close()
''')
