#!/usr/bin/env python3
"""
idempotency.py — flag idempotency/concurrency risks for event- and message-driven
operations. Tier-2. Heuristic (tree-sitter-based).

For each entry point that consumes an event/message (annotations like @KafkaListener,
WebSub callbacks, or methods reached from ApplicationReadyEvent), check whether the
handler guards against duplicate delivery:
  - reads existing state by a key before writing (find*/exists* before save/insert), or
  - relies on a unique/PK upsert, or
  - has NO guard (INSERT without prior existence check) -> duplicate-delivery risk.

Also flags retry loops and fixed-rate schedulers (concurrency surface).
Output is advisory evidence for Skill 06/07 — confirm against the DB constraints
(a PK on the key makes duplicate INSERT fail rather than duplicate).

Usage: idempotency.py --root <src>
"""
import argparse, json, os, re

EVENT_ANNO = re.compile(r"@(KafkaListener|JmsListener|RabbitListener|SqsListener|"
                        r"PreAuthenticateContentAndVerifyIntent|StreamListener|EventListener)")
READ = re.compile(r"\b(find\w*|exists\w*|get\w*ById|load\w*|count\w*)\s*\(", re.I)
WRITE = re.compile(r"\b(save|insert|persist|create|update|merge)\w*\s*\(", re.I)
RETRY = re.compile(r"\b(retry|scheduleAtFixedRate|scheduleWithFixedDelay|for\s*\()", re.I)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    findings = []
    for dp, dn, fn in os.walk(args.root):
        dn[:] = [d for d in dn if d not in ("target", "build", ".git")]
        for f in fn:
            if not f.endswith(".java"):
                continue
            path = os.path.join(dp, f)
            text = open(path, encoding="utf-8", errors="replace").read()
            if not (EVENT_ANNO.search(text) or "ApplicationReadyEvent" in text):
                continue
            # crude method slicing by signature
            for m in re.finditer(r"(public|private|protected)[^;{]*\b(\w+)\s*\([^)]*\)\s*\{", text):
                name = m.group(2)
                start = m.end()
                depth, i = 1, start
                while i < len(text) and depth:
                    depth += text[i] == "{"
                    depth -= text[i] == "}"
                    i += 1
                body = text[start:i]
                has_write = bool(WRITE.search(body))
                has_read = bool(READ.search(body))
                has_retry = bool(RETRY.search(body))
                if has_write and not has_read:
                    findings.append({"method": name, "file": path,
                                     "risk": "duplicate-delivery",
                                     "detail": "writes without a prior existence/key check — a re-delivered event may duplicate or conflict (confirm against PK/unique constraint).",
                                     "confidence": "heuristic"})
                if has_retry and has_write:
                    findings.append({"method": name, "file": path,
                                     "risk": "retry-concurrency",
                                     "detail": "retry/fixed-rate loop around a write — may run concurrently or repeat side effects.",
                                     "confidence": "heuristic"})
    out = {"ok": True, "capability": "idempotency_analysis", "root": args.root,
           "findings": findings, "counts": {"findings": len(findings)},
           "note": "Advisory. Confirm each against the datastore constraints (a PK on the write key converts 'duplicate' into a failed insert) and the actual delivery semantics."}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
