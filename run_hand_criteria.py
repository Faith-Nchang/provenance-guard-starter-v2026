#!/usr/bin/env python3
"""
Criteria 4 (appeal path) and 5 (bad input), three trials each.

    python app.py                                   # one terminal
    python run_hand_criteria.py --label before      # another

run_eval.py can only send dict bodies via requests' json=, so it can't send
malformed JSON or a JSON list, and it can't chain submit -> appeal. This does
both. Same output convention: real responses are saved to results/.

Unlike run_eval.py this one DOES decide pass/fail per trial, using the exact
wording of criteria.md #4 and #5. What it cannot observe is whether a signal was
invoked on a rejected request; it infers that from "no decision entry, no scores
in the response".
"""

import argparse
import datetime as dt
import json
import sys
import uuid

import requests

import config

DEFAULT_URL = f"http://{config.HOST}:{config.PORT}"

VALID_TEXT = (
    "The market opened early that Saturday, and I walked the whole row twice "
    "before buying anything. The peaches were soft and a little bruised, which "
    "my aunt always said was how you knew they were good."
)


def log_entries(url):
    return requests.get(f"{url}/log", timeout=30).json()["entries"]


def decisions_count(url):
    return sum(1 for e in log_entries(url) if e.get("event") is None)


def bad_requests(run_id):
    """(name, kwargs for requests.post) for the nine invalid requests."""
    json_hdr = {"Content-Type": "application/json"}
    cid = lambda s: f"hand_bad_{s}_{run_id}"  # noqa: E731
    return [
        ("missing text", dict(json={"creator_id": cid("missing")})),
        ("empty text", dict(json={"text": "", "creator_id": cid("empty")})),
        ("whitespace-only text", dict(json={"text": "   \n\t ", "creator_id": cid("ws")})),
        ("null text", dict(json={"text": None, "creator_id": cid("null")})),
        ("numeric text", dict(json={"text": 12345, "creator_id": cid("num")})),
        ("text of 10,001 characters", dict(json={"text": "a" * 10_001, "creator_id": cid("long")})),
        ("missing creator_id", dict(json={"text": VALID_TEXT})),
        ("JSON list instead of object", dict(json=[VALID_TEXT, "x"])),
        ("malformed JSON", dict(data='{"text": "oops", "creator_id": ', headers=json_hdr)),
    ]


def trial_bad_input(url, run_id):
    before = decisions_count(url)
    results = []
    for name, kwargs in bad_requests(run_id):
        r = requests.post(f"{url}/submit", timeout=60, **kwargs)
        try:
            body = r.json()
            is_json = True
        except ValueError:
            body, is_json = r.text[:200], False
        ok = (
            r.status_code == 400
            and is_json
            and isinstance(body, dict)
            and bool(body.get("error"))
            and bool(body.get("message"))
            and body.get("model_score") is None
            and body.get("style_score") is None
        )
        results.append({"case": name, "status": r.status_code, "body": body, "pass": ok})
    new_decisions = decisions_count(url) - before
    passed = sum(r["pass"] for r in results)
    return {
        "passed": passed,
        "of": len(results),
        "new_decision_entries": new_decisions,
        "trial_pass": passed == len(results) and new_decisions == 0,
        "results": results,
    }


def trial_appeal(url, run_id):
    results = []
    for i in range(1, 6):
        s = requests.post(f"{url}/submit", timeout=90, json={
            "text": VALID_TEXT + f" Visit number {i}, with a detail that is different each time.",
            "creator_id": f"hand_appeal_{run_id}_{i}"})
        sub = s.json()
        cid = sub.get("content_id")
        reasoning = f"I wrote this myself (appeal {i})."
        a = requests.post(f"{url}/appeal", timeout=30,
                          json={"content_id": cid, "reasoning": reasoning})
        entries = [e for e in log_entries(url) if e.get("content_id") == cid]
        original = [e for e in entries if e.get("event") is None]
        appeals = [e for e in entries if e.get("event") == "appeal"]
        ok = (
            s.status_code == 200 and a.status_code == 200
            and a.json().get("status") == "under_review"
            and len(original) == 1 and original[0].get("status") == "decided"
            and any(e.get("reasoning") == reasoning and e.get("status") == "under_review"
                    for e in appeals)
        )
        results.append({"submit_status": s.status_code, "content_id": cid,
                        "appeal_status": a.status_code, "appeal_body": a.json(),
                        "original_entries": len(original), "appeal_entries": len(appeals),
                        "pass": ok})

    ghost = str(uuid.uuid4())
    g = requests.post(f"{url}/appeal", timeout=30,
                      json={"content_id": ghost, "reasoning": "no such item"})
    ghost_entries = [e for e in log_entries(url) if e.get("content_id") == ghost]
    unknown_ok = g.status_code == 404 and not ghost_entries
    passed = sum(r["pass"] for r in results)
    return {
        "passed": passed, "of": 5,
        "unknown_id": {"status": g.status_code, "body": g.json(),
                       "entries_created": len(ghost_entries), "pass": unknown_ok},
        "trial_pass": passed == 5 and unknown_ok,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--label", default="")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    try:
        requests.get(f"{args.url}/health", timeout=5)
    except Exception:  # noqa: BLE001
        print(f"Nothing answering at {args.url}. Start it:  python app.py", file=sys.stderr)
        sys.exit(1)

    out = {"criterion_4_appeal_path": [], "criterion_5_bad_input": []}
    for t in range(1, args.trials + 1):
        run_id = f"{dt.datetime.now().strftime('%H%M%S')}t{t}"
        c4 = trial_appeal(args.url, run_id)
        c5 = trial_bad_input(args.url, run_id)
        out["criterion_4_appeal_path"].append(c4)
        out["criterion_5_bad_input"].append(c5)
        print(f"trial {t}:  appeal {c4['passed']}/5 "
              f"(unknown id -> {c4['unknown_id']['status']})   "
              f"bad input {c5['passed']}/{c5['of']} "
              f"(new decision entries: {c5['new_decision_entries']})")

    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"hand_criteria_{stamp}{label}.md"
    lines = [f"# Criteria 4 and 5{f' — {args.label}' if args.label else ''}", "",
             "- Produced by: `run_hand_criteria.py::main`", ""]
    for name, trials in out.items():
        lines += [f"## {name}", ""]
        for i, tr in enumerate(trials, 1):
            lines += [f"**Trial {i}** — trial_pass: {tr['trial_pass']}", "", "```json",
                      json.dumps(tr, indent=2), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
