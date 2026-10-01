import json, os, sys, pathlib, urllib.request, urllib.error, datetime as dt

B = "https://www.moltbook.com/api/v1"
HIST = pathlib.Path(__file__).parent.parent.parent / "history.jsonl"
ROUND = sys.argv[1] if len(sys.argv) > 1 else "misttrack-r1"
rows = [json.loads(l) for l in HIST.read_text().splitlines() if json.loads(l).get("round") == ROUND]

def call(path):
    h = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"): h["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    req = urllib.request.Request(B + path, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {}

def flatten(cs):
    out = []
    for c in cs or []:
        out.append(c); out.extend(flatten(c.get("replies")))
    return out

print(f"{ROUND} snapshot @ {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
alive = reps = 0
for r in rows:
    pid = r["post_id"]; cid = r["comment_url"].split("#comment-")[1]
    d = call(f"/posts/{pid}/comments")
    cs = d.get("comments") or d.get("data") or (d if isinstance(d, list) else [])
    mine = next((c for c in flatten(cs if isinstance(cs, list) else []) if c.get("id") == cid), None)
    if not mine:
        print(f"#{r['batch_no']:>2} [{r['community']}/{r['author']}] NOT FOUND"); continue
    if not mine.get("is_deleted") and not mine.get("is_spam"): alive += 1
    rl = mine.get("replies") or []
    if rl: reps += 1
    print(f"#{r['batch_no']:>2} [{r['community']}/{r['author']}] up={mine.get('upvotes')} replies={mine.get('reply_count')} spam={mine.get('is_spam')} deleted={mine.get('is_deleted')} vstatus={mine.get('verification_status')}")
    for rep in rl:
        by = (rep.get('author') or {}).get('name') if isinstance(rep.get('author'), dict) else rep.get('author')
        print(f"      REPLY by {by}: {(rep.get('content') or '')[:200]}")
print(f"\nalive {alive}/{len(rows)} · got-reply {reps}/{len(rows)}")
