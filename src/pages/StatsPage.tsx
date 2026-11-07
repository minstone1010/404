import { Button, Chip, fmt, PageHeader } from '../components/ui';
import { causeTrends, repeatIssues, statsSummary } from '../data/mock';
import { TAXONOMY_VERSION } from '../data/taxonomy';
import { downloadVocWorkbook } from '../lib/excel';
import { useStore } from '../store';
import type { ChipTone } from '../types';

/** Figma 막대: 가장 큰 값(3410건)이 409px */
const MAX_BAR = 409;

function changeChip(lastYear: number, thisYear: number): { label: string; tone: ChipTone } {
  const pct = ((thisYear - lastYear) / lastYear) * 100;
  const rounded = Math.abs(pct) >= 10 ? pct.toFixed(1) : pct.toFixed(Math.abs(pct % 1) < 0.05 ? 0 : 1);
  const label = `${pct > 0 ? '+' : ''}${rounded.replace(/\.0$/, '')}%`;
  // 크게 늘면 빨강, 조금 늘면 주황, 줄면 초록 (Figma 기준: 20% 이상이면 bad)
  const tone: ChipTone = pct >= 20 ? 'bad' : pct > 0 ? 'warn' : 'ok';
  return { label, tone };
}

/** V3 · 6 통계·보고서 (Figma 85:364) */
export function StatsPage() {
  const { complaints, showToast } = useStore();
  const saveExcel = () =>
    downloadVocWorkbook(complaints, 'KORAIL_VOC_result_2026-09.xlsx')
      .then(() => showToast('코레일 양식(A~O열) + AI 분류 열로 저장했어요'))
      .catch(() => showToast('Excel을 만들지 못했어요. 다시 눌러 주세요'));
  const max = Math.max(...causeTrends.flatMap((t) => [t.lastYear, t.thisYear]));
  const top = [...causeTrends].sort((a, b) => b.thisYear / b.lastYear - a.thisYear / a.lastYear)[0];
  const topChange = changeChip(top.lastYear, top.thisYear);

  return (
    <main className="page">
      <PageHeader
        title="작년보다 늘어난 민원"
        desc="새 파일이 분석될 때마다 자동으로 갱신돼요. 이번 달과 작년 같은 달을 1차 원인별로 비교했어요."
        aside={
          <button className="period" onClick={() => showToast('비교 기간 선택은 시안에서 고정돼 있어요')}>
            {`${statsSummary.current}  vs  ${statsSummary.compare}  ▾`}
          </button>
        }
      />

      <section className="kpis" aria-label="요약">
        <div className="stat-card">
          <span className="kpi__label">
            {statsSummary.monthLabel} 민원 (파일 {statsSummary.fileCount}개 합계)
          </span>
          <span className="kpi__value">{fmt(statsSummary.total)}건</span>
          <Chip tone="warn">
            작년 {statsSummary.monthLabel}보다 {statsSummary.yoyPercent}% 증가
          </Chip>
        </div>
        <div className="stat-card">
          <span className="kpi__label">가장 많이 늘어난 1차 원인</span>
          <span className="kpi__value">{top.cause}</span>
          <Chip tone="bad">
            {fmt(top.lastYear)} → {fmt(top.thisYear)}건 · {topChange.label}
          </Chip>
        </div>
        <div className="stat-card">
          <span className="kpi__label">반복 민원</span>
          <span className="kpi__value">{statsSummary.repeatCount}건</span>
          <Chip tone="info">{statsSummary.repeatNote}</Chip>
        </div>
      </section>

      <div className="stats-body">
        <section className="card trend-card" aria-label="유형별 비교">
          <div className="trend-card__head">
            <p className="card-title">
              1차 원인별 민원 건수 <span className="taxonomy-note">· 분류 기준 {TAXONOMY_VERSION}</span>
            </p>
            <div className="legend">
              <span className="legend__swatch" style={{ background: 'var(--line)' }} />
              <span>2025</span>
              <span className="legend__swatch" style={{ background: 'var(--accent)' }} />
              <span>2026</span>
            </div>
          </div>
          {causeTrends.map((t) => {
            const chip = changeChip(t.lastYear, t.thisYear);
            return (
              <div key={t.cause} className="trend-row">
                <p className="trend-row__label">{t.cause}</p>
                <div className="trend-row__bars">
                  <div className="trend-bar">
                    <span
                      className="trend-bar__rect"
                      style={{ width: Math.round((t.lastYear / max) * MAX_BAR), background: 'var(--line)' }}
                    />
                    <span>{t.lastYear}</span>
                  </div>
                  <div className="trend-bar">
                    <span
                      className="trend-bar__rect"
                      style={{ width: Math.round((t.thisYear / max) * MAX_BAR), background: 'var(--accent)' }}
                    />
                    <span>{t.thisYear}</span>
                  </div>
                </div>
                <div className="spacer" />
                <Chip tone={chip.tone}>{chip.label}</Chip>
              </div>
            );
          })}
        </section>

        <section className="card repeat-card" aria-label="반복 민원">
          <p className="card-title repeat-card__title">반복해서 들어오는 민원</p>
          {repeatIssues.map((r) => (
            <div key={r.title} className="repeat-item">
              <p className="repeat-item__title">{r.title}</p>
              <p className="repeat-item__detail">{r.detail}</p>
            </div>
          ))}
        </section>
      </div>

      <div className="footer-bar">
        <div className="spacer" />
        <Button variant="secondary" onClick={saveExcel}>
          Excel로 저장
        </Button>
        <Button onClick={() => showToast('보고서 PDF를 만들었어요 (시연)')}>보고서 PDF 만들기</Button>
      </div>
    </main>
  );
}
