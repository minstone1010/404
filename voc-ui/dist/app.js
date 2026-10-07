let samples = [],
  decisions = {},
  departments = [],
  selectedId = null,
  filter = "all",
  search = "",
  selectedDepartment = "",
  toastTimer;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
} [c]));
const statusOf = id => decisions[id]?.status || ({
  '분석대기': 'waiting',
  '분석완료': 'analyzed',
  '분석오류': 'failed'
} [samples.find(v => v.id === id)?.status] || 'pending');
const statusNames = {
  pending: '확인대기',
  approved: '승인완료',
  held: '보류',
  waiting: '분석대기',
  analyzed: '분석완료',
  failed: '분석오류'
};

function notify(message) {
  const t = document.getElementById('toast');
  t.textContent = message;
  t.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('visible'), 3200);
}

function renderMetrics() {
  const pending = samples.filter(v => ['pending', 'waiting', 'analyzed', 'failed'].includes(
      statusOf(v.id))).length,
    approved = samples.filter(v => statusOf(v.id) === 'approved').length,
    held = samples.filter(v => statusOf(v.id) === 'held').length;
  document.getElementById('metrics').innerHTML = [
    ['검토 대상', samples.length, '평가 VOC', '▦', ''],
    ['확인 대기', pending, '담당자 검토 필요', '◷', ''],
    ['승인 완료', approved, '최종 부서 선택 완료', '✓', 'green'],
    ['보류', held, '추가 확인 필요', 'Ⅱ', 'amber']
  ].map(([label, value, sub, icon, color]) =>
    `<div class="metric ${color}"><div><div class="metric-label">${label}</div><div class="metric-value">${value}<span style="font-size:13px;font-weight:400;color:#91a0b5;margin-left:5px">건</span></div><div class="metric-sub">${sub}</div></div><span class="metric-icon" aria-hidden="true">${icon}</span></div>`
    ).join('');
  document.getElementById('nav-count').textContent = pending;
}

function filtered() {
  return samples.filter(v => (filter === 'all' || statusOf(v.id) === filter || (filter ===
    'pending' && ['waiting', 'analyzed', 'failed'].includes(statusOf(v.id)))) && (
    `${v.id} ${v.title} ${v.body}`).toLowerCase().includes(search.toLowerCase()));
}

function renderList() {
  const rows = filtered();
  document.getElementById('list-count').textContent = `${rows.length}건`;
  document.getElementById('voc-list').innerHTML = rows.length ? rows.map(v =>
    `<button class="voc-item ${v.id===selectedId?'selected':''}" data-id="${esc(v.id)}" aria-pressed="${v.id===selectedId}"><div class="item-meta"><span>${esc(v.id.replace('VOC-','#'))}</span><span class="status ${statusOf(v.id)}">${statusNames[statusOf(v.id)]}</span></div><h3>${esc(v.title)}</h3><div class="item-foot"><span>${esc(v.channel)}</span><span>·</span><span>${esc(v.scope)}</span></div></button>`
    ).join('') : '<div class="empty">조건에 맞는 민원이 없습니다.</div>';
  document.querySelectorAll('.voc-item').forEach(b => b.addEventListener('click', () => {
    selectedId = b.dataset.id;
    renderList();
    renderDetail();
  }));
}

function recommendationCard(rec, index) {
  return `<label class="rec-card ${selectedDepartment===rec.name?'chosen':''}"><div class="rec-top"><span class="rank ${index?'secondary':''}">추천 ${index+1}순위</span><input type="radio" name="recommended-department" value="${esc(rec.name)}" ${selectedDepartment===rec.name?'checked':''} aria-label="${index+1}순위 ${esc(rec.name)} 선택"></div><div class="rec-name">${esc(rec.name)}</div><div class="rec-function">${esc(rec.fn)}</div><div class="score-row"><span>추천 점수</span><strong>${rec.score.toFixed(3)}</strong></div><div class="bar" aria-hidden="true"><span style="width:${rec.score*100}%"></span></div><div class="rec-evidence"><span>유사 처리 사례 <b>${rec.count}건</b></span><span>평균 유사도 ${rec.similarity.toFixed(3)}</span></div></label>`;
}

