#!/usr/bin/env python3
"""
reachability.py — compute the reachable method closure from entry points, for
completeness-driven traversal (Skill 04). Free/OSS.

Inputs:
  --model      source-model.json  (java_ast.py --model)  — the universe of methods
  --callgraph  callgraph JSON      (Stage B jar, or java_ast --callgraph)
  --entry      comma list of entry method names (e.g. credentialEvent,getDigitalCard)

Method: name-based transitive closure over ALL edges (resolved, unresolved, and
interface->impl `override` edges). This is a SOUND OVER-APPROXIMATION — it never
misses a reachable method; it may include a same-named method on another class.
That is the safe direction for a coverage guarantee: better to visit one extra
method than to skip a reachable one. Resolved edges are precise; unresolved edges
(offline, external arg types) are linked by name and flagged.

Output JSON:
  { reachable:[{type,method}], unreached:[...], accessors:[...],
    counts:{...}, precision:{resolved_edges, name_only_edges} }
Accessors = getters/setters/constructors on dto/entity/constant/exception types:
framework/serialization-invoked, reported separately (not behavior to narrate).
"""
import argparse, json, re, collections

ACCESSOR_PKG = ("dto", "entity", "constant", "exception", "config")


def caller_name(sig):
    s = sig.split("(")[0]
    return re.split(r"[.#]", s)[-1] if s else s


def is_accessor(cls_name, method, pkg):
    if any(p in (pkg or "") for p in ACCESSOR_PKG):
        if method[:3] in ("get", "set") or method[:2] == "is" or method == cls_name:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--callgraph", required=True)
    ap.add_argument("--entry", required=True)
    args = ap.parse_args()

    model = json.load(open(args.model))
    cg = json.load(open(args.callgraph))
    entries = [e.strip() for e in args.entry.split(",") if e.strip()]

    # name-based adjacency: caller method name -> set(callee method name)
    adj = collections.defaultdict(set)
    resolved_edges = name_only = 0
    for e in cg["edges"]:
        cm = caller_name(e["caller"])
        callee = e["callee"]["method"]
        if not callee:
            continue
        adj[cm].add(callee)
        if e.get("resolved"):
            resolved_edges += 1
        else:
            name_only += 1

    # BFS closure over method names
    reached = set()
    q = list(entries)
    while q:
        n = q.pop()
        if n in reached:
            continue
        reached.add(n)
        for callee in adj.get(n, ()):
            if callee not in reached:
                q.append(callee)

    # classify every project method
    reachable, unreached, accessors = [], [], []
    for f in model["files"]:
        pkg = f.get("package") or ""
        for c in f["classes"]:
            for m in c["methods"]:
                rec = {"type": c["name"], "method": m["name"], "package": pkg}
                if is_accessor(c["name"], m["name"], pkg):
                    accessors.append(rec)
                elif m["name"] in reached:
                    reachable.append(rec)
                else:
                    unreached.append(rec)

    out = {
        "ok": True,
        "entry_points": entries,
        "reachable": sorted(reachable, key=lambda r: (r["type"], r["method"])),
        "unreached": sorted(unreached, key=lambda r: (r["type"], r["method"])),
        "accessors": sorted(accessors, key=lambda r: (r["type"], r["method"])),
        "counts": {
            "total_methods": sum(len(c["methods"]) for f in model["files"] for c in f["classes"]),
            "reachable": len(reachable),
            "unreached": len(unreached),
            "accessors": len(accessors),
        },
        "precision": {"resolved_edges": resolved_edges, "name_only_edges": name_only,
                      "note": "name-based closure = sound over-approximation; unresolved edges linked by name (offline). Provide --classpath to the Stage B jar for precise resolution."},
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
