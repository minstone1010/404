import { TAXONOMY } from '../data/taxonomy';
import type { ReviewFlag } from '../types';

export const flagLabel = (f: ReviewFlag) => (f === '개인정보' ? '개인정보' : TAXONOMY[f].label);

/** 확인할 부분 칩 문구: "2차 원인 외 1" */
export function flagSummary(flags: ReviewFlag[]) {
  if (flags.length === 0) return null;
  return flags.length === 1 ? flagLabel(flags[0]) : `${flagLabel(flags[0])} 외 ${flags.length - 1}`;
}
