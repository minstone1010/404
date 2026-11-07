# KORAIL VOC 업무 자동화 · 프론트엔드

Figma 「VOC 간소화안 v3 · 덜 번거로운 흐름」 화면 6개를 옮긴 React 앱입니다.
코레일 민원 파일 양식(A~O열)과 분류 기준 임시안(고객 여정 단계 ~ 처리부서 8개)을 반영했어요.
지금은 **가상 데이터로 동작**하고, 백엔드 API가 준비되면 데이터 부분만 바꾸면 됩니다.

## 코레일 양식과 분류 기준 (가장 먼저 볼 파일)

| 파일 | 내용 | 바뀌면 |
| --- | --- | --- |
| `src/data/outputColumns.ts` | 출력 엑셀 A~O 15열, 열마다 가림 여부·코레일 메모, 업로드 필수 열(접수번호·접수일·질문) | 열 순서·이름이 바뀌면 여기만 고치기 |
| `src/data/taxonomy.ts` | 분류 8개 항목과 선택지 (**임시안 v0**), 처리부서 약칭→정식 이름, 처리부서 경로→8개 부서 변환 | 분류 기준이 확정되면 여기만 고치기 → 드롭다운·서랍·통계·엑셀이 같이 바뀜 |

**출력 엑셀** (부서별 전달의 `엑셀 내려받기` → `KORAIL_VOC_2026-09_영업처.xlsx` 처럼 부서마다 한 파일)

- 시트 「민원 목록」: A~O열은 코레일 양식 그대로예요. 질문·답변·처리자는 가린 값으로 들어가요.
  - 머리글은 회색 칸이고, 코레일 메모를 엑셀 메모로 달았어요.
  - P~W열에는 AI 분류 8개를 붙였어요. 머리글은 파란 칸이고, AI가 자신 없어 검토한 칸은 노란색이에요.
  - 원본 양식만 필요하면 `downloadVocWorkbook(rows, name, false)`로 부르면 돼요.
- 시트 「분류 기준」: 지금 쓰는 분류 항목과 선택지

**개인정보 가림 규칙 (시연용 표기)**

- 질문: `김**`, `010-****-5678`, `영**@example.com`, `***-***`(계좌)
- 답변: 담당 부서·이름·연락처를 `[담당부서] [담당자] [연락처]`로 바꿔요.
- 처리자: `[처리자]`

## 실행

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # dist/ (배포용)
npm run build:single # dist-single/index.html 한 파일 (팀원에게 보내는 미리보기용)
```

Node 20 이상. 화면은 Figma와 같은 1440×900 데스크톱 기준이고, 1280px보다 좁으면 가로로 스크롤돼요.

## 기술 스택

- React 19 + TypeScript + Vite
- react-router-dom 7 (HashRouter: 서버 설정 없이 어디에 올려도 새로고침해도 화면이 유지돼요)
- exceljs 4.4 (엑셀 읽기·쓰기, 버튼을 누를 때만 불러와요)
- 스타일은 일반 CSS + CSS 변수. Figma 변수 이름(`--accent`, `--warnbg` …)을 그대로 썼어요 → `src/styles/tokens.css`
- 글꼴: Noto Sans KR (Google Fonts)

## 화면과 Figma 노드

| 주소 | 화면 | Figma 노드 | 파일 |
| --- | --- | --- | --- |
| `#/` | 1 파일 올리기 | 87:202 | `src/pages/UploadPage.tsx` |
| `#/analysis` | 2 자동 분석 중 | 87:285 | `src/pages/AnalysisPage.tsx` |
| `#/review` | 3 검토함 | 83:112 | `src/pages/ReviewPage.tsx` |
| (검토함에서 행 클릭) | 4 민원 자세히 보기 (서랍) | 83:308 | `src/pages/ComplaintDrawer.tsx` |
| `#/delivery` | 부서별 전달 (5 전달 확인을 대신하는 **새 화면**, Figma 시안 없음) | — | `src/pages/DeliveryPage.tsx` |
| (부서별 전달에서) | 엑셀 열어보기 창 · 메일 쓰기 | — | `SheetViewer.tsx`, `MailCompose.tsx` |
| `#/stats` | 6 통계·보고서 | 85:364 | `src/pages/StatsPage.tsx` |
| `#/history` | 처리 이력 | **시안 없음** (임시 화면) | `src/pages/HistoryPage.tsx` |

공통 컴포넌트(`src/components/`)

| 컴포넌트 | Figma |
| --- | --- |
| `Sidebar` | v3/Sidebar (82:93) |
| `Button` primary / secondary | VOC/Button (63:84, 63:86) |
| `Chip` warn / ok / info / bad | v3/Chip (82:84~82:91) |
| `Select` | 표·서랍의 "선택 상자" — Figma 모양 위에 투명한 네이티브 select를 겹쳐 접근성 유지 |
| `PageHeader`, `ProgressBar` | 화면마다 반복되는 머리말, 진행 막대 |

## 폴더 구조

