from pathlib import Path
p=Path('backend/cli.py'); s=p.read_text().replace("import argparse as _argparse\n",'').replace("row['番号'] if '番号' in row else row['번호']","row['번호']")
s=s.replace("'ground_truth_limitations':", "'timing_note':'analysis_seconds는 원래 분석 측정치, total_seconds는 현재 요청 처리시간(분석 캐시 재사용 가능)', 'ground_truth_limitations':")
p.write_text(s)
p=Path('backend/service.py'); s=p.read_text().replace("'total_seconds':result['analysis_seconds']+time.perf_counter()-t","'total_seconds':time.perf_counter()-t")
s=s.replace("('전체 과거 이력 준비 완료' if self.history_complete else f'이력 준비 종료: 분석 오류 {self.history_failed}건')", "f'과거 이력 준비 완료: 분석 오류 {self.history_failed}건'")
p.write_text(s)
