import json
pool={p["id"]:p for p in json.load(open("mb_pool.json"))}
ids=["fa9f0bf8-3941-4607-be16-271a5f6e9195","1734d054-162e-4041-9c61-673ac6872bd7","b14a2e8b-541e-44c1-a789-1bdf5ad98a8c","3c550b91-d248-4229-9936-8f5b454fb4a0","b4170eec-33c9-4ff6-857a-1322710d3130","ebdeb977-d571-4434-b202-21a834d4244a","fd1e7a01-8cc0-4239-b5f5-08fa4ffbad83","fe648738-f3d5-466d-a075-a354d8d2fe4a","f2e28fa6-eb53-489d-a323-7379b658328f","88f8ed8c-1931-411d-bb6d-f67dafd133a5"]
for i in ids:
    p=pool[i]
    print("="*70)
    print(f"id={i} sub={p.get('submolt')} by={p.get('author')} age={p.get('age_h')}h up={p.get('up')} cc={p.get('cc')}")
    print("TITLE:",p.get("title"))
    print("CONTENT:",p.get("content"))
    print()
