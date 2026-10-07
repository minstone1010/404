const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
} [c]));
let result = null,
  selectedTopic = null,
  loadVersion = 0,
  busy = false;
const el = id => document.getElementById(id);
async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  });
  const body = await response.json();
  if (!response.ok) throw Error(body.detail || JSON.stringify(body));
  return body;
}

function message(text) {
  el('job-status').textContent = text;
}

function renderDetail() {
  const topic = result?.topics?.find(t => t.topic_id === selectedTopic);
  if (!topic) {
    el('topic-detail').innerHTML = '<div class="empty">Topic을 선택하세요.</div>';
    return;
  }
  el('topic-detail').innerHTML =
    `<div class="panel-title"><h2>Topic ${topic.topic_id} · ${escapeHTML(topic.topic_name)}</h2></div><div class="topic-detail-body"><div class="chips">${topic.representative_words.map(w=>`<span class="chip">${escapeHTML(w)}</span>`).join('')}</div><p>독립 사례 <strong>${topic.unique_case_count}건</strong> · 원본 ${topic.raw_document_count}건 · 비중 ${(topic.document_ratio*100).toFixed(1)}%</p><span class="section-label">대표 VOC (정규화 원문)</span>${topic.representative_documents.map(d=>`<p class="complaint"><b>${escapeHTML(d.id)}</b><br>${escapeHTML(d.text)}</p>`).join('')}<span class="section-label">원본 요지 분포 · 참고 통계</span><p>${Object.entries(topic.source_label_distribution).map(([k,v])=>`${escapeHTML(k||'라벨 없음')}: ${v}건`).join(' · ')}</p></div>`;
}