function renderDetail() {
  const v = samples.find(x => x.id === selectedId);
  if (!v) {
    document.getElementById('detail-area').textContent = '검토 대상이 없습니다.';
    return;
  }
  const saved = decisions[v.id];
  selectedDepartment = saved?.department || (v.hold ? '' : v.recs[0]?.name) || '';
  document.getElementById('detail-area').innerHTML =
    `
 <section class="panel"><div class="detail-header"><div class="detail-topline"><span class="record-code">${esc(v.id)} · 민원 상세</span><span class="status ${statusOf(v.id)}">${statusNames[statusOf(v.id)]}</span></div><h2>${esc(v.title)}</h2><button class="button primary" id="analyze">${v.result.execution_source==='manual'?'AI 재분석 · 추천 실행':'AI 분석 · 추천 실행'}</button><div class="record-meta"><span>접수경로 ${esc(v.channel)}</span><span>접수일시 ${esc(v.date)}</span>${v.result.execution_source==='manual'?`<span>사용자 실행 분석 · ${esc(new Date(v.result.analyzed_at).toLocaleString('ko-KR'))}</span>`:''}</div></div><div class="record-body"><span class="section-label">민원 원문</span><p class="complaint">${esc(v.body)}</p></div><div class="analysis"><div><span class="section-label">요지 분석</span><div class="analysis-value">${esc(v.topic)}</div><div class="subtopic">부 요지 ${esc(v.sub)} · 발생 원인 ${esc(v.cause)}</div><div class="subtopic">${esc(v.result.analysis?.발생원인_판단이유||'')}</div></div><div><span class="section-label">핵심 키워드</span><div class="chips">${v.keywords.map(k=>`<span class="chip">${esc(k)}</span>`).join('')}</div></div></div></section>
 <section class="panel routing-panel"><div class="panel-title"><h2>지역 · 업무 라우팅</h2><small>위치 추출 + 기준표 조회</small></div><div class="routing-grid"><div class="routing-field"><span class="section-label">추출 위치</span><strong>${esc(v.location||(v.scope==='전국형'?'현장 위치 지정 없음':'위치 확인 필요'))}</strong><small>${esc(v.locationStatus)}${v.result.analysis?.표준위치?' · 표준위치 '+esc(v.result.analysis.표준위치):''}</small></div><div class="routing-field"><span class="section-label">관할본부</span><strong>${esc(v.scope==='전국형'?'지역본부 제한 없음':v.hq||'확인 필요')}</strong><small>location_master</small></div><div class="routing-field"><span class="section-label">업무기능</span><strong>${esc(v.function)}</strong><small>topic_function_map</small></div><div class="routing-field"><span class="section-label">routing_scope</span><strong>${esc(v.scope)}</strong><small>Qwen 문맥 판별</small></div></div><div class="routing-note ${v.hold?'warning':''}">${esc(v.routing)}</div></section>
 <section class="panel recommendation-panel"><div class="panel-title"><h2>처리부서 추천</h2><span class="status ${v.hold?'held':'approved'}">${v.result.recommendation?(v.hold?'추천 보류 · 후보 검토':'추천 가능'):'미분석'}</span></div><div class="rec-body">${v.recs.length?`<div class="rec-grid">${v.recs.map(recommendationCard).join('')}</div>`:'<div class="empty">추천 후보가 없습니다. 분석 상태와 검색 근거를 확인하세요.</div>'}<p class="reason">${esc(v.reason)}</p><p class="subtopic">${esc(v.scopeNote)} · 추천 점수는 정확도 확률이 아닙니다.</p></div><div class="decision-area"><div class="decision-form"><label for="department">최종 처리부서<select id="department"><option value="">부서를 선택하세요</option>${departments.map(d=>`<option value="${esc(d)}" ${d===selectedDepartment?'selected':''}>${esc(d)}</option>`).join('')}</select></label><label for="memo">검토 메모<textarea id="memo" placeholder="선택 변경 또는 보류 사유를 입력하세요">${esc(saved?.memo||'')}</textarea></label></div><div class="action-row"><span class="decision-note">담당자 승인 후 최종 부서가 확정됩니다.</span><div class="actions"><button type="button" class="button secondary" id="hold">보류</button><button type="button" class="button primary" id="approve">선택 부서 승인</button></div></div>${saved?`<div class="decision-saved">저장된 상태: ${statusNames[saved.status]}${saved.department?' · '+esc(saved.department):''}</div>`:''}</div></section>`;
  document.querySelectorAll('input[name="recommended-department"]').forEach(r => r.addEventListener(
    'change', () => {
      document.getElementById('department').value = r.value;
      syncSelection(r.value);
    }));
  document.getElementById('department').addEventListener('change', e => syncSelection(e.target
    .value));
  document.getElementById('analyze').addEventListener('click', analyzeSelected);
  document.getElementById('approve').disabled = !v.result.recommendation;
  document.getElementById('hold').disabled = !v.result.recommendation;
  document.getElementById('approve').addEventListener('click', () => saveDecision('approved'));
  document.getElementById('hold').addEventListener('click', () => saveDecision('held'));
}

