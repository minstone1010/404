from pathlib import Path
p=Path('backend/service.py'); s=p.read_text().replace("if (i+1)%10==0: log.info('과거 이력 분석 %s/%s',i+1,len(rows))","if (i+1)%10==0: log.info('과거 이력 분석 %s/%s',i+1,len(rows))\n   time.sleep(0.01)"); p.write_text(s)
Path('e2e_real.py').write_text('''from playwright.sync_api import sync_playwright
import json,time
from pathlib import Path
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']); page=browser.new_page(viewport={'width':1440,'height':1100}); errors=[]; page.on('pageerror',lambda e:errors.append(str(e))); page.set_default_timeout(300000)
 page.goto('http://127.0.0.1:8001'); page.wait_for_selector('.voc-item'); page.locator('.voc-item[data-id="900001"]').click()
 started=time.perf_counter()
 with page.expect_response(lambda r:'/900001/analyze' in r.url and r.request.method=='POST',timeout=300000) as event: page.locator('#analyze').click()
 response=event.value; result=response.json(); print('ANALYSIS',response.status,result.get('error'),flush=True); assert response.status==200 and result['analysis']['분석상태']=='분석완료',result
 page.wait_for_function("!document.getElementById('approve').disabled")
 assert page.locator('.analysis-value').first.inner_text()!='미분석'
 assert len(result['ranking'])<=3
 choices=page.locator('#department option').all_text_contents(); page.locator('#department').select_option(label=choices[1])
 with page.expect_response(lambda r:'/900001/decision' in r.url) as event: page.locator('#approve').click()
 assert event.value.status==200
 page.wait_for_selector('.decision-saved'); page.reload(); page.wait_for_selector('.decision-saved'); assert '승인완료' in page.locator('.decision-saved').inner_text()
 with page.expect_response(lambda r:'/900001/decision' in r.url) as event: page.locator('#hold').click()
 assert event.value.status==200
 page.wait_for_function("document.querySelector('.decision-saved')?.textContent.includes('보류')")
 page.reload(); page.wait_for_selector('.decision-saved'); assert '보류' in page.locator('.decision-saved').inner_text()
 page.screenshot(path='outputs/ui_e2e.png',full_page=True)
 report=dict(real_qwen=True,real_embedding=True,analysis=result['analysis'],ranking=result['ranking'],history_count=result['history_count'],approval=True,hold=True,persist_after_reload=True,browser_errors=errors,wall_seconds=time.perf_counter()-started)
 Path('outputs/e2e_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)); assert not errors; print(json.dumps(report,ensure_ascii=False,indent=2)); browser.close()
''')
