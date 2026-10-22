from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from jc_feedback.config import ROOT

SCOPES = ["https://www.googleapis.com/auth/forms.body"]
TOKEN = ROOT / "token.json"
CREDENTIALS = ROOT / "credentials.json"
KIND_FIELD = {"text": "textQuestion", "paragraph": "textQuestion", "date": "dateQuestion", "scale": "scaleQuestion"}


def forms_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        creds = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return build("forms", "v1", credentials=creds)


def question_body(q, scale):
    kind = q["kind"]
    if kind == "scale":
        return {"scaleQuestion": {"low": scale["low"], "high": scale["high"],
                                  "lowLabel": scale["low_label"], "highLabel": scale["high_label"]}}
    if kind == "date":
        return {"dateQuestion": {"includeYear": True}}
    return {"textQuestion": {"paragraph": kind == "paragraph"}}


def item_body(q, scale, existing=None):
    question = question_body(q, scale) | {"required": bool(q.get("required", False))}
    if existing:
        question["questionId"] = existing["questionItem"]["question"]["questionId"]
    item = {"title": q["title"], "questionItem": {"question": question}}
    if existing:
        item["itemId"] = existing["itemId"]
    return item


def comparable(item):
    question = item.get("questionItem", {}).get("question", {})
    field = next((f for f in KIND_FIELD.values() if f in question), None)
    body = dict(question.get(field) or {})
    # The API omits default values; fill them so a no-op edit is not reported as a change.
    if field == "textQuestion":
        body.setdefault("paragraph", False)
    if field == "dateQuestion":
        body.setdefault("includeYear", False)
    return item.get("title"), field, body, bool(question.get("required", False))


def match_items(form, cfg, state):
    items = {it["itemId"]: it for it in form.get("items", [])}
    taken, ids = set(), {}
    for q in cfg["questions"]:
        iid = (state.get(q["key"]) or {}).get("item_id")
        if iid not in items:
            # First sync: adopt an existing question with the same title.
            iid = next((i for i, it in items.items() if it.get("title") == q["title"] and i not in taken), None)
        if iid:
            ids[q["key"]], taken = iid, taken | {iid}
    return items, ids


def plan(form, cfg, state):
    """Return (requests, human-readable changes) that make the form match config."""
    scale = cfg["scale"]
    items, ids = match_items(form, cfg, state)
    order = [it["itemId"] for it in form.get("items", [])]
    requests, changes = [], []

    info = form.get("info", {})
    want = cfg["form"]
    if (info.get("title"), info.get("description", "")) != (want["title"], want["description"]):
        requests.append({"updateFormInfo": {"info": {"title": want["title"], "description": want["description"]},
                                            "updateMask": "title,description"}})
        changes.append("form title/description")

    if form.get("settings", {}).get("emailCollectionType", "DO_NOT_COLLECT") != "DO_NOT_COLLECT":
        requests.append({"updateSettings": {"settings": {"emailCollectionType": "DO_NOT_COLLECT"},
                                            "updateMask": "emailCollectionType"}})
        changes.append("email collection -> Do not collect")

    keep = set(ids.values())
    for idx in reversed(range(len(order))):
        if order[idx] not in keep:
            requests.append({"deleteItem": {"location": {"index": idx}}})
            changes.append(f"DELETE '{items[order[idx]].get('title')}'")
    order = [i for i in order if i in keep]

    for idx, q in enumerate(cfg["questions"]):
        iid = ids.get(q["key"])
        if iid is None:
            requests.append({"createItem": {"item": item_body(q, scale), "location": {"index": idx}}})
            order.insert(idx, f"new:{q['key']}")
            changes.append(f"ADD '{q['title']}' at {idx + 1}")
            continue
        here = order.index(iid)
        if here != idx:
            requests.append({"moveItem": {"originalLocation": {"index": here}, "newLocation": {"index": idx}}})
            order.insert(idx, order.pop(here))
            changes.append(f"MOVE '{q['title']}' to {idx + 1}")
        new = item_body(q, scale, items[iid])
        if comparable(items[iid]) != comparable(new):
            field = KIND_FIELD[q["kind"]]
            requests.append({"updateItem": {"item": new, "location": {"index": idx},
                                            "updateMask": f"title,questionItem.question.{field},questionItem.question.required"}})
            changes.append(f"UPDATE '{items[iid].get('title')}' -> '{q['title']}'")
    return requests, changes


def state_from_form(form, cfg, state):
    items, ids = match_items(form, cfg, state)
    keys = {q["key"] for q in cfg["questions"]}
    out = {k: v for k, v in state.items() if k in keys}
    for q in [q for q in cfg["questions"] if q["key"] in ids]:
        qid = items[ids[q["key"]]]["questionItem"]["question"]["questionId"]
        # Pre-fill links use the question ID written in decimal.
        out[q["key"]] = {"item_id": ids[q["key"]], "question_id": qid, "entry": f"entry.{int(qid, 16)}"}
    return out


def sync(cfg, state, dry_run=False, yes=False):
    service = forms_service()
    form_id = cfg["form"]["id"]
    form = service.forms().get(formId=form_id).execute()
    requests, changes = plan(form, cfg, state)
    print("\n".join(f"  {c}" for c in changes) or "  Google Form already matches config.yaml")
    if requests and not dry_run and (yes or input("Apply these changes? [y/N] ").lower() == "y"):
        service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
        form = service.forms().get(formId=form_id).execute()
        print("Applied.")
    return state_from_form(form, cfg, state)
