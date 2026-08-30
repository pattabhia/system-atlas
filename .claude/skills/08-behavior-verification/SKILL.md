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

## Anti-Circularity
Avoid model predicts expected output → model generates test → test merely confirms its own prediction. Where feasible, the current/legacy implementation provides the executable oracle.

## Outputs
BDD feature files; native characterization tests where feasible; verification evidence; traversal/semantic/verification coverage; confidence dimensions; final unresolved gaps.

## Guardrail
Do not fabricate semantic BDD steps beyond the evidence level of the reconstructed behavior.
