import { useEffect } from 'react';
import { Button, fmt } from '../components/ui';
import { OUTPUT_COLUMNS } from '../data/outputColumns';
import { DEPT_FULL_NAME, TAXONOMY, TAXONOMY_ORDER } from '../data/taxonomy';
import type { Complaint } from '../types';

/** A, B, … Z, AA … */
const colLetter = (i: number) => {
  let s = '';
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
};

/**
 * 정리된 엑셀을 화면에서 바로 열어보는 창.
 * 내려받는 파일과 같은 열(A~O 코레일 양식 + P~W AI 분류)을 그대로 보여줘요.
 */
export function SheetViewer({
  fileName,
  rows,
  total,
  onDownload,
  onClose,
}: {
  fileName: string;
  rows: Complaint[];
  /** 실제 파일에 들어갈 전체 건수 */
  total: number;
  onDownload: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const columns = [
    ...OUTPUT_COLUMNS.map((c) => ({ id: c.key as string, header: c.header, masked: !!c.masked, ai: false, width: Math.min(c.width, 36) })),
    ...TAXONOMY_ORDER.map((k) => ({ id: k as string, header: TAXONOMY[k].label, masked: false, ai: true, width: 12 })),
  ];

  const cell = (c: Complaint, id: string) => {
    if (id in c.record) return c.record[id as keyof typeof c.record];
    const k = id as (typeof TAXONOMY_ORDER)[number];
    const v = c.classification[k];
    return k === 'dept' && v ? DEPT_FULL_NAME[v as keyof typeof DEPT_FULL_NAME] : v;
  };

  return (
    <div className="dim dim--modal" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" onClick={(e) => e.stopPropagation()}>
        <div className="sheet__head">
          <span className="sheet__icon" aria-hidden>
            ▤
          </span>
          <div className="sheet__title-wrap">
            <h2 id="sheet-title" className="sheet__title">
              {fileName}
            </h2>
            <p className="sheet__meta">
              민원 목록 시트 · {fmt(total)}행 · A~O 코레일 양식 + P~W AI 분류 · 질문·답변·처리자는 가린 값
            </p>
          </div>
          <Button variant="secondary" className="btn--sm" onClick={onDownload}>
            엑셀 내려받기
          </Button>
          <button className="drawer__close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="sheet__grid-wrap">
          <table className="sheet__grid">
            <thead>
              <tr className="sheet__letters">
                <th className="sheet__rownum" />
                {columns.map((col, i) => (
                  <th key={col.id}>{colLetter(i)}</th>
                ))}
              </tr>
              <tr className="sheet__headers">
                <th className="sheet__rownum">1</th>
                {columns.map((col) => (
                  <th
                    key={col.id}
                    className={col.ai ? 'is-ai' : ''}
                    style={{ minWidth: col.width * 8, maxWidth: col.width * 10 }}
                  >
                    {col.ai ? `[AI] ${col.header}` : col.header}
                    {col.masked && <span className="sheet__mask-tag">가림</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((c, r) => (
                <tr key={c.id}>
                  <th className="sheet__rownum">{r + 2}</th>
                  {columns.map((col) => {
                    const value = cell(c, col.id);
                    const flagged = col.ai && c.flags.includes(col.id as never);
                    return (
                      <td
                        key={col.id}
                        className={`${flagged ? 'is-flagged' : ''} ${col.masked ? 'is-masked' : ''}`}
                        style={{ maxWidth: col.width * 10 }}
                        title={value}
                      >
                        {value}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="sheet__foot">
          <span className="sheet__tab is-active">민원 목록</span>
          <span className="sheet__tab">분류 기준</span>
          <span className="spacer" />
          <span className="note-muted">
            시연용: 전체 {fmt(total)}건 중 예시 {rows.length}건을 보여줘요. 노란 칸은 검토에서 AI가 자신 없던 칸이에요.
          </span>
        </div>
      </div>
    </div>
  );
}
