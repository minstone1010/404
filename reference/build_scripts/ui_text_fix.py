from pathlib import Path
p=Path('voc-ui/dist/app.js'); s=p.read_text(); s=s.replace("${v.id.replace('VOC-','#')}","${esc(v.id.replace('VOC-','#'))}")
s=s.replace('부 요지 ${esc(v.sub)} · 발생 원인 ${esc(v.cause)}</div>','부 요지 ${esc(v.sub)} · 발생 원인 ${esc(v.cause)}</div><div class="subtopic">${esc(v.result.analysis?.발생원인_판단이유||\'\')}</div>')
s=s.replace("${esc(v.location||'위치 확인 필요')}","${esc(v.location||(v.scope==='전국형'?'현장 위치 지정 없음':'위치 확인 필요'))}")
s=s.replace("${esc(v.locationStatus)}","${esc(v.locationStatus)}${v.result.analysis?.표준위치?' · 표준위치 '+esc(v.result.analysis.표준위치):''}")
s=s.replace("${esc(v.hq||'확인 필요')}","${esc(v.scope==='전국형'?'지역본부 제한 없음':v.hq||'확인 필요')}")
s=s.replace("${v.hold?'추천 보류 · 후보 검토':'추천 가능'}","${v.result.recommendation?(v.hold?'추천 보류 · 후보 검토':'추천 가능'):'미분석'}")
p.write_text(s)
