import json, os, sys, pathlib, urllib.request, urllib.error

B = "https://www.moltbook.com/api/v1"
HERE = pathlib.Path(__file__).parent
UTM = "utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_chatproperty_v1"
AGENT_URL = "https://www.finchtech.ai/market/chips/agent-b3316156-4cab-47ba-8101-b07dc0266f14/run?" + UTM
manifest = {m["idx"]: m for m in json.load(open(HERE / "manifest.json"))}
STATE = HERE / "state.json"
state = json.load(open(STATE)) if STATE.exists() else {}

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"): h["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    req = urllib.request.Request(B + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")

start, end = int(sys.argv[1]), int(sys.argv[2])
for idx in range(start, end + 1):
    m = manifest[idx]
    text = (HERE / m["draft"]).read_text().strip()
    assert text.count(AGENT_URL) == 1, f"idx {idx}: URL count != 1"
    s, d = call("GET", f"/posts/{m['post_id']}")
    p = d.get("post", d)
    if p.get("is_locked") or p.get("is_deleted"):
        print(f"#{idx} SKIP post locked/deleted"); continue
    s, d = call("POST", f"/posts/{m['post_id']}/comments", {"content": text})
    if s != 201:
        print(f"#{idx} POST FAIL {s} {json.dumps(d)[:200]}"); continue
    c = d["comment"]; v = c["verification"]
    state[str(idx)] = {"comment_id": c["id"], "code": v["verification_code"], "post_id": m["post_id"], "status": "posted"}
    json.dump(state, open(STATE, "w"), indent=1)
    print(f"#{idx} comment_id={c['id']}")
    print(f"   CODE={v['verification_code']}")
    print(f"   CHALLENGE: {v['challenge_text']}")
    print(f"   EXPIRES {v['expires_at']}")
