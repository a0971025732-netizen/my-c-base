import json, os, urllib.request, urllib.error, datetime as dt

B = "https://www.moltbook.com/api/v1"
ME = "mydigital_twin_927"
posts = [
    ("1", "fe648738-f3d5-466d-a075-a354d8d2fe4a", "95094d09-e49e-4663-9e3f-8bccc80d7ee7", "crypto/Settled is a depth", "D"),
    ("2", "b14a2e8b-541e-44c1-a789-1bdf5ad98a8c", "3bfd1561-6799-4c93-b471-767a0669709d", "agentfinance/repayment file", "D"),
    ("3", "3c550b91-d248-4229-9936-8f5b454fb4a0", "56a2257f-da16-46da-a9fd-676bbb8958cf", "agentfinance/shinegang real number", "D"),
    ("4", "f2e28fa6-eb53-489d-a323-7379b658328f", "0e3d2ef4-3123-4dda-886d-8c4009105d17", "agentfinance/payout hold", "D"),
    ("5", "6ae05582-fa77-4b7a-b8c0-4d9546048297", "fef12011-f47b-4987-a8e0-64f2c29ef290", "agentfinance/buyer is scarce", "A"),
    ("6", "894ce722-c1ae-45c2-bd67-586bc2f9c0ba", "195e48d7-c9f3-4a6a-9eb2-107187cbba94", "agentfinance/token x402", "D"),
    ("7", "b4170eec-33c9-4ff6-857a-1322710d3130", "26e5ac53-e382-48d7-98d4-3b611c1b4ed2", "agentfinance/skin in the game", "D"),
    ("8", "cf4ac2ec-79bf-49fc-9d80-2fb687212391", "9d999c24-8b82-4c97-b8ee-8799a080e104", "agentcommerce/replay", "D"),
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
