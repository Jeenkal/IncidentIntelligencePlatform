from app.database.connection import SessionLocal
from app.services.retrieval import hybrid_search, build_or_tsquery

q = "Production API returning HTTP 502 After a deployment"
print("ts_query:", build_or_tsquery(q))
db = SessionLocal()
for domain in ("postgresql", "devops"):
    rows = hybrid_search(db, q, domain)
    print(domain, [(r["id"], r["title"], round(float(r["score"]), 4)) for r in rows])