/**
 * 출력 엑셀 양식 — 코레일 민원 파일과 같은 A~O 15열
 * (첫 번째 이미지와 그 메모를 옮겼어요)
 */
export interface OutputColumn {
  key: keyof import('../types').VocRecord;
  header: string;
  /** 엑셀 열 너비 (문자 수 기준) */
  width: number;
  /** 개인정보를 가린 값으로 내보내는 열 */
  masked?: boolean;
  /** 코레일 메모 요약 — 엑셀 머리글 메모로도 넣어요 */
  memo?: string;
}

export const OUTPUT_COLUMNS: OutputColumn[] = [
  { key: 'receiptNo', header: '접수번호', width: 14, memo: '접수번호 양식 000-00000000' },
  { key: 'complaintKind', header: '민원유형', width: 11 },
  { key: 'channel', header: '유입경로', width: 11 },
  { key: 'registeredAt', header: '등록일', width: 19, memo: '날짜 형식 YYYY-MM-DD hh:mm:ss' },
  { key: 'receivedAt', header: '접수일', width: 19 },
  { key: 'dueAt', header: '처리기한', width: 19 },
  { key: 'completedAt', header: '완료일', width: 19 },
  {
    key: 'demandType',
    header: '고객요구유형',
    width: 12,
    memo: '물적/인적/제도적 요인과 이송. 공란 있음. 민원유형이 "촬영승인"이면 공란',
  },
  { key: 'title', header: '제목', width: 28 },
  { key: 'question', header: '질문', width: 50, masked: true, memo: '개인정보 필터링이 필요한 내용은 주로 질문에 있음' },
  { key: 'answer', header: '답변', width: 60, masked: true, memo: '민원담당자 부서·이름·연락처가 필수로 들어감 → 필터링 대상' },
  { key: 'upperCompletion', header: '상위완료유형', width: 12 },
  { key: 'completion', header: '완료유형', width: 12 },
  {
    key: 'deptPath',
    header: '처리부서',
    width: 40,
    memo: '필터링 대상 아님, 분석에 활용. 여러 부서면 주무부서에서 처리',
  },
  { key: 'handler', header: '처리자', width: 10, masked: true, memo: '처리 직원 이름 → 개인정보 필터링 대상' },
];

/** 업로드할 때 꼭 있어야 하는 열 (나머지는 없어도 분석은 돼요) */
export const REQUIRED_HEADERS = ['접수번호', '접수일', '질문'] as const;
