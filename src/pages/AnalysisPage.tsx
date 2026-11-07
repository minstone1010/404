import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Chip, fmt, PageHeader, ProgressBar } from '../components/ui';
import { analysisTotals, initialProgress } from '../data/mock';
import type { FileProgress } from '../types';

/** 진행률로 지금 하는 단계를 보여줘요 (개인정보 → 요약·분류 → 부서 추천 → 추이 집계) */
function stageLabel(p: FileProgress) {
  if (p.percent >= 100) return `완료 · 검토 필요 ${p.reviewCount ?? 0}건`;
  if (p.percent <= 0) return '대기 중';
  if (p.percent < 25) return '개인정보 가리는 중';
  if (p.percent < 60) return '요약·유형 분류 중';
  if (p.percent < 90) return '담당 부서 추천 중';
  return '추이 집계 중';
}

/** V3 · 2 자동 분석 중 (Figma 87:285) — 시연용으로 진행률을 흉내 내요 */
export function AnalysisPage() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(initialProgress);

  useEffect(() => {
    // 실제 서비스에서는 GET /batches/{id}/progress 를 2초마다 불러요.
    const t = window.setInterval(() => {
      setProgress((prev) => {
        // 진행 중인 파일은 계속, 대기 파일은 앞 파일이 절반쯤 지나면 시작
        const running = prev.filter((p) => p.percent > 0 && p.percent < 100).length;
        return prev.map((p) => {
          if (p.percent >= 100) return p;
          if (p.percent === 0 && running >= 2) return p;
          const next = Math.min(100, p.percent + 1.5);
          return next >= 100 ? { ...p, percent: 100, reviewCount: p.reviewCount ?? 20 } : { ...p, percent: next };
        });
      });
    }, 400);
    return () => window.clearInterval(t);
  }, []);

  const overall = progress.reduce((s, p) => s + p.percent, 0) / progress.length;
  // 첫 화면의 58% · 7,210건과 맞도록 초기 진행률 대비로 환산해요
  const initialOverall = initialProgress.reduce((s, p) => s + p.percent, 0) / initialProgress.length;
  const start = analysisTotals.done / analysisTotals.total;
  const ratio = start + ((overall - initialOverall) / (100 - initialOverall)) * (1 - start);
  const doneCount = Math.round(analysisTotals.total * Math.min(1, ratio));
  const percent = Math.round(Math.min(1, ratio) * 100);
  const finished = progress.filter((p) => p.percent >= 100).length;

  return (
    <main className="page">
      <PageHeader
        title={`파일 ${progress.length}개, 민원 ${fmt(analysisTotals.total)}건을 ${percent >= 100 ? '모두 분석했어요' : '분석하고 있어요'}`}
        desc={`약 ${analysisTotals.minutes}분 걸려요. 창을 닫아도 계속 진행되고, 먼저 끝난 파일부터 검토함에서 볼 수 있어요.`}
      />

      <section className="card progress-card" aria-label="전체 진행">
        <div className="progress-card__head">
          <span>전체 진행</span>
          <span style={{ color: 'var(--accent)' }}>
            {percent}% · {fmt(doneCount)} / {fmt(analysisTotals.total)}건
          </span>
        </div>
        <ProgressBar percent={percent} height={8} />
        <p className="progress-card__note">
          개인정보 가리기 → 요약·유형 분류 → 담당 부서 추천 → 추이 집계 순서로 파일마다 자동 진행돼요.
        </p>
      </section>

      <section className="card" aria-label="파일별 진행">
        {progress.map((p) => {
          const done = p.percent >= 100;
          return (
            <div key={p.fileId} className="file-progress">
              <div className="file-progress__main">
                <p className="file-progress__name">{p.name}</p>
                <ProgressBar percent={p.percent} height={6} color={done ? 'var(--ok)' : 'var(--accent)'} />
              </div>
              <p className="file-progress__stage">{stageLabel(p)}</p>
              {done ? (
                <Chip tone="ok">완료</Chip>
              ) : p.percent <= 0 ? (
                <Chip tone="warn">대기</Chip>
              ) : (
                <Chip tone="info">{Math.round(p.percent)}%</Chip>
              )}
            </div>
          );
        })}
      </section>

      <div className="footer-bar">
        <p className="info-line">메일은 자동으로 보내지 않아요. 검토함에서 승인한 뒤 담당자가 보내기를 눌러야 발송돼요.</p>
        <Button variant="secondary" onClick={() => navigate('/')}>
          취소
        </Button>
        <Button disabled={finished === 0} onClick={() => navigate('/review')}>
          끝난 파일 먼저 검토
        </Button>
      </div>
    </main>
  );
}
