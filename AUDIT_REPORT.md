# VOC 시스템 결함 점검 (2026-10-06)

운영 Excel/DB/서버 코드는 수정하지 않았다. 임시 SQLite와 합성 검색 사례, 실제 UI의 API 응답을 가로챈 브라우저 테스트로 검증했다. 전체 정확도 평가와 구분한다.

| 우선순위 | 결함 | 검증 및 개선 |
|---|---|---|
| 높음 | 재분석 실패 후에도 이전 승인 상태 유지 | 같은 signature에서 실패한 새 분석이 승인완료로 표시됨을 재현. 분석 실행 ID와 승인 대상 ID 연결 필요. service.py:121, decision.py:27 |
| 높음 | 불확실한 지역의 fallback 후보가 추천가능으로 표시 | 천안 지역 정보와 확인필요 scope에서 전남 시설 부서 추천가능 합성 사례 재현. 참고 검색은 유지하되 라우팅 미확정은 확인대기로 표시. routing.py:4, notebook_logic.py:379 |
| 높음 | JSON 검증을 통과하는 의미 오류 | 유실물에 D2 및 원문에 없는 승강설비 키워드가 포함된 출력 수용. 원문 근거/모순 검사와 재시도 필요 |
| 높음 | 중복 이력이 독립 근거처럼 계산 | 독립 그룹 1개의 2행이 support_count=2로 추천가능. 실제 history 1988행/1926그룹, 중복 그룹58개. 그룹 기준 검색/빈도/지원 건수 필요. notebook_logic.py:361 |
| 높음 | 재분석 중 승인 및 중복 요청 가능 | 실제 UI에서 승인 활성화와 화면 이동 후 분석 POST 2회 재현. VOC별 실행 상태와 서버 분석 버전 검증 필요. app.js:20 |
| 중간 | 다른 VOC 응답으로 작성 중 입력 손실 | A 분석 중 B에 입력한 메모/부서가 A 응답의 reload로 초기화됨. VOC별 초안 보존 필요. app.js:11,20 |
| 중간 | export에 이전 설정 결과 혼합 | 현재 NEW 분석을 이전 signature 수동 OLD가 덮어씀. 현재 결과와 과거 이력 분리 필요. decision.py:35 |
| 중간 | 캐시 의존성 오류 | TOP_N 변경은 signature 동일, 임계값 변경은 Qwen 캐시까지 무효화. 분석/인덱스/추천 캐시 분리 및 프롬프트 버전 필요. service.py:18 |
| 중간 | 시작 시 반복 index 구축 | 캐시20행에서3회 재현. 1988행이면 분기상199회 호출. 실제 변경 때만 갱신 필요. 이는 전체 Embedding 재계산 횟수를 뜻하지 않음. service.py:80 |
| 중간 | 준비 중 실패 집계 부정확 | 저장된 이력 오류77건인데 API history_failed=0인 시점 확인. 성공/실패/검색가능 건수를 별도 집계 필요 |
| 중간 | 잘못된 수치 설정 수용 | MIN_SCORE_MARGIN=nan 허용 재현. 유한성과 범위 검증 필요 |
| 중간 | 평가 중 사용자 분석 대기 | evaluate 전체가 공용 잠금 유지. 코드 검토 결과이며 장시간 대기 측정은 미실시. service.py:126 |

재현 자료: outputs/audit_reproductions.json (9개 검증), outputs/audit_browser_reproductions.json (3개 검증), outputs/audit_runtime.json (읽기 전용 운영 스냅샷).
재현 스크립트: outputs/audit_reproduce.py, outputs/audit_browser.py, outputs/audit_readonly.py.

수정 및 전체 holdout 성능 평가는 이번 점검에서 수행하지 않았다. 가중치를 0.5:0.5로 바꾸기 전에 라우팅 확정 여부, 중복 근거, 승인 버전 관리를 먼저 수정해야 한다.
