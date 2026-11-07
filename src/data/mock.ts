/**
 * 시연용 가상 데이터 — 사람·번호·문장은 모두 지어낸 예시예요.
 * 코레일 민원 파일 양식(A~O열)과 분류 기준 임시안(taxonomy.ts)에 맞췄습니다.
 * 백엔드가 준비되면 이 모듈 대신 API 응답을 쓰면 됩니다.
 */
import type { CauseTrend, Complaint, FileProgress, RepeatIssue, UploadedFile } from '../types';

export const DUPLICATE_COUNT = 37;

export const initialFiles: UploadedFile[] = [
  { id: 'f1', name: '서울본부_9월.xlsx', count: 3120 },
  { id: 'f2', name: '수도권광역_9월.xlsx', count: 2870 },
  { id: 'f3', name: '대전충남_9월.xlsx', count: 2140 },
  { id: 'f4', name: '부산경남_9월.xlsx', count: 2460 },
  { id: 'f5', name: '국민신문고_9월.xlsx', count: 1890 },
  {
    id: 'f6',
    name: '강원본부_9월.xlsx',
    count: null,
    error: '"질문" 열을 찾지 못했어요. 어느 열인지 골라주면 같이 분석해요.',
    missing: ['질문'],
    headers: ['접수번호', '민원유형', '유입경로', '등록일', '접수일', '민원내용', '답변', '처리부서'],
  },
];

export const initialProgress: FileProgress[] = [
  { fileId: 'f1', name: '서울본부_9월.xlsx', percent: 100, reviewCount: 31 },
  { fileId: 'f2', name: '수도권광역_9월.xlsx', percent: 100, reviewCount: 27 },
  { fileId: 'f3', name: '대전충남_9월.xlsx', percent: 71 },
  { fileId: 'f4', name: '부산경남_9월.xlsx', percent: 34 },
  { fileId: 'f5', name: '국민신문고_9월.xlsx', percent: 0 },
];

export const analysisTotals = { total: 12443, done: 7210, minutes: 8 };
export const reviewTotals = { total: 12443, autoConfirmed: 12325, needsReview: 118, pages: 3 };

const ANSWER_HEAD = '안녕하십니까? 한국철도공사 입니다.';
const sinmungoHead = (no: string) =>
  `★귀하께서 국민신문고를 통해 신청하신 민원(신청번호:${no})에 대한 검토결과를 다음과 같이 알려드립니다.★`;

