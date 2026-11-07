/**
 * AI가 자신 있게 분류해 바로 정리된 민원 예시 (검토 불필요 12,325건을 대신하는 시연용 표본)
 * 부서마다 엑셀을 열어봤을 때 행이 보이도록 만든 가상 데이터예요. 이름·번호·문장은 모두 지어냈어요.
 */
import type { Classification } from './taxonomy';
import type { Complaint, VocRecord } from '../types';

type Template = {
  title: string;
  question: string;
  kind: string;
  channel: string;
  demandType: string;
  upper: string;
  completion: string;
  deptPath: string;
  summary: string;
  c: Classification;
};

const T: Template[] = [
  { title: '승차권 반환 수수료 문의', question: '출발 10분 전에 반환했는데 수수료가 왜 이렇게 많이 나오나요?', kind: '불편개선', channel: '홈페이지', demandType: '제도적요인', upper: '참고안내', completion: '제도설명', deptPath: 'KORAIL>여객사업본부>영업처', summary: '반환 수수료 기준 문의', c: { journey: '이용 후 / 연계교통', category: '제도적', cause1: '승차권', cause2: '결제 · 환불', place1: '기타', place2: '온라인', note: '', dept: '영업' } },
  { title: '좌석 중복 발권', question: '제 좌석에 다른 분이 같은 표를 가지고 계셨어요. 확인 부탁드립니다.', kind: '불편개선', channel: '고객센터', demandType: '물적요인', upper: '시정조치', completion: '사실설명', deptPath: 'KORAIL>여객사업본부>영업처', summary: '같은 좌석 중복 발권', c: { journey: '예매 및 발권', category: '물적', cause1: '시스템', cause2: '오류', place1: '기차', place2: 'KTX', note: '', dept: '영업' } },
  { title: '자동발매기 카드 결제 안 됨', question: '서울역 3번 자동발매기에서 카드 결제가 계속 실패해요.', kind: '불편개선', channel: '방문(접점)', demandType: '물적요인', upper: '시정조치', completion: '역시설개선', deptPath: 'KORAIL>서울본부>영업처', summary: '자동발매기 결제 실패', c: { journey: '예매 및 발권', category: '물적', cause1: '시설물', cause2: '고장', place1: '역', place2: '여객', note: '자동발매기', dept: '영업' } },
  { title: '승강장 안전펜스 파손', question: '수원역 4번 승강장 안전펜스 일부가 떨어져 있어 위험해 보입니다.', kind: '불편개선', channel: '홈페이지', demandType: '물적요인', upper: '시정조치', completion: '역시설개선', deptPath: 'KORAIL>수도권서부본부>시설처', summary: '승강장 안전펜스 파손', c: { journey: '역 방문', category: '물적', cause1: '시설물', cause2: '파손', place1: '역', place2: '광역', note: '승강장', dept: '시설' } },
  { title: '선로변 수목 정리 요청', question: '집 뒤 선로변 나무가 너무 자라 창문을 가립니다. 정리해 주세요.', kind: '국민신문고', channel: '신문고', demandType: '물적요인', upper: '반영개선', completion: '기타', deptPath: 'KORAIL>대전충남본부>시설처', summary: '선로변 수목 정리 요청', c: { journey: '이용 외(外)', category: '물적', cause1: '수목 제거', cause2: '단순요청', place1: '철도용지', place2: '장소 없음', note: '', dept: '시설' } },
  { title: '객실 냉방이 너무 셈', question: 'ITX-새마을 3호차 냉방이 너무 세서 춥습니다.', kind: '불편개선', channel: '고객센터', demandType: '물적요인', upper: '참고안내', completion: '사실설명', deptPath: 'KORAIL>차량본부>차량처', summary: '객실 냉방 과다', c: { journey: '수송', category: '물적', cause1: '시설물', cause2: '냉난방', place1: '기차', place2: 'ITX-새마을', note: '차체', dept: '차량' } },
  { title: '객실 출입문 고장', question: '무궁화호 5호차 출입문이 잘 안 열려서 내리지 못할 뻔했어요.', kind: '불편개선', channel: '홈페이지', demandType: '물적요인', upper: '시정조치', completion: '기타', deptPath: 'KORAIL>차량본부>차량처', summary: '객실 출입문 작동 불량', c: { journey: '수송', category: '물적', cause1: '시설물', cause2: '고장', place1: '기차', place2: '무궁화', note: '차체', dept: '차량' } },
  { title: '열차팀장 안내 친절', question: '몸이 불편한 어머니를 끝까지 도와주신 열차팀장님께 감사드립니다.', kind: '불편개선', channel: '홈페이지', demandType: '인적요인', upper: '기타', completion: '기타', deptPath: 'KORAIL>여객사업본부>승무처', summary: '열차팀장 친절 칭찬', c: { journey: '수송', category: '인적', cause1: '서비스', cause2: '친절', place1: '기차', place2: 'KTX', note: '열차팀장/여객전무', dept: '승무' } },
  { title: '객실 내 소란 승객', question: '객실에서 큰 소리로 통화하는 승객이 있었는데 제지가 없었어요.', kind: '불편개선', channel: '고객센터', demandType: '인적요인', upper: '참고안내', completion: '교육', deptPath: 'KORAIL>여객사업본부>승무처', summary: '객실 내 소란 제지 요청', c: { journey: '수송', category: '인적', cause1: '질서유지', cause2: '불만', place1: '기차', place2: 'KTX', note: '열차팀장/여객전무', dept: '승무' } },
  { title: '역 화장실 누수', question: '부산역 2층 화장실 천장에서 물이 떨어집니다.', kind: '불편개선', channel: '방문(접점)', demandType: '물적요인', upper: '시정조치', completion: '역시설개선', deptPath: 'KORAIL>부산경남본부>건축처', summary: '역 화장실 천장 누수', c: { journey: '역 방문', category: '물적', cause1: '시설물', cause2: '노후', place1: '역', place2: '여객', note: '화장실', dept: '건축' } },
  { title: '대합실 의자 부족', question: '천안아산역 대합실에 앉을 의자가 너무 부족합니다.', kind: '불편개선', channel: '홈페이지', demandType: '물적요인', upper: '반영개선', completion: '역시설개선', deptPath: 'KORAIL>대전충남본부>건축처', summary: '대합실 의자 부족', c: { journey: '역 방문', category: '물적', cause1: '시설물', cause2: '단순제안', place1: '역', place2: '여객', note: '의자', dept: '건축' } },
  { title: '에스컬레이터 정지', question: '광명역 에스컬레이터가 일주일째 멈춰 있어요.', kind: '불편개선', channel: '홈페이지', demandType: '물적요인', upper: '시정조치', completion: '역시설개선', deptPath: 'KORAIL>수도권서부본부>전기처', summary: '역 에스컬레이터 장기 정지', c: { journey: '역 방문', category: '물적', cause1: '시설물', cause2: '고장', place1: '역', place2: '여객', note: '에스컬레이터', dept: '전기' } },
  { title: '승강장 조명 어두움', question: '밤에 동대구역 승강장 끝쪽 조명이 꺼져 있어 어둡습니다.', kind: '불편개선', channel: '고객센터', demandType: '물적요인', upper: '시정조치', completion: '역시설개선', deptPath: 'KORAIL>대구본부>전기처', summary: '승강장 조명 소등', c: { journey: '역 방문', category: '물적', cause1: '시설물', cause2: '고장', place1: '역', place2: '여객', note: '승강장', dept: '전기' } },
  { title: '건널목 차단기 늦게 내려감', question: '마을 건널목 차단기가 열차가 가까이 와서야 내려가 위험합니다.', kind: '국민신문고', channel: '신문고', demandType: '물적요인', upper: '시정조치', completion: '기타', deptPath: 'KORAIL>안전본부>안전보건처', summary: '건널목 차단기 작동 지연', c: { journey: '이용 외(外)', category: '물적', cause1: '시설물', cause2: '작업', place1: '선로', place2: '장소 없음', note: '구조물', dept: '안전' } },
  { title: '선로 작업 소음', question: '새벽마다 선로 작업 소음 때문에 잠을 잘 수 없어요.', kind: '국민신문고', channel: '신문고', demandType: '제도적요인', upper: '참고안내', completion: '사실설명', deptPath: 'KORAIL>안전본부>안전보건처', summary: '야간 선로 작업 소음', c: { journey: '이용 외(外)', category: '제도적', cause1: '소음', cause2: '작업', place1: '선로', place2: '장소 없음', note: '', dept: '안전' } },
  { title: '채용 절차 문의', question: '사회복무요원 근무지 배정 절차가 궁금합니다.', kind: '불편개선', channel: '홈페이지', demandType: '제도적요인', upper: '참고안내', completion: '제도설명', deptPath: 'KORAIL>경영인사본부>경영인사처', summary: '사회복무요원 배정 문의', c: { journey: '이용 외(外)', category: '제도적', cause1: '기타', cause2: '단순문의', place1: '기타', place2: '장소 없음', note: '사회복무요원/인턴', dept: '경영' } },
];

