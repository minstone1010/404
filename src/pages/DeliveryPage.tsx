import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Chip, fmt, PageHeader } from '../components/ui';
import { deptDirectory, PERIOD_LABEL, reviewTotals } from '../data/mock';
import { DEPT_FULL_NAME, TAXONOMY, type TaxonomyValue } from '../data/taxonomy';
import { downloadVocWorkbook } from '../lib/excel';
import { useStore } from '../store';
import type { Complaint } from '../types';
import { MailCompose } from './MailCompose';
import { SheetViewer } from './SheetViewer';

type Dept = TaxonomyValue<'dept'>;

const fileNameFor = (dept: Dept | 'all') =>
  `KORAIL_VOC_${PERIOD_LABEL.replace(/(\d+)년 (\d+)월/, (_, y, m) => `${y}-${m.padStart(2, '0')}`)}_${dept === 'all' ? '전체' : DEPT_FULL_NAME[dept]}.xlsx`;

const now = () => {
  const d = new Date();
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

/** 부서별 전달 — 정리된 민원을 처리부서별 엑셀로 묶고, 열어보고, 부서마다 메일로 보내요 (v3 시안 다음 단계, 새 화면) */
export function DeliveryPage() {
  const { complaints, deliveries, dispatch, showToast } = useStore();
  const navigate = useNavigate();
  const [viewing, setViewing] = useState<Dept | 'all' | null>(null);
  const [composing, setComposing] = useState<Dept | null>(null);

  const handled = complaints.filter((c) => c.status !== 'review' && c.source !== 'auto').length;
  const reviewLeft = reviewTotals.needsReview - handled;

  const groups = useMemo(
    () =>
      TAXONOMY.dept.options.map((dept) => {
        const ready = complaints.filter((c) => c.classification.dept === dept && c.status !== 'review');
        const pending = complaints.filter((c) => c.classification.dept === dept && c.status === 'review').length;
        // 화면의 건수는 이번 달 전체 기준(가상), 표본 행은 엑셀 열어보기에 보여줘요
        const total = deptDirectory[dept].total - pending;
        const causes = new Map<string, number>();
        ready.forEach((c) => {
          const key = `${c.classification.cause1} · ${c.classification.cause2}`;
          causes.set(key, (causes.get(key) ?? 0) + 1);
        });
        const top = [...causes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k]) => k);
        return { dept, ready, pending, total, top };
      }),
    [complaints],
  );

  const sentCount = Object.keys(deliveries).length;
  const readyTotal = groups.reduce((s, g) => s + g.total, 0);
  const allRows: Complaint[] = groups.flatMap((g) => g.ready);

  const download = (dept: Dept | 'all') => {
    const rows = dept === 'all' ? allRows : groups.find((g) => g.dept === dept)!.ready;
    downloadVocWorkbook(rows, fileNameFor(dept))
      .then(() => showToast(`${fileNameFor(dept)} 을(를) 내려받았어요`))
      .catch(() => showToast('Excel을 만들지 못했어요. 다시 눌러 주세요'));
  };

  const viewGroup = viewing && viewing !== 'all' ? groups.find((g) => g.dept === viewing)! : null;
  const composeGroup = composing ? groups.find((g) => g.dept === composing)! : null;

  if (composeGroup) {
    const deptName = DEPT_FULL_NAME[composeGroup.dept];
    return (
      <main className="page">
        <PageHeader
          title={`${deptName}에 메일 보내기`}
          desc={`${PERIOD_LABEL} ${deptName}로 정리된 민원 ${fmt(composeGroup.total)}건을 엑셀로 첨부해 보내요.`}
          aside={
            <button className="link-strong" onClick={() => setComposing(null)}>
              ← 부서 목록
            </button>
          }
        />
        <MailCompose
          deptName={deptName}
          email={deptDirectory[composeGroup.dept].email}
          fileName={fileNameFor(composeGroup.dept)}
          rows={composeGroup.ready}
          total={composeGroup.total}
          onOpenSheet={() => setViewing(composeGroup.dept)}
          onCancel={() => setComposing(null)}
          onSent={(subject) => {
            dispatch({
              type: 'sendDept',
              dept: composeGroup.dept,
              delivery: { sentAt: now(), to: deptDirectory[composeGroup.dept].email, subject, count: composeGroup.total },
            });
            setComposing(null);
            showToast(`${deptName}에 메일을 보냈어요`);
          }}
        />
        {viewGroup && (
          <SheetViewer
            fileName={fileNameFor(viewGroup.dept)}
            rows={viewGroup.ready}
            total={viewGroup.total}
            onDownload={() => download(viewGroup.dept)}
            onClose={() => setViewing(null)}
          />
        )}
      </main>
    );
  }

  return (
    <main className="page">
      <PageHeader
        title="부서별로 정리한 민원"
        desc="분석과 검토를 마친 민원을 처리부서별 엑셀로 묶었어요. 열어서 확인하고, 부서마다 메일로 보내세요."
        aside={
          <Button variant="secondary" className="btn--sm" onClick={() => setViewing('all')}>
            전체 엑셀 열어보기
          </Button>
        }
      />

      <section className="kpis" aria-label="요약">
        <div className="kpi">
          <span className="kpi__label">정리된 민원 ({PERIOD_LABEL})</span>
          <span className="kpi__value">{fmt(readyTotal)}건</span>
        </div>
        <div className="kpi">
          <span className="kpi__label">메일 보낸 부서</span>
          <span className="kpi__value" style={{ color: sentCount === 8 ? 'var(--ok)' : 'var(--ink)' }}>
            {sentCount} / {groups.length}곳
          </span>
        </div>
        <button className="kpi kpi--link" onClick={() => navigate('/review')}>
          <span className="kpi__label">아직 검토 중 → 검토함</span>
          <span className="kpi__value" style={{ color: reviewLeft ? 'var(--warn)' : 'var(--muted)' }}>
            {fmt(reviewLeft)}건
          </span>
        </button>
      </section>

      <section className="card delivery" aria-label="처리부서별 정리 결과">
        <div className="delivery__head">
          <span className="c-d-name th">처리부서</span>
          <span className="c-d-count th">정리된 민원</span>
          <span className="c-d-top th">많이 들어온 원인</span>
          <span className="c-d-state th">상태</span>
          <span className="c-d-actions th" />
        </div>
        {groups.map((g) => {
          const sent = deliveries[g.dept];
          return (
            <div key={g.dept} className="delivery__row">
              <div className="c-d-name">
                <p className="delivery__dept">{DEPT_FULL_NAME[g.dept]}</p>
                <p className="note-muted">{deptDirectory[g.dept].email}</p>
              </div>
              <div className="c-d-count">
                <span className="delivery__count">{fmt(g.total)}건</span>
              </div>
              <div className="c-d-top">
                {g.top.length ? (
                  g.top.map((t) => (
                    <p key={t} className="delivery__cause">
                      {t}
                    </p>
                  ))
                ) : (
                  <span className="muted">—</span>
                )}
              </div>
              <div className="c-d-state">
                {sent ? (
                  <Chip tone="ok">보냄 · {sent.sentAt}</Chip>
                ) : g.pending ? (
                  <Chip tone="warn">검토 대기 {g.pending}건</Chip>
                ) : (
                  <Chip tone="info">보낼 준비 완료</Chip>
                )}
              </div>
              <div className="c-d-actions">
                <Button variant="secondary" className="btn--sm" onClick={() => setViewing(g.dept)}>
                  엑셀 열어보기
                </Button>
                <Button className="btn--sm" onClick={() => setComposing(g.dept)}>
                  {sent ? '다시 보내기' : '메일 보내기'}
                </Button>
              </div>
            </div>
          );
        })}
      </section>

      <p className="note-muted">
        검토 대기 중인 민원은 승인하면 해당 부서 엑셀에 들어가요. 처리부서 주소는 가상 주소예요 (코레일 주소록으로 바꿔야 해요).
      </p>

      {viewing && (
        <SheetViewer
          fileName={fileNameFor(viewing)}
          rows={viewGroup ? viewGroup.ready : allRows}
          total={viewGroup ? viewGroup.total : readyTotal}
          onDownload={() => download(viewing)}
          onClose={() => setViewing(null)}
        />
      )}
    </main>
  );
}
