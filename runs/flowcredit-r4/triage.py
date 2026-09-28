import json, pathlib

pool = json.load(open(pathlib.Path(__file__).parent / "mb_pool.json"))
HIST = pathlib.Path(__file__).parent.parent.parent / "history.jsonl"

used_posts, used_authors = set(), set()
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
# r3 finding: down-rank token-rant / crypto-sovereignty archetypes (engage but hostile to evidence framing)
ARCH_BAD = ["your token is a scam","utility token is a tax","x402 makes it obsolete","x402 proves you don't need",
"sovereignty is the only","don't trust, verify","privacy is the only","surveillance","cypherpunk",
"multisig in a trenchcoat","shitcoin","bag-holder"]
# r3 finding: prefer operations-evidence builders / ledger publishers
ARCH_GOOD = ["ledger","settled","published","our numbers","repayment","invoice","reconcile","provenance",
"real revenue","external buyer","external payer","five-field","audit","evidence","attributable"]

def feats(p):
    t = ((p.get("title") or "") + " " + (p.get("content") or "")).lower()
    return (sum(1 for k in POS if k in t), sum(1 for k in NEG if k in t),
            sum(1 for k in ARCH_BAD if k in t), sum(1 for k in ARCH_GOOD if k in t), t)

rows = []
for p in pool:
    if p["id"] in used_posts or (p.get("author") or "") in used_authors: continue
    if (p.get("age_h") or 999) > 24 or (p.get("cc") or 0) > 200: continue
    pos, neg, bad, good, t = feats(p)
    if pos < 2: continue
    # active-OP proxy: has some comments (thread alive) and reasonably fresh
    active = 1 if (p.get("cc") or 0) >= 2 else 0
    sc = pos - neg * 3 - bad * 4 + good * 1 + active
    rows.append((sc, pos, neg, bad, good, active, p))
rows.sort(key=lambda r: (-r[0], r[6].get("age_h") or 999))
print("candidates:", len(rows))
for rank, (sc, pos, neg, bad, good, active, p) in enumerate(rows[:26]):
    tag = " BAD-ARCH" if bad else (" builder" if good >= 2 else "")
    print(f"\n[{rank}] sc={sc} pos={pos} bad={bad} good={good} active={active}{tag} sub={p.get('submolt')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')} by={p.get('author')} id={p['id']}")
    print("   ", (p.get('title') or '')[:135])
