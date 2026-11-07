import { useEffect } from 'react';
import { Button, Select } from '../components/ui';
import { reviewTotals } from '../data/mock';
import { DEPT_FULL_NAME, TAXONOMY, TAXONOMY_ORDER, TAXONOMY_VERSION } from '../data/taxonomy';
import { useStore } from '../store';
import type { TextPart } from '../types';

function Original({ parts }: { parts: TextPart[] }) {
  return (
    <>
      {parts.map((part, i) =>
        part.pii ? (
          <strong key={i} style={{ color: 'var(--ink)' }}>
            {part.text}
          </strong>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}

/** V3 · 4 민원 자세히 보기 — 같은 화면 서랍 (Figma 83:497) */
export function ComplaintDrawer({
  id,
  ids,
  onMove,
  onClose,
}: {
  id: string;
  ids: string[];
  onMove: (id: string) => void;
  onClose: () => void;
}) {
  const { complaints, dispatch, showToast } = useStore();
  const c = complaints.find((x) => x.id === id);
  const index = ids.indexOf(id);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!c) return null;
  const r = c.record;

  const approveAndNext = () => {
    dispatch({ type: 'approve', ids: [c.id] });
    const rest = ids.filter((x) => x !== c.id);
    if (rest.length === 0) {
      showToast('검토할 민원을 모두 승인했어요');
      onClose();
    } else {
      onMove(rest[Math.min(index, rest.length - 1)]);
    }
  };

  const piiFlagged = c.flags.includes('개인정보');

  return (
    <>
      <div className="dim dim--drawer" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`민원 ${r.receiptNo}`}>
        <div className="drawer__head">
          <div style={{ minWidth: 0 }}>
            <h2 className="drawer__title">{r.title}</h2>
            <p className="drawer__meta">
              {r.receiptNo} · {r.complaintKind} · {r.channel} · {Math.max(1, index + 1)} / {reviewTotals.needsReview}
            </p>
          </div>
          <button className="drawer__close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </div>

        <section className="drawer__section">
          <p className="drawer__label">질문 원문 (권한 있는 검토자에게만 표시)</p>
          <p className="text-box">
            <Original parts={c.original.question} />
          </p>
        </section>

        <section className="drawer__section">
          <p className="drawer__label">가린 질문</p>
          <p className={`text-box ${piiFlagged ? 'text-box--masked' : 'text-box--plain'}`}>{r.question}</p>
          {c.aiNote && <p className="note-warn">{c.aiNote}</p>}
        </section>

        {r.answer && (
          <section className="drawer__section">
            <p className="drawer__label">가린 답변 · 담당 부서·이름·연락처</p>
            <p className="text-box text-box--plain">{r.answer}</p>
            <div className="inline-pair">
              <span className="muted">처리자</span>
              <span>{r.handler}</span>
              <span className="muted">← 원문 {c.original.handler.slice(0, 1)}** (가림)</span>
            </div>
          </section>
        )}

        <section className="drawer__section">
          <p className="drawer__label">AI 요약 · 분류</p>
          <p className="drawer__summary">{c.summary}</p>
          <div className="class-grid">
            {TAXONOMY_ORDER.map((key) => {
              const flagged = c.flags.includes(key);
              const value = c.classification[key];
              return (
                <label key={key} className="class-field">
                  <span className={`class-field__label ${flagged ? 'is-flagged' : ''}`}>
                    {TAXONOMY[key].label}
                    {flagged ? ' · 확인 필요' : ''}
                  </span>
                  <Select
                    fill
                    label={TAXONOMY[key].label}
                    value={value || (key === 'note' ? '해당 없음' : '선택')}
                    options={(key === 'note' ? ['해당 없음', ...TAXONOMY[key].options] : TAXONOMY[key].options) as readonly string[]}
                    flagged={flagged}
                    onChange={(v) => dispatch({ type: 'setClass', id: c.id, key, value: v === '해당 없음' ? '' : v })}
                  />
                </label>
              );
            })}
          </div>
          <p className="note-muted">{c.reason}</p>
        </section>

        <section className="drawer__section">
          <p className="drawer__label">원본 정보</p>
          <dl className="meta-grid">
            <dt>접수일</dt>
            <dd>{r.receivedAt}</dd>
            <dt>처리기한</dt>
            <dd>{r.dueAt}</dd>
            <dt>고객요구유형</dt>
            <dd>{r.demandType || '공란'}</dd>
            <dt>완료유형</dt>
            <dd>{r.upperCompletion ? `${r.upperCompletion} › ${r.completion}` : '처리 중'}</dd>
            <dt>처리부서 경로</dt>
            <dd>
              {r.deptPath}
              {c.classification.dept && ` → ${DEPT_FULL_NAME[c.classification.dept]}`}
            </dd>
          </dl>
          <p className="taxonomy-note">분류 기준 {TAXONOMY_VERSION} · 확정되면 항목과 선택지가 바뀔 수 있어요</p>
        </section>

        <div className="spacer" />

        <div className="row-gap-10">
          <Button
            variant="secondary"
            fill
            aria-disabled={index <= 0}
            onClick={() => (index > 0 ? onMove(ids[index - 1]) : showToast('첫 번째 민원이에요'))}
          >
            ← 이전
          </Button>
          {c.status === 'review' ? (
            <Button fill onClick={approveAndNext}>
              승인 · 다음 민원
            </Button>
          ) : (
            <Button fill disabled={index >= ids.length - 1} onClick={() => onMove(ids[index + 1])}>
              다음 민원 →
            </Button>
          )}
        </div>
      </aside>
    </>
  );
}
