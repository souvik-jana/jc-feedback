import json
import re
import urllib.request


def live_questions(responder_url):
    """Read (title, entry) pairs from the public form page; no login needed."""
    html = urllib.request.urlopen(responder_url).read().decode()
    data = json.loads(re.search(r"FB_PUBLIC_LOAD_DATA_ = (.*?);</script>", html, re.S).group(1))
    return [(q[1], f"entry.{q[4][0][0]}") for q in data[1][1] if q[4]]


def check(cfg, state):
    live = live_questions(cfg["form"]["responder_url"])
    want = [(q["title"], (state.get(q["key"]) or {}).get("entry")) for q in cfg["questions"]]
    for i in range(max(len(live), len(want))):
        a = want[i] if i < len(want) else ("-", "-")
        b = live[i] if i < len(live) else ("-", "-")
        print(f"{'ok ' if a == b else 'DIFF'} {i + 1}. config: {a[0]} [{a[1]}]")
        if a != b:
            print(f"        form:   {b[0]} [{b[1]}]")
    return live == want
