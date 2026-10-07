import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os

os.environ["STARTUP_MODELS"] = "false"
from backend.service import Service
from backend import notebook_logic as l

s = Service()
print("DATA", len(l.df), l.df.데이터역할.value_counts().to_dict())
print("LOCATION", l.lookup_location("수원역"))
print("CHANNEL", s.parse_channel("APP 코레일톡 앱"))
print("DETAIL", s.detail(l.df.loc[l.df.데이터역할.eq("검토대상"), "번호"].iloc[0]))
from fastapi.testclient import TestClient
from backend.main import app

with TestClient(app) as c:
    r = c.get("/api/vocs")
    print("LIST", r.status_code, len(r.json()))
    id = r.json()[0]["id"]
    print("DETAIL_API", c.get("/api/vocs/" + id).status_code)
    print("UI", c.get("/").status_code)
    print("STATS", c.get("/api/stats").json())
    print(
        "UNAUTHORIZED_APPROVAL",
        c.post(
            "/api/vocs/" + id + "/decision",
            json={"status": "승인완료", "department": s.teams[0]},
        ).status_code,
    )