```
src/
  styles/      tokens.css(Figma 변수·글자 스타일), global.css
  components/  Sidebar, ui.tsx(Button·Chip·Select·PageHeader·ProgressBar), ui.css
  pages/       화면 6개 + 처리 이력, pages.css
  data/mock.ts 시연용 가상 데이터 (Figma 숫자·문구 그대로)
  store.tsx    화면 사이에서 공유하는 상태 (파일 목록, 민원, 승인·발송 상태)
  types.ts     데이터 타입
```

## 동작하는 것

- 파일 올리기
  - 실제 .xlsx의 머리글을 읽어 필수 열(접수번호·접수일·질문)이 있는지 확인하고 건수를 세요.
  - 열이 없으면 "열 지정"에서 그 파일의 머리글 중 하나를 골라요.
- 자동 분석: 진행률이 시간에 따라 올라가는 흉내예요.
- 검토함
  - 열: 접수번호 · 제목/AI 요약 · 1차 원인 · 2차 원인 · 가린 질문 · 처리부서 · 확인할 부분
  - 원인과 부서를 드롭다운으로 고치면 노란 표시가 사라져요.
- 서랍
  - 질문 원문과 가린 질문을 비교하고, 가린 답변과 처리자를 볼 수 있어요.
  - **분류 8개를 모두 수정**할 수 있어요.
  - 원본 정보(접수일, 처리기한, 고객요구유형, 완료유형, 처리부서 경로 → 8개 부서)도 보여요.
- 부서별 전달 (메일 흐름을 바꿨어요)
  1. 검토함에서 **승인**하면 메일 창 없이 바로 처리부서별 엑셀에 들어가요. AI가 자신 있게 분류한 민원은 처음부터 들어가 있어요.
  2. **부서별 전달** 화면에 처리부서 8곳이 나와요. 부서마다 정리된 건수, 많이 들어온 원인, 상태(보낼 준비 완료 / 검토 대기 n건 / 보냄 시각)를 보여줘요.
  3. **엑셀 열어보기**를 누르면 정리된 엑셀을 화면에서 시트처럼 볼 수 있어요. A~W열, 행 번호, 가림 표시가 있고 내려받기도 돼요.
  4. **메일 보내기**를 누르면 메일 쓰기 화면으로 넘어가요.
     - 보내는 사람 이름, 받는 사람(부서 주소), 제목, 본문, 첨부 엑셀이 들어 있어요.
     - 본문 기본 문구는 "안녕하세요. / 코레일 민원 VOC 담당자 OOO입니다. / 정리한 민원 보내드립니다."예요. 담당자가 고칠 수 있고, 고친 문구는 다른 부서 메일에도 그대로 쓰여요.
  5. **보내기**를 누르면 바로 보내져요. 지금은 시연용으로 보낸 것처럼 처리해요. 부서 상태는 "보냄 · 시각"이 되고 처리 이력에 남아요.
- 엑셀 내려받기 (부서별 전달·통계): 위 양식대로 진짜 .xlsx를 만들어요.
- 통계: 1차 원인별로 작년과 비교해요.

## 백엔드 붙일 때 바꿀 곳

계획서의 API 목록과 연결됩니다. 지금 가짜로 처리하는 곳마다 주석을 달아 두었어요.

| 지금 | 바꿀 API |
| --- | --- |
| `UploadPage` `addFiles` | `POST /batches`, `PUT /files/{id}/columns`, `DELETE /files/{id}` |
| `AnalysisPage` 진행률 타이머 | `GET /batches/{id}/progress` 2초 폴링 |
| `data/mock.ts` `complaints`, `reviewTotals` | `GET /complaints?status=&file=&dept=&page=` |
| `store.tsx` `setType`·`setDepartment`·`approve` | `PATCH /complaints/{id}`, `POST /complaints/approve` |
| 서랍의 원문 | `GET /complaints/{id}/original` (검토자 권한만) |
| `MailCompose` 보내기 | `POST /mail/send` {부서, 받는 사람, 제목, 본문} → 서버가 부서 엑셀을 만들어 첨부해 발송 |
| `data/mock.ts` `deptDirectory` (가상 주소) | 부서 주소록 API 또는 관리자 설정 |
| `StatsPage` 데이터 | `GET /stats?current=&compare=` |
| Excel·PDF 버튼 (지금은 알림만) | `GET /exports/…` |

## 알아둘 점

- **업로드 아이콘은 임시**예요. Figma 에셋을 내려받을 수 없어 같은 모양으로 그렸어요. Figma에서 `icon/upload`(87:225)를 SVG로 내보내 `src/assets/icon-upload.svg`를 바꿔주세요.
- **처리 이력·열 지정 창·개별 업무 선택**은 v3 시안이 없어 최소한으로만 만들었어요.
- 검토함 표에는 시연용 6건만 들어 있어요. 접수번호·이름·연락처·문장은 모두 지어낸 예시예요.
- 부서 엑셀을 열면 이번 달 전체 건수(가상) 중 예시 행만 보여요. 실제로는 서버가 전체 행으로 파일을 만들어요.
- 처리부서 경로가 8개 부서 이름과 맞지 않으면(예: `…>고객서비스처`) 「확인할 부분: 처리부서」로 표시해요. 8개 부서 밖의 부서를 어떻게 다룰지는 정해야 해요.
- 분석 화면은 올린 파일과 관계없이 Figma의 파일 5개로 진행돼요 (백엔드 연결 전 한계).