export const complaints: Complaint[] = [
  {
    id: '001',
    fileName: '서울본부_9월.xlsx',
    record: {
      receiptNo: '101-26091401',
      complaintKind: '불편개선',
      channel: '홈페이지',
      registeredAt: '2026-09-14 09:12:33',
      receivedAt: '2026-09-14 09:15:02',
      dueAt: '2026-09-21 18:00:00',
      completedAt: '2026-09-16 14:20:11',
      demandType: '제도적요인',
      title: 'KTX 지연 환불 문의',
      question: '어제 KTX 101편이 40분 지연돼서 환불 요청합니다. 예약자 김**, 연락처 010-****-5678로 연락 주세요.',
      answer: `${ANSWER_HEAD} 귀하의 민원은 열차 지연에 따른 환불 요청으로 이해됩니다. 지연 배상은 코레일톡 승차권 반환 메뉴에서 신청하실 수 있습니다. 담당: [담당부서] [담당자] [연락처]`,
      upperCompletion: '참고안내',
      completion: '제도설명',
      deptPath: 'KORAIL>여객사업본부>영업처',
      handler: '[처리자]',
    },
    original: {
      question: [
        { text: '어제 KTX 101편이 40분 지연돼서 환불 요청합니다. 예약자 ' },
        { text: '김민수', pii: true },
        { text: ', 연락처 ' },
        { text: '010-1234-5678', pii: true },
        { text: '로 연락 주세요.' },
      ],
      answer: [
        { text: `${ANSWER_HEAD} 귀하의 민원은 열차 지연에 따른 환불 요청으로 이해됩니다. 지연 배상은 코레일톡 승차권 반환 메뉴에서 신청하실 수 있습니다. 담당: ` },
        { text: '영업처 여객영업부', pii: true },
        { text: ' ' },
        { text: '이수진', pii: true },
        { text: ' ' },
        { text: '042-615-0000', pii: true },
      ],
      handler: '이수진',
    },
    summary: '열차 지연으로 환불 요청',
    classification: {
      journey: '수송',
      category: '제도적',
      cause1: '열차 지연',
      cause2: '배상 · 보상',
      place1: '기차',
      place2: 'KTX',
      note: '',
      dept: '영업',
    },
    flags: ['개인정보'],
    aiNote: 'AI 확인 요청: "101편"이 개인정보인지 판단이 어려웠어요. 필요하면 드래그해서 가리기를 추가하세요.',
    reason: '분류 근거: "지연", "환불" 키워드 · 처리부서 경로 "…>영업처" · 비슷한 민원 312건이 같은 분류',
    status: 'review',
  },
  {
    id: '003',
    fileName: '대전충남_9월.xlsx',
    record: {
      receiptNo: '205-26091503',
      complaintKind: '불편개선',
      channel: '방문(접점)',
      registeredAt: '2026-09-15 11:02:10',
      receivedAt: '2026-09-15 11:05:44',
      dueAt: '2026-09-22 18:00:00',
      completedAt: '2026-09-18 10:31:00',
      demandType: '물적요인',
      title: '대전역 안내 전광판 고장',
      question: '대전역 2층 안내 전광판이 이틀째 꺼져 있어요. 열차 시간을 확인하기 어렵습니다.',
      answer: `${ANSWER_HEAD} 말씀하신 전광판은 부품 교체 후 정상 작동 중입니다. 담당: [담당부서] [담당자] [연락처]`,
      upperCompletion: '시정조치',
      completion: '역시설개선',
      deptPath: 'KORAIL>대전충남본부>전기처, KORAIL>대전충남본부>대전역',
      handler: '[처리자]',
    },
    original: {
      question: [{ text: '대전역 2층 안내 전광판이 이틀째 꺼져 있어요. 열차 시간을 확인하기 어렵습니다.' }],
      answer: [
        { text: `${ANSWER_HEAD} 말씀하신 전광판은 부품 교체 후 정상 작동 중입니다. 담당: ` },
        { text: '전기처 전기설비부', pii: true },
        { text: ' ' },
        { text: '박정호', pii: true },
        { text: ' ' },
        { text: '042-615-1111', pii: true },
      ],
      handler: '박정호',
    },
    summary: '역사 안내 전광판 고장',
    classification: {
      journey: '역 방문',
      category: '물적',
      cause1: '시설물',
      cause2: '고장',
      place1: '역',
      place2: '여객',
      note: '기타 설비',
      dept: '전기',
    },
    flags: ['dept'],
    reason: '분류 근거: "전광판", "고장" 키워드 · 처리부서 경로에 부서가 2곳(전기처, 대전역)이라 주무부서 확인 필요',
    status: 'review',
  },
  {
    id: '004',
    fileName: '국민신문고_9월.xlsx',
    record: {
      receiptNo: '310-26091504',
      complaintKind: '국민신문고',
      channel: '신문고',
      registeredAt: '2026-09-15 15:40:00',
      receivedAt: '2026-09-15 16:02:12',
      dueAt: '2026-09-29 18:00:00',
      completedAt: '2026-09-19 09:10:45',
      demandType: '제도적요인',
      title: '환불 계좌 변경 요청',
      question: '환불은 이 계좌로 받고 싶어요. ***-*** 입니다.',
      answer: `${ANSWER_HEAD} ${sinmungoHead('1AA-2609-0000000')} 귀하의 민원은 환불 계좌 변경 요청으로 이해됩니다. 계좌 변경은 고객센터에서 본인 확인 후 가능합니다. 담당: [담당부서] [담당자] [연락처]`,
      upperCompletion: '참고안내',
      completion: '사실설명',
      deptPath: 'KORAIL>여객사업본부>영업처',
      handler: '[처리자]',
    },
    original: {
      question: [
        { text: '환불은 이 계좌로 받고 싶어요. ' },
        { text: '110-123-456789', pii: true },
        { text: ' 입니다.' },
      ],
      answer: [
        {
          text: `${ANSWER_HEAD} ${sinmungoHead('1AA-2609-0000000')} 귀하의 민원은 환불 계좌 변경 요청으로 이해됩니다. 계좌 변경은 고객센터에서 본인 확인 후 가능합니다. 담당: `,
        },
        { text: '영업처 고객지원부', pii: true },
        { text: ' ' },
        { text: '최유나', pii: true },
        { text: ' ' },
        { text: '02-3149-0000', pii: true },
      ],
      handler: '최유나',
    },
    summary: '환불 계좌 변경 요청',
    classification: {
      journey: '이용 후 / 연계교통',
      category: '제도적',
      cause1: '승차권',
      cause2: '결제 · 환불',
      place1: '기타',
      place2: '온라인',
      note: '',
      dept: '영업',
    },
    flags: ['개인정보'],
    reason: '분류 근거: "환불", "계좌" 키워드 · 처리부서 경로 "…>영업처"',
    status: 'review',
  },
  {
    id: '007',
    fileName: '수도권광역_9월.xlsx',
    record: {
      receiptNo: '118-26091607',
      complaintKind: '불편개선',
      channel: '고객센터',
      registeredAt: '2026-09-16 08:20:41',
      receivedAt: '2026-09-16 08:31:05',
      dueAt: '2026-09-23 18:00:00',
      completedAt: '',
      demandType: '물적요인',
      title: '코레일톡 결제 오류',
      question: '앱에서 결제하면 계속 오류가 나요. 박**, 영**@example.com으로 답 주세요.',
      answer: '',
      upperCompletion: '',
      completion: '',
      deptPath: 'KORAIL>디지털본부>고객서비스처',
      handler: '[처리자]',
    },
    original: {
      question: [
        { text: '앱에서 결제하면 계속 오류가 나요. ' },
        { text: '박영희', pii: true },
        { text: ', ' },
        { text: 'younghee@example.com', pii: true },
        { text: '으로 답 주세요.' },
      ],
      answer: [],
      handler: '정다은',
    },
    summary: '코레일톡 결제 단계 반복 오류',
    classification: {
      journey: '예매 및 발권',
      category: '물적',
      cause1: '시스템',
      cause2: '코레일톡',
      place1: '기타',
      place2: '온라인',
      note: '',
      dept: '영업',
    },
    flags: ['cause2', 'dept'],
    reason: '분류 근거: "앱", "결제" 키워드 · 2차 원인이 코레일톡과 결제 · 환불 사이에서 갈림 · 처리부서 경로가 8개 부서에 없음',
    status: 'review',
  },
  {
    id: '012',
    fileName: '국민신문고_9월.xlsx',
    record: {
      receiptNo: '310-26091712',
      complaintKind: '국민신문고',
      channel: '신문고',
      registeredAt: '2026-09-17 21:05:17',
      receivedAt: '2026-09-18 09:00:00',
      dueAt: '2026-10-02 18:00:00',
      completedAt: '2026-09-22 16:44:30',
      demandType: '',
      title: '명절 예매 대기 오류',
      question: '추석 예매 대기 순번이 줄다가 갑자기 처음으로 돌아갔어요.',
      answer: `${ANSWER_HEAD} ${sinmungoHead('1AA-2609-0000001')} 불편을 드려 죄송합니다. 대기열 서버 오류를 확인하여 조치했습니다. 담당: [담당부서] [담당자] [연락처]`,
      upperCompletion: '반영개선',
      completion: '기타',
      deptPath: 'KORAIL>여객사업본부>영업처',
      handler: '[처리자]',
    },
    original: {
      question: [{ text: '추석 예매 대기 순번이 줄다가 갑자기 처음으로 돌아갔어요.' }],
      answer: [
        {
          text: `${ANSWER_HEAD} ${sinmungoHead('1AA-2609-0000001')} 불편을 드려 죄송합니다. 대기열 서버 오류를 확인하여 조치했습니다. 담당: `,
        },
        { text: '영업처 예약발매부', pii: true },
        { text: ' ' },
        { text: '한지민', pii: true },
        { text: ' ' },
        { text: '02-3149-1111', pii: true },
      ],
      handler: '한지민',
    },
    summary: '명절 승차권 예매 대기열 오류',
    classification: {
      journey: '예매 및 발권',
      category: '물적',
      cause1: '시스템',
      cause2: '오류',
      place1: '기타',
      place2: '온라인',
      note: '',
      dept: '영업',
    },
    flags: ['category'],
    reason: '분류 근거: "예매", "대기" 키워드 · 원본 고객요구유형이 공란이라 구분을 AI가 추정',
    status: 'review',
  },
  {
    id: '015',
    fileName: '부산경남_9월.xlsx',
    record: {
      receiptNo: '402-26091815',
      complaintKind: '불편개선',
      channel: '홈페이지',
      registeredAt: '2026-09-18 13:30:00',
      receivedAt: '2026-09-18 13:41:27',
      dueAt: '2026-09-25 18:00:00',
      completedAt: '2026-09-20 11:05:00',
      demandType: '물적요인',
      title: '부산역 수유실 냉방 고장',
      question: '부산역 수유실 에어컨이 안 돼요. 확인되면 010-****-1234로 알려주세요.',
      answer: `${ANSWER_HEAD} 수유실 냉방기를 점검하여 수리를 마쳤습니다. 담당: [담당부서] [담당자] [연락처]`,
      upperCompletion: '시정조치',
      completion: '역시설개선',
      deptPath: 'KORAIL>부산경남본부>건축처',
      handler: '[처리자]',
    },
    original: {
      question: [
        { text: '부산역 수유실 에어컨이 안 돼요. 확인되면 ' },
        { text: '010-9876-1234', pii: true },
        { text: '로 알려주세요.' },
      ],
      answer: [
        { text: `${ANSWER_HEAD} 수유실 냉방기를 점검하여 수리를 마쳤습니다. 담당: ` },
        { text: '건축처 건축설비부', pii: true },
        { text: ' ' },
        { text: '오세훈', pii: true },
        { text: ' ' },
        { text: '051-440-0000', pii: true },
      ],
      handler: '오세훈',
    },
    summary: '부산역 수유실 냉방기 고장',
    classification: {
      journey: '역 방문',
      category: '물적',
      cause1: '시설물',
      cause2: '냉난방',
      place1: '역',
      place2: '여객',
      note: '기타 설비',
      dept: '건축',
    },
    flags: ['note'],
    reason: '분류 근거: "수유실", "냉방" 키워드 · 처리부서 경로 "…>건축처" · 비고가 기타 설비와 화장실 사이에서 갈림',
    status: 'review',
  },
];

