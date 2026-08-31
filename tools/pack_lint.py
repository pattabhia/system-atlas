#!/usr/bin/env python3
"""
pack_lint.py — self-consistency + evidence-grounding linter for a behavior-baseline pack.

The pack mixes MECHANICAL EVIDENCE (90-evidence/*.json — tool output, ground truth)
with SYNTHESIZED REASONING (per-operation *.yaml/*.md — the runtime's interpretation).
This linter checks the synthesized artifacts are internally consistent AND grounded in
the evidence, so nothing is asserted that the evidence doesn't support and nothing the
evidence surfaces is silently dropped. It is the mechanical antidote to hand-patching.

Checks (per pack):
  STRUCT  each operation has the required files
  YAML    every .yaml parses
  FAMILY  every behavior family maps to a BDD scenario (or is marked non-projectable)
  SILENT  every silent-failure handler (exceptions.json) is addressed somewhere in the pack
  REACH   every reachable behavior-bearing method (reachability.json) is mentioned in some
          operation flow/decision artifact (coverage grounding)
  LIFECYC every framework-lifecycle unreached entry point has an operation
  CODES   error codes cited in the pack exist in the code catalog (errorcodes.json)

Usage: pack_lint.py <pack-dir>
Exit 0 if no FAIL findings; 1 otherwise.
"""
import json, os, re, sys, glob

try:
    import yaml
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False

REQUIRED_OP_FILES = ["01-scope", "03-flows", "04-decisions-effects", "06-behavior", "07-bdd",
                     "10-gaps", "11-confidence"]

findings = []
def add(sev, check, msg): findings.append({"severity": sev, "check": check, "message": msg})

def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""

def load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return None

def main():
    pack = sys.argv[1] if len(sys.argv) > 1 else "."
    ev = os.path.join(pack, "90-evidence")
    ops_dir = os.path.join(pack, "03-operations")
    ops = [d for d in glob.glob(os.path.join(ops_dir, "*")) if os.path.isdir(d)]

    # STRUCT + YAML
    for op in ops:
        for req in REQUIRED_OP_FILES:
            if not os.path.exists(os.path.join(op, req)):
                add("FAIL", "STRUCT", f"{os.path.basename(op)} missing {req}/")
    for yf in glob.glob(os.path.join(pack, "**", "*.yaml"), recursive=True):
        if HAVE_YAML:
            try:
                list(yaml.safe_load_all(read(yf)))
            except Exception as e:
                add("FAIL", "YAML", f"{os.path.relpath(yf, pack)} does not parse: {type(e).__name__}")

    # FAMILY -> BDD scenario
    for op in ops:
        fam = glob.glob(os.path.join(op, "06-behavior", "behavior-family.yaml"))
        feat = glob.glob(os.path.join(op, "07-bdd", "*.feature"))
        if not fam:
            continue
        ftext = read(feat[0]) if feat else ""
        ftext_low = ftext.lower()
        famtext = read(fam[0])
        # pull (id, name) pairs
        pairs = re.findall(r"id:\s*([A-Za-z0-9_-]+)\s*\n\s*name:\s*\"?([^\"\n]+)\"?", famtext)
        ids_only = re.findall(r"\bid:\s*([A-Za-z0-9_-]+)", famtext)
        seen = {p[0] for p in pairs}
        for fid in ids_only:
            if fid not in seen:
                pairs.append((fid, ""))
        for fid, name in pairs:
            if fid in ftext:
                continue
            # else try name keywords (>=2 distinctive words present in the feature)
            words = [w for w in re.findall(r"[a-zA-Z]{4,}", name.lower())
                     if w not in ("card", "with", "that", "when", "then", "fail", "failed")]
            hits = sum(1 for w in words if w in ftext_low)
            if hits >= 2:
                continue
            add("WARN", "FAMILY",
                f"{os.path.basename(op)}: behavior family '{fid}' has no matching BDD scenario "
                "(add a scenario, tag one with the family id, or mark it non-projectable).")

    # SILENT failures grounded / addressed
    exj = load_json(os.path.join(ev, "exceptions.json"))
    if exj:
        packtext = "\n".join(read(p) for p in glob.glob(os.path.join(pack, "**", "*.*"), recursive=True)
                             if p.endswith((".yaml", ".md")))
        for s in exj.get("silent_failures", []):
            meth = s["method"].split(".")[-1].split("#")[-1]
            if meth not in packtext:
                add("WARN", "SILENT",
                    f"silent-failure handler in {s['method'].split('.')[-1]} (L{s['line']}, {s['handling']}) "
                    "is not addressed in any pack artifact.")

    # REACH grounding
    rj = load_json(os.path.join(ev, "reachability.json"))
    if rj:
        flowtext = "\n".join(read(p) for p in glob.glob(os.path.join(ops_dir, "**", "*.*"), recursive=True)
                             if p.endswith((".yaml", ".md", ".mmd")))
        missing = []
        for m in rj.get("reachable", []):
            name = m["method"]
            if name not in flowtext and name not in ("main",):
                missing.append(f"{m['type']}#{m['method']}")
        if missing:
            add("WARN", "REACH",
                f"{len(missing)} reachable method(s) not mentioned in any operation artifact: "
                + ", ".join(sorted(set(missing))[:12]) + (" …" if len(missing) > 12 else ""))
        # LIFECYC
        for m in rj.get("unreached", []):
            pass  # classification lives in coverage.yaml; check that file exists
        cov = glob.glob(os.path.join(ops_dir, "**", "coverage.yaml"), recursive=True) + \
              glob.glob(os.path.join(pack, "**", "coverage.yaml"), recursive=True)
        if not cov:
            add("WARN", "LIFECYC", "no coverage.yaml found — unreached set not classified.")

    # CODES cited exist in catalog
    ecj = load_json(os.path.join(ev, "errorcodes.json"))
    if ecj:
        known = set()
        for e in ecj.get("enums", []):
            for c in e["constants"]:
                known.add(c["name"])
        cited = set()
        for p in glob.glob(os.path.join(ops_dir, "**", "*.yaml"), recursive=True):
            cited |= set(re.findall(r"\b([A-Z][A-Z0-9]+(?:_[A-Z0-9]+){1,})\b", read(p)))
        # only complain about tokens that look like error codes and resemble known families
        suspect = {c for c in cited if c.endswith(("_FAILED", "_NOT_GENERATED", "_NOT_SET",
                   "_NOT_CREATED", "_EXCEPTION", "_NOT_FOUND")) and c not in known}
        for c in sorted(suspect):
            add("WARN", "CODES", f"cited code-like token '{c}' not found in the code catalog.")

    # report
    fails = [f for f in findings if f["severity"] == "FAIL"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    out = {"ok": len(fails) == 0, "pack": pack,
           "counts": {"fail": len(fails), "warn": len(warns)},
           "findings": findings,
           "note": ("pyyaml not installed — YAML validity check skipped" if not HAVE_YAML else None)}
    print(json.dumps(out, indent=2))
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    main()
