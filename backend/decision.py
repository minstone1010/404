import sqlite3, json
from datetime import datetime, timezone
from backend.config import settings


class Store:
    def __init__(self, path=None):
        self.path = path or settings.output / "voc.sqlite3"
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, signature TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS manual_analyses (id TEXT PRIMARY KEY, signature TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS decision_events (event_id INTEGER PRIMARY KEY, id TEXT, payload TEXT NOT NULL)"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def analysis(self, id, signature):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM analyses WHERE id=? AND signature=?",
                (id, signature),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def record_recommendation(self, id, signature, payload):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO analyses VALUES (?,?,?)",
                (
                    id,
                    signature,
                    json.dumps(payload, ensure_ascii=False, allow_nan=False),
                ),
            )

    def manual_analysis(self, id, signature):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM manual_analyses WHERE id=? AND signature=?",
                (id, signature),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_manual_analysis(self, id, signature, payload):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO manual_analyses VALUES (?,?,?)",
                (
                    id,
                    signature,
                    json.dumps(payload, ensure_ascii=False, allow_nan=False),
                ),
            )

    def load_approvals(self):
        with self.connect() as db:
            return {
                id: json.loads(p)
                for id, p in db.execute("SELECT id,payload FROM decisions")
            }

    def save_decision(
        self, id, department, state, memo, active_teams, ai_department, signature
    ):
        if state not in {"승인완료", "보류"}:
            raise ValueError("허용되지 않는 상태")
        if state == "승인완료" and department not in active_teams:
            raise ValueError("활성 처리부서를 선택하세요")
        payload = dict(
            id=id,
            status=state,
            department=department if state == "승인완료" else "",
            memo=memo[:500],
            ai_department=ai_department,
            signature=signature,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )
        text = json.dumps(payload, ensure_ascii=False)
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO decisions VALUES (?,?)", (id, text))
            db.execute(
                "INSERT INTO decision_events (id,payload) VALUES (?,?)", (id, text)
            )
        return payload

    def export_results(self):
        import pandas as pd

        with self.connect() as db:
            payloads = {
                id: json.loads(p)
                for id, p in db.execute("SELECT id,payload FROM analyses")
            }
            payloads.update(
                {
                    id: json.loads(p)
                    for id, p in db.execute("SELECT id,payload FROM manual_analyses")
                }
            )
            rows = [
                dict(id=id, **{k: v for k, v in payload.items() if k != "id"})
                for id, payload in payloads.items()
            ]
        approvals = self.load_approvals()
        for row in rows:
            row["decision"] = approvals.get(row["id"])
            row.update(
                {
                    k: (
                        json.dumps(v, ensure_ascii=False)
                        if isinstance(v, (dict, list))
                        else v
                    )
                    for k, v in list(row.items())
                }
            )
        dest = settings.output / "voc_results.xlsx"
        temp = dest.with_suffix(".tmp.xlsx")
        pd.DataFrame(rows).to_excel(temp, index=False)
        temp.replace(dest)
        return dest
