/**
 * 엑셀 읽기·쓰기 (exceljs, 필요할 때만 불러와요)
 * - readVocFile: 올린 파일의 머리글을 보고 필수 열이 있는지, 몇 건인지 확인
 * - downloadVocWorkbook: 코레일 양식(A~O열) 그대로 정리된 결과 엑셀을 만들어 내려받기
 */
import { OUTPUT_COLUMNS, REQUIRED_HEADERS } from '../data/outputColumns';
import { DEPT_FULL_NAME, TAXONOMY, TAXONOMY_ORDER, TAXONOMY_VERSION } from '../data/taxonomy';
import type { Complaint } from '../types';

/** 머리글 이름이 조금 달라도 같은 열로 봐요 */
const HEADER_ALIASES: Record<string, string[]> = {
  접수번호: ['접수번호', '접수 번호', '민원번호'],
  접수일: ['접수일', '접수일자', '접수일시'],
  질문: ['질문', '민원내용', '민원 내용', '내용'],
};

const normalize = (s: string) => s.replace(/\s/g, '');

export interface ReadResult {
  count: number;
  headers: string[];
  missing: string[];
}

export async function readVocFile(file: File): Promise<ReadResult> {
  const { default: ExcelJS } = await import('exceljs');
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(await file.arrayBuffer());
  const ws = wb.worksheets[0];
  if (!ws) return { count: 0, headers: [], missing: [...REQUIRED_HEADERS] };

  const headers: string[] = [];
  ws.getRow(1).eachCell({ includeEmpty: false }, (cell) => headers.push(String(cell.text).trim()));
  const normalized = headers.map(normalize);
  const missing = REQUIRED_HEADERS.filter(
    (h) => !HEADER_ALIASES[h].some((alias) => normalized.includes(normalize(alias))),
  );

  let count = 0;
  ws.eachRow({ includeEmpty: false }, (row, n) => {
    if (n > 1 && row.cellCount > 0) count += 1;
  });
  return { count, headers, missing };
}

const HEADER_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFBFBFBF' } } as const;
const CLASS_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDDEBF7' } } as const;
const FLAG_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFF2CC' } } as const;

/**
 * 결과 엑셀
 * 시트1 "민원 목록": A~O 코레일 양식 (질문·답변·처리자는 가린 값)
 *                    + P열부터 AI 분류 8개 (분류 기준 임시안이라 따로 색을 달리했어요)
 * 시트2 "분류 기준": 지금 쓰는 분류 항목과 선택지
 */
export async function downloadVocWorkbook(rows: Complaint[], fileName: string, withClassification = true) {
  const { default: ExcelJS } = await import('exceljs');
  const wb = new ExcelJS.Workbook();
  wb.creator = 'KORAIL VOC 업무 자동화';

  const ws = wb.addWorksheet('민원 목록', { views: [{ state: 'frozen', ySplit: 1 }] });
  const classCols = withClassification
    ? TAXONOMY_ORDER.map((k) => ({ key: k, header: `[AI] ${TAXONOMY[k].label}`, width: k === 'cause2' || k === 'note' ? 16 : 13 }))
    : [];

  ws.columns = [
    ...OUTPUT_COLUMNS.map((c) => ({ header: c.header, key: c.key, width: c.width })),
    ...classCols.map((c) => ({ header: c.header, key: `class_${c.key}`, width: c.width })),
  ];

  const header = ws.getRow(1);
  header.height = 22;
  header.eachCell((cell, col) => {
    cell.font = { bold: true, size: 11 };
    cell.alignment = { vertical: 'middle', horizontal: 'center' };
    cell.fill = col > OUTPUT_COLUMNS.length ? CLASS_FILL : HEADER_FILL;
    const memo = OUTPUT_COLUMNS[col - 1]?.memo;
    if (memo) cell.note = `KORAIL:\n${memo}`;
  });
  if (withClassification) {
    ws.getCell(1, OUTPUT_COLUMNS.length + 1).note = `AI 분류 (${TAXONOMY_VERSION})\n노란 칸은 AI가 자신 없어 검토한 칸이에요.`;
  }

  for (const c of rows) {
    const values: Record<string, string> = { ...c.record };
    if (withClassification) {
      for (const k of TAXONOMY_ORDER) {
        values[`class_${k}`] = k === 'dept' && c.classification.dept ? DEPT_FULL_NAME[c.classification.dept] : c.classification[k];
      }
    }
    const row = ws.addRow(values);
    row.alignment = { vertical: 'top', wrapText: false };
    row.getCell('question').alignment = { vertical: 'top', wrapText: true };
    row.getCell('answer').alignment = { vertical: 'top', wrapText: true };
    if (withClassification) {
      for (const k of TAXONOMY_ORDER) {
        if (c.flags.includes(k)) row.getCell(`class_${k}`).fill = FLAG_FILL;
      }
    }
  }
  ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: ws.columnCount } };

  const ref = wb.addWorksheet('분류 기준');
  ref.addRow([`분류 기준 ${TAXONOMY_VERSION} — 확정 전이에요. 바뀌면 src/data/taxonomy.ts 를 고쳐주세요.`]).font = { bold: true };
  ref.addRow([]);
  const longest = Math.max(...TAXONOMY_ORDER.map((k) => TAXONOMY[k].options.length));
  const head = ref.addRow(TAXONOMY_ORDER.map((k) => TAXONOMY[k].label));
  head.eachCell((cell) => {
    cell.font = { bold: true };
    cell.fill = HEADER_FILL;
  });
  for (let i = 0; i < longest; i++) {
    ref.addRow(
      TAXONOMY_ORDER.map((k) => {
        const v = (TAXONOMY[k].options as readonly string[])[i] ?? '';
        return k === 'dept' && v ? `${v} (${DEPT_FULL_NAME[v as keyof typeof DEPT_FULL_NAME]})` : v;
      }),
    );
  }
  ref.columns.forEach((col) => (col.width = 20));

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
