#!/usr/bin/env python3
"""
seq_diagram.py — generate a Mermaid sequenceDiagram for one operation from the
resolved call graph (Stage B). Tier-3 deliverable: per-operation sequence view.

Usage: seq_diagram.py <callgraph.json> <entry-method> [--depth N] [--title T]
Emits a ```mermaid sequenceDiagram fenced block on stdout.

Nodes are class-level participants; edges are method calls in call order (best-effort:
call graphs are unordered, so ordering follows a DFS from the entry). External/library
callees (non-project owners) are shown as boundary participants.
"""
import json, sys, argparse, re

def simple(owner):
    return (owner or "?").split(".")[-1]

NOISE = {"String", "Base64", "LocalDateTime", "DateTimeFormatter", "DateUtils2", "Objects",
         "System", "Arrays", "Collections", "Optional", "Math", "Integer", "Boolean", "Map",
         "List", "ArrayList", "HashMap", "StringUtils", "ExceptionUtils", "UUID", "Timestamp"}
COLLAB = re.compile(r"(Util|Service|ServiceImpl|Impl|Client|Repository|Helper|Verifier|"
                    r"Generator|Controller|Manager|Initializer|Template|Encryption|DataShare)$")

def is_participant(owner_fqn, project):
    """Keep only meaningful collaborators: project types or injected-collaborator-shaped
    classes. Drop local vars (lowercase), method-chain artifacts ('()'), and JDK/util noise."""
    if not owner_fqn:
        return False
    s = simple(owner_fqn)
    if not s or not s[0].isupper() or "(" in s or s in NOISE:
        return False
    return (project in owner_fqn) or bool(COLLAB.search(s))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("callgraph")
    ap.add_argument("entry")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--title", default=None)
    ap.add_argument("--project", default=None,
                    help="project base package; inferred from the call graph if omitted")
    args = ap.parse_args()

    d = json.load(open(args.callgraph, encoding="utf-8"))

    if not args.project:
        # infer the dominant in-project package from caller signatures (callers are, by
        # definition, methods being analyzed — i.e. in-project). No hardcoded literal.
        import collections as _c
        pkgs = _c.Counter()
        for e in d["edges"]:
            parts = e["caller"].split("(")[0].split(".")
            if len(parts) >= 4:
                pkgs[".".join(parts[:3])] += 1
        args.project = pkgs.most_common(1)[0][0] if pkgs else ""
        sys.stderr.write(f"[seq_diagram] inferred --project={args.project or '(none)'}\n")
    # adjacency: caller-method-name -> [(callee_owner, callee_method, resolved)]
    adj = {}
    for e in d["edges"]:
        cm = re.split(r"[.#(]", e["caller"].split("(")[0])
        caller = cm[-1] if cm else e["caller"]
        adj.setdefault(caller, []).append(
            (e["callee"].get("owner_fqn"), e["callee"]["method"], e.get("resolved")))

    lines, participants, seen_edges = [], [], set()
    def emit(caller_owner, method, depth):
        if depth > args.depth:
            return
        for owner, callee, resolved in adj.get(method, []):
            if not is_participant(owner, args.project):
                continue
            co = simple(owner)
            external = args.project not in (owner or "")
            key = (simple(caller_owner), co, callee)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            note = "  %% external boundary" if external else ""
            lines.append(f"    {simple(caller_owner)}->>{co}: {callee}(){note}")
            for p in (simple(caller_owner), co):
                if p not in participants:
                    participants.append(p)
            if not external:
                emit(owner, callee, depth + 1)

    # entry is Class#method or method
    if "#" in args.entry:
        ecls, emeth = args.entry.split("#", 1)
    else:
        ecls, emeth = "Client", args.entry
    participants.append(simple(ecls))
    emit(ecls, emeth, 1)

    print("```mermaid")
    print("sequenceDiagram")
    if args.title:
        print(f"    autonumber")
    for p in participants:
        print(f"    participant {p}")
    if not lines:
        print(f"    Note over {simple(ecls)}: no resolved outgoing calls at this depth")
    for l in lines:
        print(l)
    print("```")

if __name__ == "__main__":
    main()
