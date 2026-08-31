---
description: Run system-atlas current-behavior discovery on a repo (or one operation), then finalize (manifest + lint).
argument-hint: <root-path> [operation-name]
---
Run **system-atlas** current-behavior discovery.

Root scope: `$1`
Operation (optional): `$2` — if given, deep-reconstruct just that business operation; otherwise discover the stack profile, entry points, and business operations, and reconstruct each.

Use the `current-behavior-orchestrator` skill as the single entry point; it routes the 8 worker skills (as subagents) and binds adapters by stack profile / boundary kind. Work autonomously across reachable boundaries; do not invent unresolved semantics; record open gaps.

Write the deliverable pack to `<workspace-root>/.haiintel/behavior-baselines/<project-id>/`.

**Always finish by finalizing the pack** (mandatory, every run):
```
tools/finalize_pack.sh <pack-dir>
```
This emits the root `MANIFEST.md` and runs the self-consistency lint gate. Report the lint verdict; FAIL findings block completion.
