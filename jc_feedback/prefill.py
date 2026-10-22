import urllib.parse


def prefilled_url(cfg, state, title, date):
    # Pre-filling the date makes the QR denser; it can be turned off in config.
    values = {"title": title, "date": date.isoformat() if cfg["print"]["prefill_date"] else None}
    params = {
        state[q["key"]]["entry"]: values[q["prefill"]]
        for q in cfg["questions"]
        if q.get("prefill") and values[q["prefill"]] and q["key"] in state
    }
    return cfg["form"]["responder_url"] + "?" + urllib.parse.urlencode(params)
