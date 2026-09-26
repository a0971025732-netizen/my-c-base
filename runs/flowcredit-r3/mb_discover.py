import json, urllib.request, urllib.parse, datetime as dt, time
B="https://www.moltbook.com/api/v1"
def get(path):
    for i in range(3):
        try:
            with urllib.request.urlopen(B+path, timeout=25) as r: return json.load(r)
        except Exception as e: err=e; time.sleep(2)
    print("ERR",path,err); return {}
now=dt.datetime.now(dt.timezone.utc)
posts={}
def add(p, src):
    if not p or "id" not in p: return
    t=dt.datetime.fromisoformat(p["created_at"].replace("Z","+00:00"))
    age=(now-t).total_seconds()/3600
    q=posts.setdefault(p["id"],{"id":p["id"],"title":p.get("title"),"content":(p.get("content") or "")[:600],
      "submolt":(p.get("submolt") or {}).get("name") if isinstance(p.get("submolt"),dict) else p.get("submolt"),
      "author":(p.get("author") or {}).get("name"),"up":p.get("upvotes"),"cc":p.get("comment_count"),"age_h":round(age,1),"src":set()})
    q["src"].add(src)
subs=["crypto","defi","agentfinance","trading","finance","investing","agenteconomy","agentcommerce","economics","web3","blockchain","onchain","usdc","agent-economy","agenteconomics","quantmolt","research"]
for s in subs:
    cur=None
    for page in range(4):
        d=get(f"/posts?submolt={s}&sort=new&limit=50"+(f"&cursor={urllib.parse.quote(cur)}" if cur else ""))
        ps=d.get("posts") or []
        for p in ps: add(p,"sub:"+s)
        cur=d.get("next_cursor")
        if not ps or not cur: break
        last=dt.datetime.fromisoformat(ps[-1]["created_at"].replace("Z","+00:00"))
        if (now-last).total_seconds()>36*3600: break
queries=["how do you verify a crypto project has real revenue","onchain revenue vs token emissions","due diligence on a web3 protocol partner",
"DePIN usage numbers fake or inflated","wash trading fake users inflated metrics","proving protocol traction with verifiable data",
"AI agent tokens actual usage","evaluating onchain business fundamentals framework","risk score black box explainable",
"counterparty risk evaluating agents or protocols","real yield sustainable protocol revenue","token utility real demand",
"how to assess credibility of an onchain business","compute marketplace usage verification","trust signals for agent economy businesses"]
for q in queries:
    d=get("/search?"+urllib.parse.urlencode({"q":q,"type":"posts","limit":30}))
    for p in d.get("results") or []:
        p.setdefault("submolt",p.get("submolt"))
        add(p,"q:"+q[:30])
out=[dict(v,src=sorted(v["src"])) for v in posts.values()]
json.dump(out,open("mb_pool.json","w"),indent=1,default=str)
fresh=[p for p in out if p["age_h"]<=24]
print("total",len(out),"fresh<=24h",len(fresh),"<=48h",len([p for p in out if p['age_h']<=48]))
