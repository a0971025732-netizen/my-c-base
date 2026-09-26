import json
pool=json.load(open("mb_pool.json"))
POS=["revenue","real yield","emission","onchain","on-chain","usage","traction","due diligence","diligence","verify","verifiable","fake","wash trad","inflat","metric","fundamental","depin","compute","counterparty","risk score","black box","explainable","token utility","real demand","grant","screen applic","proof of","provenance","credibility","legit","scam","rug","audit","transparen","settle","ledger","payer","customer","evidence","vet","assess","trust signal","real user","active user"]
from collections import Counter
c=Counter()
rows=[]
for p in pool:
    if (p.get("age_h") or 999)>24: continue
    t=((p.get("title") or "")+" "+(p.get("content") or "")).lower()
    pos=sum(1 for k in POS if k in t)
    if pos==0: continue
    c[p.get("submolt")]+=1
    if p.get("submolt") not in ("crypto","agentfinance","finance"):
        rows.append((pos,p))
print("fresh-relevant by submolt:",dict(c))
print("\n--- non crypto/agentfinance/finance candidates ---")
rows.sort(key=lambda r:-r[0])
for pos,p in rows[:15]:
    print(f"\npos={pos} sub={p.get('submolt')} by={p.get('author')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')} id={p['id']}")
    print(" T:",(p.get('title') or '')[:120])
    print(" C:",(p.get('content') or '')[:220])
