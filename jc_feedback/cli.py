import argparse
import csv
import datetime as dt

from jc_feedback.config import ROOT, load_config, load_state, save_state
from jc_feedback.prefill import prefilled_url
from jc_feedback.render import make_pdf, make_png


def cmd_make(args):
    cfg, state = load_config(), load_state()
    date = dt.date.fromisoformat(args.date)
    title = " ".join(args.title.split())
    url = prefilled_url(cfg, state, title, date)

    out = ROOT / "out" / date.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    make_pdf(out / f"JC_feedback_{date}.pdf", cfg, url, title, date.strftime("%d %b %Y"))
    make_png(out / f"JC_QR_{date}.png", url)
    (out / f"JC_link_{date}.txt").write_text(url + "\n")

    log = ROOT / "sessions.csv"
    new = not log.exists()
    with log.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "paper_title", "prefilled_link"])
        w.writerow([date.isoformat(), title, url])
    print(f"Wrote {out}\n{url}")


def cmd_sync(args):
    # Imported here so `jc make` works before Google API credentials are set up.
    from jc_feedback.sync import sync

    state = sync(load_config(), load_state(), dry_run=args.dry_run, yes=args.yes)
    save_state(state)
    print("form_state.json updated.")


def cmd_check(args):
    from jc_feedback.check import check

    print("Config and Google Form match." if check(load_config(), load_state())
          else "Mismatch: run `uv run jc sync`.")


def run():
    ap = argparse.ArgumentParser(prog="jc", description="GW journal club feedback kit")
    sub = ap.add_subparsers(required=True)

    p = sub.add_parser("make", help="printable PDF + pre-filled QR for one session")
    p.add_argument("--title", required=True, help="paper title")
    p.add_argument("--date", required=True, help="JC date, YYYY-MM-DD")
    p.set_defaults(func=cmd_make)

    p = sub.add_parser("sync", help="update the Google Form to match config.yaml")
    p.add_argument("--dry-run", action="store_true", help="show changes only")
    p.add_argument("--yes", action="store_true", help="apply without asking")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("check", help="compare config.yaml with the live Google Form (no login)")
    p.set_defaults(func=cmd_check)

    args = ap.parse_args()
    args.func(args)
