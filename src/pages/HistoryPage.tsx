import { fmt, PageHeader } from '../components/ui';
import { DEPT_FULL_NAME } from '../data/taxonomy';
import { useStore } from '../store';

/**
 * 처리 이력 — v3 Figma에는 이 화면 시안이 없어요.
 * 같은 스타일로 최소한만 만들어 두었고, 시안이 나오면 교체하면 됩니다.
 */
export function HistoryPage() {
  const { complaints, deliveries, senderName } = useStore();
  const approved = complaints.filter((c) => c.source !== 'auto' && c.status !== 'review').length;

  const rows = [
    { at: '10/24 10:20', who: '시스템', action: '개인정보 가리기', target: '12,443건', state: '완료' },
    { at: '10/24 10:24', who: '시스템', action: '분류 (임시안 v0)', target: '12,443건', state: '완료' },
    ...(approved ? [{ at: '오늘', who: senderName, action: '검토 승인', target: `${approved}건`, state: '부서별 엑셀에 반영' }] : []),
    ...Object.entries(deliveries).map(([dept, d]) => ({
      at: d!.sentAt,
      who: senderName,
      action: `메일 발송 · ${DEPT_FULL_NAME[dept as keyof typeof DEPT_FULL_NAME]}`,
      target: `${fmt(d!.count)}건 · ${d!.to}`,
      state: '보냄',
    })),
  ].reverse();

  return (
    <main className="page">
      <PageHeader
        title="처리 이력"
        desc="누가 어떤 파일을 처리했고, 어느 부서에 무엇을 전달했는지 남겨요."
        aside={<span className="demo-badge">v3 시안 없음 · 임시 화면</span>}
      />
      <section className="card">
        <table className="history-table">
          <thead>
            <tr>
              <th>처리 일시</th>
              <th>처리자</th>
              <th>작업</th>
              <th>대상</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.at}</td>
                <td>{r.who}</td>
                <td>{r.action}</td>
                <td>{r.target}</td>
                <td>{r.state}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
