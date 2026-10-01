import json, urllib.request, urllib.parse, datetime as dt, time
B="https://www.moltbook.com/api/v1"
def get(path):
    for i in range(3):
        try:
            with urllib.request.urlopen(B+path, timeout=25) as r: return json.load(r)
        except Exception as e: err=e; time.sleep(2)
    return {}
now=dt.datetime.now(dt.timezone.utc); posts={}
def add(p, src):
    if not p or "id" not in p: return
    t=dt.datetime.fromisoformat(p["created_at"].replace("Z","+00:00"))
    age=(now-t).total_seconds()/3600
    q=posts.setdefault(p["id"],{"id":p["id"],"title":p.get("title"),"content":(p.get("content") or "")[:600],
      "submolt":(p.get("submolt") or {}).get("name") if isinstance(p.get("submolt"),dict) else p.get("submolt"),
      "author":(p.get("author") or {}).get("name"),"up":p.get("upvotes"),"cc":p.get("comment_count"),"age_h":round(age,1),"src":set()})
    q["src"].add(src)
subs=["realestate","property","singapore","investing","finance","economics","housing","realty","wealth","personalfinance","markets","asia","propertyinvesting","reits","landlord"]
for s in subs:
    cur=None
    for page in range(3):
        d=get(f"/posts?submolt={s}&sort=new&limit=50"+(f"&cursor={urllib.parse.quote(cur)}" if cur else ""))
        ps=d.get("posts") or []
        for p in ps: add(p,"sub:"+s)
        cur=d.get("next_cursor")
        if not ps or not cur: break
queries=["singapore condo price","singapore property market","rental yield singapore","private residential singapore","is this condo a good buy","district price comparison property","executive condominium EC singapore","property investment analysis","housing market trends","rent vs buy property","real estate price data","landlord rental returns"]
for q in queries:
    d=get("/search?"+urllib.parse.urlencode({"q":q,"type":"posts","limit":30}))
    for p in d.get("results") or []: add(p,"q:"+q[:28])
out=[dict(v,src=sorted(v["src"])) for v in posts.values()]
json.dump(out,open("mb_pool.json","w"),indent=1,default=str)
# property-relevance quick count
KW=["real estate","real-estate","property","propert","condo","apartment","rental","rent ","renting","landlord","mortgage","reit","housing","home price","house price","square foot","psf","district","singapore","hdb","residential","yield","tenant","lease"]
rel=[p for p in out if any(k in ((p.get('title') or '')+' '+(p.get('content') or '')).lower() for k in KW)]
sg=[p for p in rel if 'singapore' in ((p.get('title') or '')+' '+(p.get('content') or '')).lower() or 'hdb' in ((p.get('title') or '')+' '+(p.get('content') or '')).lower()]
print("total",len(out),"| property-ish",len(rel),"| singapore-mention",len(sg),"| fresh<=24h",len([p for p in out if p['age_h']<=24]))
