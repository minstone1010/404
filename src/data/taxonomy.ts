/**
 * 민원 분류 기준 — 임시안 v0 (2026-10-31, 팀 내부 정리 전)
 *
 * 코레일 분류표 이미지(고객 여정 단계 ~ 처리부서)를 그대로 옮겼어요.
 * 아직 확정이 아니니, 항목·선택지를 바꿀 때는 이 파일만 고치면
 * 검토함 드롭다운, 서랍, 통계, 출력 엑셀이 모두 따라 바뀝니다.
 */

export const TAXONOMY_VERSION = '임시안 v0';

export const TAXONOMY = {
  journey: {
    label: '고객 여정 단계',
    options: ['예매 및 발권', '역 방문', '수송', '이용 후 / 연계교통', '이용 외(外)'],
  },
  category: {
    label: '구분',
    options: ['인적', '물적', '제도적', '기타'],
  },
  cause1: {
    label: '1차 원인',
    options: [
      '서비스', '질서유지', '안내', '승차권', '승객 간 분쟁', '시설물', '시스템', '열차 지연', '열차 중지',
      '유실물', '수목 제거', '적치물 제거', '소음', '촬영승인', 'VOE', '서비스 아이디어 제안', '기타',
    ],
  },
  cause2: {
    label: '2차 원인',
    options: [
      '친절', '불친절', '오류', '배상 · 보상', '냉난방', '고장', '파손', '노후', '코레일톡', '홈페이지',
      '결제 · 환불', '작업', '열차 통과', '연계교통비 지급 요청', 'CCTV 제공요청', '영업사고 접수 요청',
      '단순요청', '단순문의', '단순제안', '여행상품', '불만', '기타',
    ],
  },
  place1: {
    label: '발생 장소1',
    options: ['역', '기차', '선로', '철도용지', '기타'],
  },
  place2: {
    label: '발생 장소2',
    options: [
      '여객', '광역', 'KTX', 'ITX-새마을', 'ITX-마음', '새마을', '무궁화', '전동차', '동해선', '경전선',
      '경부선', '주차장', '온라인', '장소 없음',
    ],
  },
  note: {
    label: '비고',
    options: [
      '역무원', '열차팀장/여객전무', 'KN승무원', '사회복무요원/인턴', '기관사', '본부 스탭', '재신청',
      '에스컬레이터', '엘리베이터', 'ES, EV', '의자', '화장실', '승강장', '광장', '인도', '진출입로', '구조물',
      '기타 설비', '차체', '자동발매기', '사고', '규정외',
    ],
  },
  dept: {
    label: '처리부서',
    options: ['경영', '안전', '영업', '승무', '차량', '시설', '건축', '전기'],
  },
} as const;

export type TaxonomyKey = keyof typeof TAXONOMY;
export type TaxonomyValue<K extends TaxonomyKey> = (typeof TAXONOMY)[K]['options'][number];

/** 민원 한 건에 붙는 분류 8개. 비고는 해당 없으면 빈칸이에요. */
export type Classification = { [K in TaxonomyKey]: TaxonomyValue<K> | '' };

/** 화면에 보여줄 순서 */
export const TAXONOMY_ORDER: TaxonomyKey[] = ['journey', 'category', 'cause1', 'cause2', 'place1', 'place2', 'note', 'dept'];

/** 처리부서 약칭 → 정식 이름 */
export const DEPT_FULL_NAME: Record<TaxonomyValue<'dept'>, string> = {
  경영: '경영인사처',
  안전: '안전보건처',
  영업: '영업처',
  승무: '승무처',
  차량: '차량처',
  시설: '시설처',
  건축: '건축처',
  전기: '전기처',
};

/**
 * 원본 "처리부서" 경로(KORAIL>부산경남본부>건축처, 여러 개면 쉼표)에서 8개 부서 중 하나를 찾아요.
 * 첫 번째(주무부서) 경로부터 보고, 끝 부서 이름에 정식 이름이나 약칭이 들어 있으면 그 부서예요.
 * 못 찾으면 null → 검토함에서 "확인할 부분: 처리부서"로 표시합니다.
 */
export function deptFromPath(path: string): TaxonomyValue<'dept'> | null {
  const entries = Object.entries(DEPT_FULL_NAME) as [TaxonomyValue<'dept'>, string][];
  for (const one of path.split(',').map((s) => s.trim()).filter(Boolean)) {
    const parts = one.split('>').map((s) => s.trim());
    for (const part of parts.reverse()) {
      const hit = entries.find(([short, full]) => part.includes(full) || part.startsWith(short));
      if (hit) return hit[0];
    }
  }
  return null;
}
