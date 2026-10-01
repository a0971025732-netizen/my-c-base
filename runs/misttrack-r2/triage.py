import json, pathlib
pool = json.load(open(pathlib.Path(__file__).parent / "mb_pool.json"))
HIST = pathlib.Path(__file__).parent.parent.parent / "history.jsonl"
used_posts, used_authors = set(), set()
for line in HIST.read_text().splitlines():
    r = json.loads(line)
    if r.get("post_id"): used_posts.add(r["post_id"])
    if r.get("author"): used_authors.add(r["author"])

POS = ["scam","scammed","stolen","drain","drained","drainer","phish","phishing","hack","hacked","exploit",
"trace","traced","tracing","tainted","address risk","risk score","aml","kyc","source of funds","sanction",
"sanctioned","blocklist","blacklist","mixer","tornado","bridge","launder","laundering","rug","rug pull",
"liquidity","fund flow","funds went","follow the money","counterparty","on-chain investigation","forensic",
"illicit","dirty","frozen","freeze","froze","recover","stolen funds","compliance","provenance","victim",
"wallet","transaction hash","tx hash","attacker","hacker","reimburse","chargeback","fraud","fake token","honeypot"]
NEG = ["price predict","should i buy","should i sell","buy or sell","to the moon","pump","when moon",
"price target","technical analysis","entry point","good investment","best coin to buy","airdrop farm"]
# security/tracing relevance is stronger than generic wallet talk; require a core signal
CORE = ["scam","stolen","drain","phish","hack","exploit","trace","tainted","aml","sanction","mixer","launder",
"rug","fund flow","follow the money","forensic","illicit","fraud","victim","froze","frozen","recover","attacker","honeypot"]

def feats(p):
    t = ((p.get("title") or "") + " " + (p.get("content") or "")).lower()
    return sum(1 for k in POS if k in t), sum(1 for k in NEG if k in t), sum(1 for k in CORE if k in t), t

rows = []
for p in pool:
    if p["id"] in used_posts or (p.get("author") or "") in used_authors: continue
    if (p.get("age_h") or 999) > 24 or (p.get("cc") or 0) > 200: continue
    pos, neg, core, t = feats(p)
    if core < 1 or pos < 2: continue
    active = 1 if (p.get("cc") or 0) >= 2 else 0
    sc = pos + core * 2 - neg * 3 + active
    rows.append((sc, pos, core, active, p))
rows.sort(key=lambda r: (-r[0], r[4].get("age_h") or 999))
print("candidates:", len(rows))
for rank, (sc, pos, core, active, p) in enumerate(rows[:34]):
    print(f"\n[{rank}] sc={sc} pos={pos} core={core} act={active} sub={p.get('submolt')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')} by={p.get('author')} id={p['id']}")
    print("   ", (p.get('title') or '')[:135])
