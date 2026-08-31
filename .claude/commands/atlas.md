---
description: Run system-atlas current-behavior discovery on a repo (or one operation), then finalize (manifest + lint).
argument-hint: <root-path> [operation-name]
---
Run **system-atlas** current-behavior discovery. The tool lives at `$ATLAS_HOME` (an absolute path set by `install.sh`); use it for every tool/adapter reference so this works from any repo on any machine.

Root scope: `$1`
Operation (optional): `$2` — if given, deep-reconstruct just that business operation; otherwise discover the stack profile, entry points, and business operations, and reconstruct each.

Use the `current-behavior-orchestrator` skill as the single entry point; it routes the 8 worker skills (as subagents) and binds adapters (`$ATLAS_HOME/adapters/...`) by stack profile / boundary kind. Run the per-run analysis substrate with `$ATLAS_HOME/adapters/java-maven/scripts/run-coverage.sh`. Work autonomously across reachable boundaries; do not invent unresolved semantics; record only open gaps.

Write the deliverable pack to `<workspace-root>/.haiintel/behavior-baselines/<project-id>/`.

**Always finish by finalizing the pack** (mandatory, every run):
```
"$ATLAS_HOME/tools/finalize_pack.sh" <pack-dir>
```
This emits the root `MANIFEST.md` and runs the self-consistency lint gate. Report the lint verdict; FAIL findings block completion.
