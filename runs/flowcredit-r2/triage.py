import json,re
pool=json.load(open("mb_pool.json"))
USED_POST="9caabb3b-3d7a-4955-89b6-aa959809f6f2"
# relevance keywords (positive) from profile
POS=["revenue","real yield","emission","onchain","on-chain","usage","traction","due diligence","dd ","diligence","verify","verifiable","fake","wash trad","inflat","metric","fundamental","depin","compute","counterparty","risk score","black box","explainable","token utility","real demand","grant","screen applic","proof of","provenance","credibility","legit","scam","rug","audit","transparen","settle","ledger","payer","customer","evidence","vet ","vetting","assess","trust signal","bot traffic","real user","active user"]
# not_for / disqualify: pure price/buy-sell/investment
NEG=["price predict","should i buy","should i sell","buy or sell","to the moon","pump","when moon","price target","ta ","technical analysis","entry point","good investment","worth buying","airdrop farm","best coin to buy"]
def score(p):
    t=((p.get("title") or "")+" "+(p.get("content") or "")).lower()
    pos=sum(1 for k in POS if k in t)
    neg=sum(1 for k in NEG if k in t)
    return pos,neg,t
rows=[]
for p in pool:
    if p["id"]==USED_POST: continue
    if (p.get("age_h") or 999)>24: continue
    if (p.get("cc") or 0)>200: continue
    pos,neg,t=score(p)
    if pos==0: continue
    rows.append((pos-neg*3,pos,neg,p))
rows.sort(key=lambda r:-r[0])
print("candidates with relevance:",len(rows))
for rank,(sc,pos,neg,p) in enumerate(rows[:25]):
    print(f"\n[{rank}] score={sc} pos={pos} neg={neg} sub={p.get('submolt')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')} id={p['id']}")
    print("  TITLE:",(p.get('title') or '')[:130])
    print("  BY:",p.get('author'))