/**
 * 처리부서 주소록 (가상) — 실제 주소는 코레일에서 받아 관리자 화면이나 서버 설정으로 넣어야 해요.
 * total = 이번 달 정리된 민원 수 (12,443건을 부서별로 나눈 가상 숫자)
 */
export const deptDirectory = {
  경영: { email: 'voc-management@korail.example', total: 623 },
  안전: { email: 'voc-safety@korail.example', total: 870 },
  영업: { email: 'voc-sales@korail.example', total: 4210 },
  승무: { email: 'voc-crew@korail.example', total: 1180 },
  차량: { email: 'voc-rollingstock@korail.example', total: 1290 },
  시설: { email: 'voc-track@korail.example', total: 1830 },
  건축: { email: 'voc-building@korail.example', total: 1460 },
  전기: { email: 'voc-electric@korail.example', total: 980 },
} as const;

/** 로그인한 VOC 담당자 (가상). 메일 인사말의 이름으로 들어가요. */
export const currentUser = { name: '김코레' };

export const PERIOD_LABEL = '2026년 9월';

export const statsSummary = {
  monthLabel: '9월',
  current: '2026년 9월',
  compare: '2025년 9월',
  fileCount: 5,
  total: 12443,
  yoyPercent: 12,
  repeatCount: 18,
  repeatNote: '명절·연휴에 집중',
};

/** 1차 원인별 건수 (상위 6개) */
export const causeTrends: CauseTrend[] = [
  { cause: '열차 지연', lastYear: 2140, thisYear: 3410 },
  { cause: '승차권', lastYear: 2760, thisYear: 2890 },
  { cause: '시스템', lastYear: 1880, thisYear: 2620 },
  { cause: '시설물', lastYear: 1750, thisYear: 1610 },
  { cause: '서비스', lastYear: 1290, thisYear: 1380 },
  { cause: '안내', lastYear: 640, thisYear: 590 },
];

export const repeatIssues: RepeatIssue[] = [
  { title: '명절 예매 대기 중 코레일톡 오류', detail: '시스템 · 코레일톡 · 3년 연속 9월 급증 · 42건' },
  { title: 'KTX 지연 후 배상 지연', detail: '열차 지연 · 배상 · 보상 · 매달 반복 · 31건' },
  { title: '역사 엘리베이터 고장', detail: '시설물 · 고장 · 같은 역 5회 · 12건' },
  { title: '수유실 냉방 불량', detail: '시설물 · 냉난방 · 여름철 반복 · 9건' },
];
