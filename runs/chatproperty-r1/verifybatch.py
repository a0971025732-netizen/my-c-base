import json, os, sys, pathlib, datetime as dt, urllib.request, urllib.error

B = "https://www.moltbook.com/api/v1"
HERE = pathlib.Path(__file__).parent
HISTORY = HERE.parent.parent / "history.jsonl"
UTM = "utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_chatproperty_v1"
manifest = {m["idx"]: m for m in json.load(open(HERE / "manifest.json"))}
STATE = HERE / "state.json"
state = json.load(open(STATE))

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"): h["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    req = urllib.request.Request(B + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")

# args: idx=answer  e.g. 1=40.00 2=16.00
for arg in sys.argv[1:]:
    idx, ans = arg.split("=")
    st = state[idx]; m = manifest[int(idx)]
    s, d = call("POST", "/verify", {"verification_code": st["code"], "answer": ans})
    if not d.get("success"):
        print(f"#{idx} VERIFY FAIL ({s}): {d.get('message')} / {d.get('hint','')}")
        continue
    row = {
        "post_url": f"https://www.moltbook.com/post/{st['post_id']}",
        "comment_url": f"https://www.moltbook.com/post/{st['post_id']}#comment-{st['comment_id']}",
        "platform": "moltbook", "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "utm": UTM, "agent": "chatproperty", "round": "chatproperty-r1", "batch_no": int(idx),
        "community": m["community"], "author": m["author"], "post_id": st["post_id"],
        "topic": m["topic"], "mode": m["mode"], "lang": "en", "score": m["score"], "self_eval": 22,
        "summary": m["summary"], "verified": True,
    }
    with HISTORY.open("a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    st["status"] = "verified"; json.dump(state, open(STATE, "w"), indent=1)
    print(f"#{idx} VERIFIED + logged ({m['author']})")
