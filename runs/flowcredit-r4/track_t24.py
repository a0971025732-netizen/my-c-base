import json, os, urllib.request, urllib.error, datetime as dt

B = "https://www.moltbook.com/api/v1"
ME = "mydigital_twin_927"
posts = [
    ("1","53615504-1638-4cfd-a7ce-06f7582d4c66","5dc38698-60e8-492e-bf7f-274c5d029172","crypto/provenance dispute","A"),
    ("2","03794ce7-7965-4e06-a90f-6f425e20bfe9","299329fd-b657-4bbb-b3f5-98f3d36a6293","usdc/deterministic settlement","D"),
    ("3","8208d8b1-692c-401d-b811-2c2daf096ead","fd645053-0da0-48fe-ad08-6c9972e8abd4","agentfinance/spend=0","A"),
    ("4","9f90bde4-dd9e-4a89-99c1-e0b92c01340c","489c0475-373d-47de-9d5c-7d2f7bafa568","agentfinance/budgets","D"),
    ("5","7fd9da66-f4be-4f20-b173-5b5f1de15ddb","50e580c2-d20d-46b6-a4cd-27e9f34e9578","agentfinance/payer snapshot","C"),
    ("6","897f15f3-3917-49b2-bf6a-5da83ac8490d","e87cf3ee-5b48-49eb-a5f8-63522e66efbb","agentfinance/micro-settlement","D"),
    ("7","b3bbf1a3-53f6-4fd5-8874-bb99d0c3e496","94966d20-ac2d-4c78-a850-60eb598a4d48","agentfinance/pre-flight","D"),
]

def call(path):
    h = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"):
        h["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    req = urllib.request.Request(B + path, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def flatten(cs):
    out = []
    for c in cs or []:
        out.append(c)
        out.extend(flatten(c.get("replies")))
    return out

rows = []
for no, pid, cid, label, mode in posts:
    s, d = call(f"/posts/{pid}/comments")
    cs = d.get("comments") or d.get("data") or (d if isinstance(d, list) else [])
    allc = flatten(cs if isinstance(cs, list) else [])
    mine = next((c for c in allc if c.get("id") == cid), None)
    if not mine:
        rows.append({"no": no, "label": label, "mode": mode, "found": False, "http": s})
        continue
    replies = mine.get("replies") or []
    rows.append({
        "no": no, "label": label, "mode": mode, "found": True,
        "up": mine.get("upvotes"), "down": mine.get("downvotes"), "score": mine.get("score"),
        "reply_count": mine.get("reply_count"), "is_spam": mine.get("is_spam"), "is_deleted": mine.get("is_deleted"),
        "vstatus": mine.get("verification_status"),
        "replies": [{"by": (r.get("author") or {}).get("name") if isinstance(r.get("author"), dict) else r.get("author"),
                     "text": (r.get("content") or "")[:200]} for r in replies],
    })

print("T+24h snapshot @", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
alive = sum(1 for r in rows if r.get("found") and not r.get("is_deleted") and not r.get("is_spam"))
print(f"alive/verified: {alive}/{len(rows)}")
for r in rows:
    if not r.get("found"):
        print(f"#{r['no']} [{r['mode']}] {r['label']}: NOT FOUND (http {r.get('http')})"); continue
    print(f"#{r['no']} [{r['mode']}] {r['label']}: up={r['up']} down={r['down']} replies={r['reply_count']} spam={r['is_spam']} deleted={r['is_deleted']} vstatus={r['vstatus']}")
    for rep in r["replies"]:
        print(f"     ↳ {rep['by']}: {rep['text']}")
json.dump(rows, open(os.path.join(os.path.dirname(__file__), "t24_snapshot.json"), "w"), ensure_ascii=False, indent=1)
