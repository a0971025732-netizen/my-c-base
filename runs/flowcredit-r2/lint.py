import re,pathlib
URL='https://www.finchtech.ai/market/chips/agent-e96e9a01-50aa-4686-bd0e-1aa9cdfcf967/run?utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_flowcredit_v1'
BANNED=["game-changer","game changer","revolutionary","check out","must-try","must try"]
for n in range(1,6):
    t=pathlib.Path(f"draft_{n}.txt").read_text().strip()
    words=len(t.split())
    urlc=t.count(URL)
    first=t.split(".")[0]
    prod_in_first=("flowcredit" in first.lower()) or ("finch" in first.lower())
    banned=[b for b in BANNED if b in t.lower()]
    allcaps=re.findall(r'\b[A-Z]{4,}\b',t)
    emoji2=bool(re.search(r'[\U0001F300-\U0001FAFF]{2,}',t))
    print(f"#{n}: words={words} url_count={urlc} prod_in_1st={prod_in_first} banned={banned} allcaps={allcaps} emoji2={emoji2}")
