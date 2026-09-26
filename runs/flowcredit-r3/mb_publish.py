"""Publish one approved Moltbook comment (STEP 7).

usage:
  python mb_publish.py check  <post_id>                  # post still up and unlocked?
  python mb_publish.py post   <post_id> <comment_file>   # create comment, prints verification challenge
  python mb_publish.py verify <verification_code> <answer>
  python mb_publish.py log    <post_id> <comment_id> <review_no>  # append to history.jsonl

Auth: MOLTBOOK_API_KEY from the environment if set, otherwise whatever the agent proxy injects.
"""
import json, os, sys, datetime as dt, urllib.request, urllib.error, pathlib

B = "https://www.moltbook.com/api/v1"
HERE = pathlib.Path(__file__).parent
HISTORY = HERE.parent.parent / "history.jsonl"
UTM = "utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_flowcredit_v1"
AGENT_URL = "https://www.finchtech.ai/market/chips/agent-e96e9a01-50aa-4686-bd0e-1aa9cdfcf967/run?" + UTM


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if os.environ.get("MOLTBOOK_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["MOLTBOOK_API_KEY"]
    req = urllib.request.Request(B + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    cmd, *a = sys.argv[1:]
    if cmd == "check":
        s, d = call("GET", f"/posts/{a[0]}")
        p = d.get("post", d)
        print(s, {k: p.get(k) for k in ("title", "is_locked", "is_deleted", "upvotes", "comment_count", "created_at")})
    elif cmd == "post":
        text = pathlib.Path(a[1]).read_text().strip()
        assert text.count(AGENT_URL) == 1, "comment must contain the agent URL exactly once"
        s, d = call("POST", f"/posts/{a[0]}/comments", {"content": text})
        print(s, json.dumps(d, indent=1))
    elif cmd == "verify":
        s, d = call("POST", "/verify", {"verification_code": a[0], "answer": a[1]})
        print(s, json.dumps(d, indent=1))
    elif cmd == "log":
        post_id, comment_id, no = a
        review = json.loads((HERE / "approved.json").read_text())[no]
        row = {
            "post_url": f"https://www.moltbook.com/post/{post_id}",
            "comment_url": f"https://www.moltbook.com/post/{post_id}#comment-{comment_id}",
            "platform": "moltbook", "posted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "utm": UTM, "agent": "flowcredit", "round": "flowcredit-r1", "review_no": int(no), **review,
        }
        with HISTORY.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print("logged", row["comment_url"])


if __name__ == "__main__":
    main()
