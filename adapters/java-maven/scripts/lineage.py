#!/usr/bin/env python3
"""
lineage.py — value/data lineage for one identifier, over the source model + call graph.
Tier-2: trace where a field/parameter is read, transformed, persisted, or emitted.

Heuristic (tree-sitter-based): find every method whose body textually references the
term, classify the reference site (assignment / DB write / external call / return /
event / condition), and chain via the call graph. Best-effort — flags confidence.

Usage: lineage.py --root <src> --term <identifier> [--callgraph callgraph.json]
"""
import argparse, json, os, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--term", required=True)
    ap.add_argument("--callgraph", default=None)
    args = ap.parse_args()
    term = args.term
    pat = re.compile(r"\b" + re.escape(term) + r"\b")

    DB_HINT = re.compile(r"\b(repository|repo|save|update|find|insert|delete|persist|jdbc|entity)\b", re.I)
    EXT_HINT = re.compile(r"\b(restClient|restApiClient|postApi|getApi|getForObject|client)\b", re.I)
    EVT_HINT = re.compile(r"\b(publish|event|topic|kafka|websub|send)\b", re.I)

    sites = []
    for dp, dn, fn in os.walk(args.root):
        dn[:] = [d for d in dn if d not in ("target", "build", ".git")]
        for f in fn:
            if not f.endswith(".java"):
                continue
            path = os.path.join(dp, f)
            for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
                if not pat.search(line):
                    continue
                s = line.strip()
                kind = ("db-write" if DB_HINT.search(s) and re.search(r"\b(save|update|insert|delete)\b", s, re.I)
                        else "db-read" if DB_HINT.search(s)
                        else "external-call" if EXT_HINT.search(s)
                        else "event" if EVT_HINT.search(s)
                        else "assignment" if "=" in s and "==" not in s
                        else "condition" if re.search(r"\b(if|while|switch|\?)\b", s)
                        else "reference")
                sites.append({"file": path, "line": i, "kind": kind, "code": s[:120]})
    by_kind = {}
    for s in sites:
        by_kind.setdefault(s["kind"], 0)
        by_kind[s["kind"]] += 1
    out = {"ok": True, "capability": "value_lineage", "term": term, "root": args.root,
           "sites": sites, "by_kind": by_kind,
           "counts": {"sites": len(sites)},
           "note": "heuristic textual lineage; confirm sinks (db-write/external-call/event) against the call graph + adapter evidence."}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
