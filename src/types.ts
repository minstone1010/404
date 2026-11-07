import type { Classification, TaxonomyKey } from './data/taxonomy';

export type ChipTone = 'warn' | 'ok' | 'info' | 'bad';

/** 코레일 민원 파일 한 행 (출력 엑셀 A~O열). 질문·답변·처리자는 가린 값이에요. */
export interface VocRecord {
  receiptNo: string; // 접수번호 000-00000000
  complaintKind: string; // 민원유형 (불편개선, 국민신문고 …)
  channel: string; // 유입경로 (홈페이지, 고객센터, 방문(접점), 신문고 …)
  registeredAt: string; // YYYY-MM-DD hh:mm:ss
  receivedAt: string;
  dueAt: string;
  completedAt: string;
  demandType: string; // 고객요구유형 (물적요인 …, 공란 가능)
  title: string;
  question: string; // 가린 질문
  answer: string; // 가린 답변
  upperCompletion: string; // 상위완료유형
  completion: string; // 완료유형
  deptPath: string; // 처리부서 경로 (가리지 않음)
  handler: string; // 가린 처리자
}

/** 개인정보 표시를 위해 원문을 조각으로 나눈 것 */
export type TextPart = { text: string; pii?: boolean };

/** 검토가 필요한 칸 = AI가 자신 없는 칸 */
export type ReviewFlag = '개인정보' | TaxonomyKey;

export type ComplaintStatus = 'review' | 'approved' | 'sent';

export interface Complaint {
  /** 표에 보이는 짧은 번호 */
  id: string;
  fileName: string;
  record: VocRecord;
  /** 원문 (권한 있는 검토자만) */
  original: { question: TextPart[]; answer: TextPart[]; handler: string };
  summary: string; // AI 한 줄 요약
  classification: Classification;
  /** AI가 자신 없어 사람이 봐야 하는 칸 */
  flags: ReviewFlag[];
  aiNote?: string;
  reason: string;
  status: ComplaintStatus;
  /** 'auto' = AI가 자신 있게 분류해 검토 없이 바로 정리된 민원 */
  source?: 'auto';
}

/** 부서별 메일 발송 기록 */
export interface Delivery {
  sentAt: string;
  to: string;
  subject: string;
  count: number;
}

export interface UploadedFile {
  id: string;
  name: string;
  count: number | null;
  error?: string;
  /** 오류일 때 고를 수 있는 머리글 목록 */
  headers?: string[];
  missing?: string[];
}

export interface FileProgress {
  fileId: string;
  name: string;
  percent: number;
  reviewCount?: number;
}

export interface CauseTrend {
  cause: string;
  lastYear: number;
  thisYear: number;
}

export interface RepeatIssue {
  title: string;
  detail: string;
}
