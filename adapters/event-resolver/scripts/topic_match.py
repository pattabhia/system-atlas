#!/usr/bin/env python3
"""
topic_match.py — correlate message producers with consumers by destination,
for the event-resolver adapter (resolve_event_target).

Usage:
  python3 topic_match.py --producers producers.json --consumers consumers.json \
          [--config resolved-config.json]

Inputs (JSON arrays):
  producers: [{"destination": "...", "ref": "Class#method", "source": "path"}]
  consumers: [{"destination": "...", "group": "...", "ref": "...", "source": "..."}]
  config (optional): {"topic.name": "orders.v1", ...}  # resolves ${placeholders}

Output: {"ok": true, "links": [...], "unmatched_producers": [...],
         "unmatched_consumers": [...], "counts": {...}}

Matching:
  1. resolve ${placeholder} destinations via config where possible;
  2. exact match on resolved destination;
  3. fan-out preserved — one destination may link to many consumers, in
     different sources/repos. Producers with no consumer, and consumers with
     no producer, are reported explicitly (both are real, actionable gaps).
"""
import argparse
import json
import re
import sys

PLACEHOLDER = re.compile(r"\$\{([^:}]+)(?::[^}]*)?\}")


def resolve(dest, config):
    if not isinstance(dest, str):
        return dest, False
    m = PLACEHOLDER.search(dest)
    if not m:
        return dest, True  # already literal
    key = m.group(1).strip()
    if key in config:
        return PLACEHOLDER.sub(config[key], dest), True
    return dest, False  # unresolved placeholder


def norm(dest):
    return dest.strip().lower() if isinstance(dest, str) else dest


def load(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--producers", required=True)
    ap.add_argument("--consumers", required=True)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    producers = load(args.producers)
    consumers = load(args.consumers)
    config = load(args.config) if args.config else {}

    # index consumers by normalized resolved destination
    cons_index = {}
    for c in consumers:
        rd, ok = resolve(c.get("destination"), config)
        c = dict(c, resolved_destination=rd, destination_resolved=ok)
        cons_index.setdefault(norm(rd), []).append(c)

    links, matched_cons = [], set()
    unmatched_prod = []
    for p in producers:
        rd, ok = resolve(p.get("destination"), config)
        matches = cons_index.get(norm(rd), [])
        if matches:
            for c in matches:
                matched_cons.add(id(c))
            links.append({
                "destination": rd,
                "destination_resolved": ok,
                "producer": {"ref": p.get("ref"), "source": p.get("source")},
                "consumers": [{"ref": c.get("ref"), "group": c.get("group"),
                               "source": c.get("source")} for c in matches],
                "fanout": len(matches),
                "confidence": 0.9 if ok else 0.5,
            })
        else:
            unmatched_prod.append({
                "destination": rd, "destination_resolved": ok,
                "producer": {"ref": p.get("ref"), "source": p.get("source")},
                "reason": "no_consumer_in_scope" if ok else "unresolved_destination",
            })

    unmatched_cons = []
    for lst in cons_index.values():
        for c in lst:
            if id(c) not in matched_cons:
                unmatched_cons.append({
                    "destination": c.get("resolved_destination"),
                    "destination_resolved": c.get("destination_resolved"),
                    "consumer": {"ref": c.get("ref"), "group": c.get("group"),
                                 "source": c.get("source")},
                    "reason": "no_producer_in_scope",
                })

    out = {
        "ok": True,
        "links": links,
        "unmatched_producers": unmatched_prod,
        "unmatched_consumers": unmatched_cons,
        "counts": {
            "links": len(links),
            "total_fanout": sum(l["fanout"] for l in links),
            "unmatched_producers": len(unmatched_prod),
            "unmatched_consumers": len(unmatched_cons),
        },
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