function render() {
  const metrics = result.metrics;
  if (!metrics) {
    el('topic-metrics').innerHTML = '';
    el('topics-list').innerHTML = '<div class="empty">현재 데이터·설정의 분석 결과가 없습니다. 배치를 실행하세요.</div>';
    el('topic-detail').innerHTML = '';
    el('generated').textContent = '미학습';
    el('topic-quality').textContent = '미학습';
    el('topic-trends').textContent = '배치 분석 후 확인 가능합니다.';
    return;
  }
  const cards = [
    ['Topic 수', metrics.topic_count, 'Outlier 제외'],
    ['독립 사례', metrics.unique_case_count, `원본 ${metrics.raw_document_count}건`],
    ['미군집 독립 사례', metrics.outlier_unique_count, `원본 ${metrics.outlier_raw_count}건`],
    ['Outlier 비율', `${(metrics.outlier_ratio*100).toFixed(1)}%`, '독립 사례 기준']
  ];
  el('topic-metrics').innerHTML = cards.map(([label, value, sub]) =>
    `<div class="metric"><div><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-sub">${sub}</div></div></div>`
    ).join('');
  el('generated').textContent = new Date(result.generated_at).toLocaleString('ko-KR');
  if (!result.topics.some(t => t.topic_id === selectedTopic)) selectedTopic = result.topics[0]
    ?.topic_id;
  el('topics-list').innerHTML = result.topics.map(t =>
    `<button class="topic-row ${t.topic_id===selectedTopic?'selected':''}" data-topic="${t.topic_id}"><strong>${t.topic_id===-1?'Outlier':`Topic ${t.topic_id}`} · ${escapeHTML(t.topic_name)}</strong><small>독립 ${t.unique_case_count}건 / 원본 ${t.raw_document_count}건 · ${(t.document_ratio*100).toFixed(1)}%</small></button>`
    ).join('');
  document.querySelectorAll('.topic-row').forEach(b => b.onclick = () => {
    selectedTopic = Number(b.dataset.topic);
    render();
  });
  renderDetail();
  const trend = result.trends;
  el('topic-trends').innerHTML = trend.enabled ?
    `<p class="subtopic">데이터 최신일 기준 ${result.config.trend_days}일 비교 · 날짜 포함 독립 사례 ${(trend.date_coverage*100).toFixed(1)}%</p><table class="topic-table"><thead><tr><th>Topic</th><th>전체</th><th>최근</th><th>이전</th><th>증감률</th><th>탐지</th></tr></thead><tbody>${trend.topics.map(t=>`<tr><td>${t.topic_id}</td><td>${t.total_unique_cases}</td><td>${t.recent_count}</td><td>${t.previous_count}</td><td>${t.growth_rate===null?'비교 기준 없음':(t.growth_rate*100).toFixed(1)+'%'}</td><td>${t.new_topic?'신규 등장':t.emerging?'최근 증가':'-'}</td></tr>`).join('')}</tbody></table>` :
    escapeHTML(trend.reason);
  el('topic-quality').innerHTML =
    `<p>Topic diversity: ${metrics.topic_diversity?.toFixed(3)??'계산 불가'} · Coherence NPMI: ${metrics.coherence_npmi?.toFixed(3)??'계산 불가'}</p><p class="subtopic">${escapeHTML(metrics.coherence_method)}. 지표는 정확도가 아니며 대표 문서의 사람 검토가 필요합니다.</p><p class="subtopic">Embedding 신규 계산 ${result.embedding.computed_unique}개 / 캐시 재사용 ${result.embedding.cached}개 · CPU 배치 ${result.elapsed_seconds.toFixed(1)}초</p>`;
}
async function load() {
  const ticket = ++loadVersion,
    mode = el('mode').value;
  try {
    const [data, validation] = await Promise.all([request(`/api/topics?mode=${mode}`), request(
      `/api/topics/warnings?mode=${mode}`).catch(e => ({
      error: e.message,
      candidates: []
    }))]);
    if (ticket !== loadVersion) return;
    result = data;
    render();
    const job = data.job;
    busy = ['starting', 'running'].includes(job.status);
    el('rebuild-topics').disabled = busy;
    el('rebuild-both').disabled = busy;
    message(job.status === 'failed' ? `배치 실패: ${job.error}` : busy ? `배치 실행 중 · ${job.mode}` :
      data.status === 'ready' ? '저장된 분석 결과를 표시합니다.' : '배치 분석 대기');
    el('topic-warnings').innerHTML = validation.error ? escapeHTML('재검토 통계 조회 실패: ' + validation
        .error) : validation.candidates.length ? validation.candidates.map(w =>
        `<div class="topic-warning"><b>${escapeHTML(w.id)} · 분류 재검토 필요</b><p>Qwen ${escapeHTML(w.qwen_topic_code)} / Topic ${w.topic_id} 과거 사례의 ${(w.dominant_ratio*100).toFixed(1)}%는 ${escapeHTML(w.dominant_label)} · 독립 근거 ${w.reference_unique_cases}건</p></div>`
        ).join('') :
      '<div class="empty">현재 저장된 Qwen 분석 중 임계값을 충족한 후보가 없습니다. 미분석 VOC는 검사하지 않습니다.</div>';
  } catch (e) {
    message('Topic 분석 조회 실패: ' + e.message);
  }
}
async function rebuild(mode) {
  if (busy) return;
  busy = true;
  el('rebuild-topics').disabled = true;
  el('rebuild-both').disabled = true;
  try {
    await request('/api/topics/rebuild', {
      method: 'POST',
      body: JSON.stringify({
        mode,
        force: el('force').checked
      })
    });
    message('배치 실행 요청을 접수했습니다.');
  } catch (e) {
    message('배치 실행 실패: ' + e.message);
  } finally {
    await load();
  }
}
el('mode').onchange = () => {
  selectedTopic = null;
  load();
};
el('refresh-topics').onclick = load;
el('rebuild-topics').onclick = () => rebuild(el('mode').value);
el('rebuild-both').onclick = () => rebuild('both');
load();
setInterval(() => {
  if (busy) load();
}, 5000);
