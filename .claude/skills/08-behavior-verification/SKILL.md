---
name: 08-behavior-verification
description: Determine what parts of reconstructed current behavior can be structurally or executably proven, and generate preservation artifacts. Use to link every behavior statement to source evidence, generate Gherkin for business-readable behavior, and produce native characterization tests that use the current/legacy implementation as the executable oracle. Normally routed by the current-behavior-orchestrator as the final step.
---

# Skill 08 — Behavior Verification

## Mission
Determine what parts of reconstructed current behavior can be structurally or executably proven and generate preservation artifacts using the target stack's native verification mechanisms.

## Verification Layers
1. **Structural verification** — every behavior statement links to source evidence.
2. **Scenario verification** — generate Gherkin for meaningful business-readable/testable behavior.
3. **Characterization verification** — where executable, run the current implementation and capture actual observable outcomes as the oracle for regression tests.

## Native Test Framework
Delegate test generation/execution mechanics to the active Stack Adapter (`run_characterization_tests`).

## BDD Rule
Gherkin is a projection of business behavior, **not** the lossless storage format for every technical condition.

```
Decision/Effect Model
        ↓
Business Behavior
        ↓
BDD Feature/Scenarios
        ↓
Native Characterization Tests
```

## Keep BDD in sync with behavior families (re-projection rule)
The BDD feature is a **projection of the behavior families** — it must be regenerated whenever the family set changes. Later passes routinely add families: **branch-completeness** (Skill 06) frequently surfaces a materially-distinct outcome (e.g. an operation succeeds but a downstream publish silently fails) that must be (a) elevated to a behavior family in Skill 07, then (b) re-projected here as a scenario. Do **not** leave an observation recorded only in the gap registry if it is a distinct outcome — that is a missed scenario. Every family with a business-readable/testable outcome maps to a scenario; computations/formulas (e.g. a password rule) stay in the rule catalog + characterization tests, not Gherkin. Treat "families changed since the feature was written" as a trigger to re-run this skill.

## Anti-Circularity
Avoid model predicts expected output → model generates test → test merely confirms its own prediction. Where feasible, the current/legacy implementation provides the executable oracle.

## Characterization execution (the oracle)
Prefer an **executed** oracle over asserted values: run the target's own tests (`tools/characterize.sh <project>`), capturing the current implementation's actual outcomes. When the build cannot run (offline, missing deps/DB/services), that is the honest **not-executed** result → record capability gap CG-04 and keep structural + BDD verification; never fabricate expected values.

## Self-consistency gate
End every verification by running `tools/pack_lint.py <pack-dir>`. FAIL findings block; WARN findings are the worklist. The linter is what makes the synthesized deliverables trustworthy against the mechanical evidence (families↔BDD, silent-failures addressed, reachable methods grounded, codes in catalog).

## Sequence views
Generate a per-operation Mermaid sequence diagram from the resolved call graph (`tools/seq_diagram.py <callgraph.json> <entry>`), showing collaborator interactions and external boundaries — a projection like the flow graph, useful for review.

## Outputs
BDD feature files; native characterization tests where feasible; sequence diagrams; lint report; verification evidence; traversal/semantic/verification coverage; confidence dimensions; final unresolved gaps.

## Guardrail
Do not fabricate semantic BDD steps beyond the evidence level of the reconstructed behavior.
