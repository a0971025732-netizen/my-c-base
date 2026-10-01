import json, urllib.request, urllib.parse, datetime as dt, time
B = "https://www.moltbook.com/api/v1"
def get(path):
    for i in range(3):
        try:
            with urllib.request.urlopen(B + path, timeout=25) as r: return json.load(r)
        except Exception: time.sleep(2)
    return {}
now = dt.datetime.now(dt.timezone.utc); posts = {}
def add(p, src):
    if not p or "id" not in p: return
    t = dt.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")); age = (now - t).total_seconds() / 3600
    posts.setdefault(p["id"], {"id": p["id"], "title": p.get("title"), "content": (p.get("content") or "")[:500],
        "submolt": (p.get("submolt") or {}).get("name") if isinstance(p.get("submolt"), dict) else p.get("submolt"),
        "author": (p.get("author") or {}).get("name"), "cc": p.get("comment_count"), "age_h": round(age, 1)})
subs = ["crypto","defi","agentfinance","agenteconomy","agentcommerce","web3","blockchain","onchain","investing","realestate","rwa","tokenization"]
for s in subs:
    cur = None
    for pg in range(3):
        d = get(f"/posts?submolt={s}&sort=new&limit=50" + (f"&cursor={urllib.parse.quote(cur)}" if cur else ""))
        ps = d.get("posts") or []
        for p in ps: add(p, s)
        cur = d.get("next_cursor")
        if not ps or not cur: break
for q in ["tokenized real estate","real world assets RWA onchain","RWA valuation underlying data","vertical AI agent domain",
          "agents need proprietary data moat","agent grounding real data hallucination","property tokenization",
          "onchain real estate deed","singapore real estate onchain","structured market data agent"]:
    for p in (get("/search?" + urllib.parse.urlencode({"q": q, "type": "posts", "limit": 30})).get("results") or []): add(p, "q")
out = list(posts.values())
json.dump(out, open("edge_pool.json", "w"), indent=1, default=str)
def t(p): return ((p.get("title") or "") + " " + (p.get("content") or "")).lower()
EDGE = {
 "RWA/tokenized-RE": ["tokeniz","real world asset","rwa","real-world asset","onchain real estate","property token","tokenized property","deed","fractional"],
 "vertical/data-agent": ["vertical agent","domain agent","proprietary data","data moat","grounded","grounding","hallucinat","structured data","niche agent","specialized agent","real data"],
 "RE-direct": ["real estate","property market","condo","rental yield","housing market","landlord","mortgage","reit"],
}
for label, kws in EDGE.items():
    hits = [p for p in out if any(k in t(p) for k in kws)]
    fresh = [p for p in hits if (p.get("age_h") or 9e9) <= 48]
    print(f"== {label}: total {len(hits)}, fresh<=48h {len(fresh)} ==")
    for p in sorted(fresh, key=lambda x: x.get("age_h") or 9e9)[:8]:
        print(f"   age={p.get('age_h')}h cc={p.get('cc')} sub={p.get('submolt')} by={p.get('author')} :: {(p.get('title') or '')[:76]}")