function syncSelection(value) {
  selectedDepartment = value;
  document.querySelectorAll('.rec-card').forEach(c => {
    const r = c.querySelector('input');
    r.checked = r.value === value;
    c.classList.toggle('chosen', r.checked);
  });
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  });
  if (!response.ok) {
    let body = await response.text();
    throw new Error(body);
  }
  return response.json();
}
async function reload() {
  const rows = await api('/api/vocs');
  samples = rows;
  decisions = {};
  for (const v of samples) {
    if (v.decision) decisions[v.id] = {
      status: v.decision.status === '승인완료' ? 'approved' : 'held',
      department: v.decision.department,
      memo: v.decision.memo
    };
  }
  if (!samples.some(v => v.id === selectedId)) selectedId = samples[0]?.id;
  renderMetrics();
  renderList();
  renderDetail();
  const stats = await api('/api/stats');
  document.querySelector('.demo-badge').textContent = stats.initialization_error ? '초기화 실패' :
    `과거 이력 ${stats.history_searchable}/${stats.history_total}건${stats.history_preparation_done?` · 준비 완료(오류 ${stats.history_failed}건)`:' · 준비 중'}`;
  if (stats.initialization_error) notify(stats.initialization_error);
}
async function saveDecision(status) {
  const id = selectedId,
    department = document.getElementById('department').value,
    memo = document.getElementById('memo').value.trim();
  if (status === 'approved' && !departments.includes(department)) {
    notify('최종 부서를 선택하세요.');
    return;
  }
  document.getElementById('approve').disabled = true;
  document.getElementById('hold').disabled = true;
  try {
    await api(`/api/vocs/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        status: status === 'approved' ? '승인완료' : '보류',
        department,
        memo
      })
    });
    await reload();
    notify('결과를 Backend에 저장했습니다.');
  } catch (e) {
    notify('저장실패: ' + e.message);
    document.getElementById('approve').disabled = false;
    document.getElementById('hold').disabled = false;
  }
}
async function analyzeSelected() {
  const id = selectedId;
  document.getElementById('analyze').disabled = true;
  notify('AI 분석 중입니다.');
  try {
    const result = await api(`/api/vocs/${encodeURIComponent(id)}/analyze`, {
      method: 'POST'
    });
    await reload();
    notify(result.error ? '분석실패: ' + result.error : '분석과 추천을 완료했습니다.');
  } catch (e) {
    notify('분석실패: ' + e.message);
    document.getElementById('analyze').disabled = false;
  }
}
document.getElementById('search').addEventListener('input', e => {
  search = e.target.value;
  renderList();
});
document.querySelectorAll('.filter').forEach(b => b.addEventListener('click', () => {
  filter = b.dataset.filter;
  document.querySelectorAll('.filter').forEach(x => {
    x.classList.toggle('active', x === b);
    x.setAttribute('aria-pressed', String(x === b));
  });
  renderList();
}));
document.getElementById('reset').addEventListener('click', () => reload().catch(e => notify(e
  .message)));
(async () => {
  try {
    departments = await api('/api/departments');
    await reload();
  } catch (e) {
    document.getElementById('detail-area').textContent = 'Backend 연결 실패: ' + e.message;
  }
})();

setInterval(async () => {
  try {
    const s = await api('/api/stats');
    document.querySelector('.demo-badge').textContent = s.initialization_error ? '초기화 실패' :
      `과거 이력 ${s.history_searchable}/${s.history_total}건${s.history_preparation_done?` · 준비 완료(오류 ${s.history_failed}건)`:' · 준비 중'}`;
  } catch (e) {
    console.error(e);
  }
}, 10000);
