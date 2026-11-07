import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Chip, fmt, PageHeader, Select } from '../components/ui';
import { reviewTotals } from '../data/mock';
import { TAXONOMY, TAXONOMY_VERSION, type TaxonomyKey } from '../data/taxonomy';
import { flagSummary } from '../lib/flags';
import { useStore } from '../store';
import type { Complaint, ComplaintStatus } from '../types';
import { ComplaintDrawer } from './ComplaintDrawer';

const TABS: { status: ComplaintStatus; label: string }[] = [
  { status: 'review', label: '검토 필요' },
  { status: 'approved', label: '승인 완료 · 전달 전' },
  { status: 'sent', label: '발송 완료' },
];

/** V3 · 3 검토함 (Figma 83:112) — 열은 코레일 분류 기준 임시안에 맞췄어요 */
export function ReviewPage() {
  const { complaints: all, dispatch, showToast } = useStore();
  const navigate = useNavigate();
  // 검토함에는 AI가 자신 없어 사람이 봐야 하는 민원만 나와요 (자동 확인 민원은 바로 부서별 전달로)
  const complaints = useMemo(() => all.filter((c) => c.source !== 'auto'), [all]);
  const [tab, setTab] = useState<ComplaintStatus>('review');
  const [selected, setSelected] = useState<Set<string>>(() => new Set(complaints.map((c) => c.id)));
  const [openId, setOpenId] = useState<string | null>(null);

  const handled = complaints.filter((c) => c.status !== 'review').length;
  const counts = {
    review: reviewTotals.needsReview - handled,
    approved: complaints.filter((c) => c.status === 'approved').length,
    sent: complaints.filter((c) => c.status === 'sent').length,
  };

  const rows = useMemo(() => complaints.filter((c) => c.status === tab), [complaints, tab]);
  const selectedRows = rows.filter((r) => selected.has(r.id));
  const allChecked = rows.length > 0 && selectedRows.length === rows.length;

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const toggleAll = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      rows.forEach((r) => (allChecked ? next.delete(r.id) : next.add(r.id)));
      return next;
    });

  const approveSelected = () => {
    dispatch({ type: 'approve', ids: selectedRows.map((r) => r.id) });
    showToast(`${selectedRows.length}건을 승인했어요 · 처리부서별 엑셀에 들어갔어요`);
  };

  /** 표에 드롭다운으로 바로 보이는 분류 칸 (1차 원인 · 2차 원인 · 처리부서) */
  const classCell = (c: Complaint, key: TaxonomyKey) => (
    <div className={`tcell c-${key}`}>
      <Select
        label={`민원 ${c.record.receiptNo} ${TAXONOMY[key].label}`}
        value={c.classification[key] || '선택'}
        options={TAXONOMY[key].options as readonly string[]}
        flagged={c.flags.includes(key)}
        onChange={(value) => dispatch({ type: 'setClass', id: c.id, key, value })}
      />
    </div>
  );

  return (
    <main className="page page--flush-bottom">
      <PageHeader
        title={`검토할 민원 ${counts.review}건`}
        desc={`파일 5개 · ${fmt(reviewTotals.total)}건 중 AI가 자신 없는 칸만 노란색으로 표시했어요. 고칠 게 없으면 승인만 하면 됩니다.`}
        aside={<span className="demo-badge">분류 기준 {TAXONOMY_VERSION} · 가상 민원</span>}
      />

      <section className="kpis" aria-label="요약">
        <div className="kpi">
          <span className="kpi__label">전체 민원</span>
          <span className="kpi__value">{fmt(reviewTotals.total)}건</span>
        </div>
        <div className="kpi">
          <span className="kpi__label">AI 자동 확인 (검토 불필요)</span>
          <span className="kpi__value" style={{ color: 'var(--ok)' }}>
            {fmt(reviewTotals.autoConfirmed)}건
          </span>
        </div>
        <div className="kpi">
          <span className="kpi__label">검토 필요</span>
          <span className="kpi__value" style={{ color: 'var(--warn)' }}>
            {fmt(counts.review)}건
          </span>
        </div>
        <div className="kpi" style={{ color: counts.sent ? 'var(--ink)' : 'var(--muted)' }}>
          <span className="kpi__label">메일 발송 완료</span>
          <span className="kpi__value">{counts.sent}건</span>
        </div>
      </section>

      <section className="card review-card" aria-label="통합 검토 표">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.status}
              role="tab"
              aria-selected={tab === t.status}
              className={`tab ${tab === t.status ? 'is-active' : ''}`}
              onClick={() => setTab(t.status)}
            >
              {t.label} {counts[t.status]}
            </button>
          ))}
          <div className="spacer" />
          <span className="filter">파일: 전체 5개 ▾</span>
          <span className="filter">처리부서 ▾</span>
        </div>

        <div className="table" role="table">
          <div className="trow trow--head" role="row">
            <div className="tcell c-check">
              <button
                className={`checkbox checkbox--head ${allChecked ? 'is-checked' : ''}`}
                role="checkbox"
                aria-checked={allChecked}
                aria-label="모두 선택"
                onClick={toggleAll}
              >
                {allChecked ? '✓' : ''}
              </button>
            </div>
            <div className="tcell c-no th">접수번호</div>
            <div className="tcell c-summary th">제목 · AI 요약</div>
            <div className="tcell c-cause1 th">1차 원인</div>
            <div className="tcell c-cause2 th">2차 원인</div>
            <div className="tcell c-pii th">개인정보 가린 질문</div>
            <div className="tcell c-dept th">처리부서</div>
            <div className="tcell c-flag th">확인할 부분</div>
          </div>

          {rows.length === 0 && <p className="empty">이 탭에는 아직 민원이 없어요.</p>}

          {rows.map((c) => {
            const checked = selected.has(c.id);
            const piiFlag = c.flags.includes('개인정보');
            const summary = flagSummary(c.flags);
            return (
              <div
                key={c.id}
                className={`trow trow--body ${openId === c.id ? 'is-open' : ''}`}
                role="row"
                onClick={() => setOpenId(c.id)}
              >
                <div className="tcell c-check">
                  <button
                    className={`checkbox ${checked ? 'is-checked' : ''}`}
                    role="checkbox"
                    aria-checked={checked}
                    aria-label={`민원 ${c.record.receiptNo} 선택`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(c.id);
                    }}
                  />
                </div>
                <div className="tcell c-no">
                  <span className="receipt-no">{c.record.receiptNo}</span>
                </div>
                <div className="tcell c-summary">
                  <div style={{ minWidth: 0 }}>
                    <p className="summary-cell__title">{c.record.title}</p>
                    <p className="summary-cell__file">
                      {c.record.channel} · {c.summary}
                    </p>
                  </div>
                </div>
                {classCell(c, 'cause1')}
                {classCell(c, 'cause2')}
                <div className="tcell c-pii">
                  <span className={`pii-box pii-box--clip ${piiFlag ? 'is-flagged' : ''}`} title={c.record.question}>
                    {c.record.question}
                  </span>
                </div>
                {classCell(c, 'dept')}
                <div className="tcell c-flag">{summary ? <Chip>{summary}</Chip> : <Chip tone="ok">확인함</Chip>}</div>
              </div>
            );
          })}

          {tab === 'review' && rows.length > 0 && (
            <p className="table-foot">
              1 / {reviewTotals.pages} 페이지 · 50건씩 보기 · 행을 누르면 분류 8개를 모두 볼 수 있어요
            </p>
          )}
        </div>
      </section>

      <div className="action-bar">
        <p className="action-bar__count">{selectedRows.length}건 선택됨</p>
        <p className="action-bar__note">승인하면 처리부서별 엑셀에 들어가요. 메일은 부서별 전달에서 부서마다 보내요.</p>
        <Button variant="secondary" onClick={() => navigate('/delivery')}>
          부서별 전달 →
        </Button>
        {tab === 'review' ? (
          <Button disabled={selectedRows.length === 0} onClick={approveSelected}>
            선택한 {selectedRows.length}건 승인
          </Button>
        ) : (
          <Button disabled={tab === 'sent'} onClick={() => navigate('/delivery')}>
            {tab === 'sent' ? '전달 완료' : '부서별로 보내기'}
          </Button>
        )}
      </div>

      {openId && (
        <ComplaintDrawer id={openId} ids={rows.map((r) => r.id)} onMove={setOpenId} onClose={() => setOpenId(null)} />
      )}

    </main>
  );
}

