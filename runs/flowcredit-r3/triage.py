import json, re, pathlib

pool = json.load(open(pathlib.Path(__file__).parent / "mb_pool.json"))
HIST = pathlib.Path(__file__).parent.parent.parent / "history.jsonl"

# exclude posts/authors already used (7-day rule) + the r2 leftovers being published this batch
used_posts = {"9caabb3b-3d7a-4955-89b6-aa959809f6f2", "fa9f0bf8-3941-4607-be16-271a5f6e9195",
              "fe648738-f3d5-466d-a075-a354d8d2fe4a", "b14a2e8b-541e-44c1-a789-1bdf5ad98a8c",
              "3c550b91-d248-4229-9936-8f5b454fb4a0", "f2e28fa6-eb53-489d-a323-7379b658328f"}
used_authors = {"noah_ilands", "kairos_signal_ai", "ttooribot", "creditclaw", "clawdsmith", "bitroadai"}
for line in HIST.read_text().splitlines():
    r = json.loads(line)
    if r.get("post_id"): used_posts.add(r["post_id"])
    if r.get("author"): used_authors.add(r["author"])

POS = ["revenue","real yield","emission","onchain","on-chain","usage","traction","due diligence","diligence",
"verify","verifiable","fake","wash trad","inflat","metric","fundamental","depin","compute","counterparty",
"risk score","black box","explainable","token utility","real demand","grant","screen applic","proof of",
"provenance","credibility","legit","scam","rug","audit","transparen","settle","ledger","payer","customer",
"evidence","vetting","assess","trust signal","bot traffic","real user","active user","reconcil","attest",
"underwrit","repayment","chargeback","finality","invoice","dispute","x402","agent payment","agent commerce"]
NEG = ["price predict","should i buy","should i sell","buy or sell","to the moon","pump","when moon",
"price target","technical analysis","entry point","good investment","worth buying","airdrop farm","best coin to buy"]

def score(p):
    t = ((p.get("title") or "") + " " + (p.get("content") or "")).lower()
    pos = sum(1 for k in POS if k in t)
    neg = sum(1 for k in NEG if k in t)
    return pos, neg, t

rows = []
for p in pool:
    if p["id"] in used_posts: continue
    if (p.get("author") or "") in used_authors: continue
    if (p.get("age_h") or 999) > 24: continue
    if (p.get("cc") or 0) > 200: continue
    pos, neg, t = score(p)
    if pos < 2: continue
    rows.append((pos - neg * 3, pos, neg, p))
rows.sort(key=lambda r: (-r[0], r[3].get("age_h") or 999))
print("candidates:", len(rows))
for rank, (sc, pos, neg, p) in enumerate(rows[:28]):
    print(f"\n[{rank}] score={sc} pos={pos} neg={neg} sub={p.get('submolt')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')} id={p['id']}")
    print("  TITLE:", (p.get('title') or '')[:140])
    print("  BY:", p.get('author'))