const pad = (n: number, w = 2) => String(n).padStart(w, '0');

/** 템플릿마다 날짜·접수번호를 바꿔 2건씩 만들어요 */
export const autoSamples: Complaint[] = T.flatMap((t, i) =>
  [0, 1].map((k) => {
    const day = 2 + ((i * 3 + k * 11) % 27);
    const hour = 8 + ((i + k * 5) % 10);
    const seq = i * 2 + k;
    const date = `2026-09-${pad(day)}`;
    const record: VocRecord = {
      receiptNo: `${pad(500 + seq, 3)}-2609${pad(day)}${pad(seq)}`,
      complaintKind: t.kind,
      channel: t.channel,
      registeredAt: `${date} ${pad(hour)}:${pad((seq * 7) % 60)}:00`,
      receivedAt: `${date} ${pad(hour)}:${pad((seq * 7 + 4) % 60)}:00`,
      dueAt: `2026-09-${pad(Math.min(30, day + 7))} 18:00:00`,
      completedAt: `2026-09-${pad(Math.min(30, day + 2))} ${pad(hour)}:30:00`,
      demandType: t.demandType,
      title: t.title,
      question: t.question,
      answer: '안녕하십니까? 한국철도공사 입니다. 귀하의 민원을 확인하여 조치하였습니다. 담당: [담당부서] [담당자] [연락처]',
      upperCompletion: t.upper,
      completion: t.completion,
      deptPath: t.deptPath,
      handler: '[처리자]',
    };
    return {
      id: `a${seq}`,
      fileName: '자동 확인',
      record,
      original: { question: [{ text: t.question }], answer: [], handler: '' },
      summary: t.summary,
      classification: t.c,
      flags: [],
      reason: 'AI가 자신 있게 분류한 민원이에요',
      status: 'approved' as const,
      source: 'auto' as const,
    };
  }),
);
