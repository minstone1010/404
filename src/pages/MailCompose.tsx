import { useState } from 'react';
import { Button, fmt } from '../components/ui';
import { PERIOD_LABEL } from '../data/mock';
import { useStore, defaultMailBody } from '../store';
import type { Complaint } from '../types';

/** 메일에 원문 개인정보가 섞이지 않았는지 한 번 더 확인 (전화·이메일·계좌 원형) */
const RAW_PII = /(01[016789]-?\d{3,4}-?\d{4})|([\w.+-]+@[\w-]+\.[\w.]+)|(\d{3}-\d{2,6}-\d{4,6})/;
const hasRawPii = (text: string) => text.split(/\s/).some((t) => RAW_PII.test(t) && !t.includes('*'));

/**
 * 메일 쓰기 화면 — 부서별 전달에서 "메일 보내기"를 누르면 열려요.
 * 인사말은 담당자가 고칠 수 있고, 고친 문구는 다음 부서 메일에도 그대로 쓰여요.
 * 실제 발송은 서버가 해요 (POST /mail-drafts/send). 지금은 시연용으로 보낸 것처럼 처리합니다.
 */
export function MailCompose({
  deptName,
  email,
  fileName,
  rows,
  total,
  onOpenSheet,
  onCancel,
  onSent,
}: {
  deptName: string;
  email: string;
  fileName: string;
  rows: Complaint[];
  total: number;
  onOpenSheet: () => void;
  onCancel: () => void;
  onSent: (subject: string) => void;
}) {
  const { senderName, mailBody, dispatch } = useStore();
  const [subject, setSubject] = useState(`[코레일 VOC] ${PERIOD_LABEL} ${deptName} 민원 정리 (${fmt(total)}건)`);
  const [sending, setSending] = useState(false);
  const body = mailBody ?? defaultMailBody(senderName);
  const unsafe = rows.filter((c) => hasRawPii(c.record.question) || hasRawPii(c.record.answer)).length;
  const canSend = subject.trim().length > 0 && body.trim().length > 0 && unsafe === 0 && !sending;

  const send = () => {
    if (!canSend) return;
    setSending(true);
    window.setTimeout(() => onSent(subject.trim()), 700);
  };

  return (
    <section className="card compose" aria-label={`${deptName}에 메일 보내기`}>
      <div className="compose__row">
        <label className="compose__label" htmlFor="mail-from">
          보내는 사람
        </label>
        <div className="compose__field compose__inline">
          <span className="muted">코레일 민원 VOC 담당자</span>
          <input
            id="mail-from"
            className="input input--name"
            value={senderName}
            onChange={(e) => dispatch({ type: 'setSender', name: e.target.value })}
            aria-label="보내는 사람 이름"
          />
        </div>
      </div>

      <div className="compose__row">
        <span className="compose__label">받는 사람</span>
        <div className="compose__field">
          <span className="recipient">
            {deptName} VOC 담당 <span className="muted">&lt;{email}&gt;</span>
          </span>
        </div>
      </div>

      <div className="compose__row">
        <label className="compose__label" htmlFor="mail-subject">
          제목
        </label>
        <input id="mail-subject" className="input compose__field" value={subject} onChange={(e) => setSubject(e.target.value)} />
      </div>

      <div className="compose__row compose__row--top">
        <label className="compose__label" htmlFor="mail-body">
          본문
        </label>
        <div className="compose__field">
          <textarea
            id="mail-body"
            className="input textarea"
            rows={7}
            value={body}
            onChange={(e) => dispatch({ type: 'setMailBody', body: e.target.value })}
          />
          <div className="compose__hint">
            <span className="note-muted">고친 인사말은 다른 부서 메일에도 그대로 쓰여요.</span>
            {mailBody !== null && (
              <button className="link-strong" style={{ fontSize: 12 }} onClick={() => dispatch({ type: 'setMailBody', body: null })}>
                기본 문구로 되돌리기
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="compose__row">
        <span className="compose__label">첨부</span>
        <div className="compose__field">
          <button className="attachment" onClick={onOpenSheet}>
            <span className="file-row__icon" aria-hidden>
              ▤
            </span>
            <span className="attachment__name">{fileName}</span>
            <span className="muted">{fmt(total)}건</span>
            <span className="link-strong">열어보기</span>
          </button>
        </div>
      </div>

      <div className={`check-ok ${unsafe ? 'is-bad' : ''}`}>
        <span className="check-ok__mark" aria-hidden>
          {unsafe ? '!' : '✓'}
        </span>
        <span>
          {unsafe
            ? `첨부 엑셀에 개인정보 원문이 ${unsafe}건 남아 있어요 · 검토함에서 가림을 확인해 주세요`
            : '첨부 엑셀의 질문·답변·처리자 가림 확인 완료 · 받는 사람은 등록된 부서 주소예요'}
        </span>
      </div>

      <div className="compose__actions">
        <Button variant="secondary" onClick={onCancel} disabled={sending}>
          취소
        </Button>
        <Button onClick={send} disabled={!canSend}>
          {sending ? '보내는 중…' : '보내기'}
        </Button>
      </div>
    </section>
  );
}
