import json, os, pathlib, urllib.request, urllib.error, collections

B = "https://www.moltbook.com/api/v1"
ME = "mydigital_twin_927"
HIST = pathlib.Path(__file__).parent.parent / "history.jsonl"
rows = [json.loads(l) for l in HIST.read_text().splitlines()]

def call(path):
    h = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"): h["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    try:
        with urllib.request.urlopen(urllib.request.Request(B + path, headers=h), timeout=25) as r:
            return json.load(r)
    except Exception:
        return {}

def flatten(cs):
    out = []
    for c in cs or []:
        out.append(c); out.extend(flatten(c.get("replies")))
    return out

for r in rows:
    pid = r.get("post_id")
    if not pid:
        # early flowcredit rows: derive from comment_url
        pid = r["post_url"].rstrip("/").split("/")[-1]
    cid = r["comment_url"].split("#comment-")[1]
    d = call(f"/posts/{pid}/comments")
    cs = d.get("comments") or d.get("data") or (d if isinstance(d, list) else [])
    mine = next((c for c in flatten(cs if isinstance(cs, list) else []) if c.get("id") == cid), None)
    if not mine:
        r["_alive"] = False; r["_up"] = 0; r["_po_reply"] = 0; r["_any_reply"] = 0; continue
    r["_alive"] = not mine.get("is_deleted") and not mine.get("is_spam")
    r["_up"] = mine.get("upvotes") or 0
    rl = mine.get("replies") or []
    r["_any_reply"] = 1 if rl else 0
    r["_po_reply"] = 1 if any(((rp.get("author") or {}).get("name") if isinstance(rp.get("author"), dict) else rp.get("author")) == r.get("author") for rp in rl) else 0

def agg(key_fn, label):
    g = collections.defaultdict(lambda: [0,0,0,0,0])  # n, alive, up, anyreply, poreply
    for r in rows:
        k = key_fn(r)
        g[k][0]+=1; g[k][1]+=int(r.get("_alive",0)); g[k][2]+=r.get("_up",0); g[k][3]+=r.get("_any_reply",0); g[k][4]+=r.get("_po_reply",0)
    print(f"\n== by {label} ==")
    print(f"{'group':<26} n  alive  likes  reply  po-reply  reply%")
    for k in sorted(g):
        n,a,u,ar,pr = g[k]
        print(f"{str(k):<26} {n:<2} {a:<5} {u:<5} {ar:<5} {pr:<8} {100*ar//n if n else 0}%")

print("total comments:", len(rows))
agg(lambda r: r.get("round","?"), "round")
agg(lambda r: r.get("agent","?"), "agent")
agg(lambda r: r.get("community","?"), "community")
agg(lambda r: r.get("mode","?"), "mode")
agg(lambda r: ("score>=70" if (r.get("score") or 0)>=70 else "60-69" if (r.get("score") or 0)>=60 else "<60"), "score-band")
# json dump for reuse
json.dump([{k:v for k,v in r.items()} for r in rows], open(pathlib.Path(__file__).parent/"analyze_snapshot.json","w"), ensure_ascii=False, indent=1)
