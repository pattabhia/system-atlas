---
name: 07-business-behavior-reconstruction
description: Reconstruct whole current business behavior from technical flow, decisions, effects, state changes and integration consequences. Use to assemble the Current Behavior (CBH) model, Service Context, behavior families (success/rejection/exception/retry/async/manual), and capability mapping, attaching unresolved boundaries and unknown semantics to the behaviors they affect. Stack-agnostic. Normally routed by the current-behavior-orchestrator.
---

# Skill 07 — Business Behavior Reconstruction

## Mission
Reconstruct whole current business behavior from technical flow, decisions, effects, state changes and integration consequences. This skill is intentionally stack-agnostic.

## Build
Current Behavior / CBH; Service Context; business context; operation; behavior family; primary/contributing/supporting capabilities; known/inferred/unknown semantics; behavior-linked gaps.

```
Evidence
  ↓
Decisions + Effects
  ↓
Rules
  ↓
Behavior Variants
  ↓
Business Operation
  ↓
Capability Context
```

## Capability Rule
Prefer an existing enterprise capability taxonomy. If unavailable, emit **Capability Candidate + confidence**, never silently invent a canonical taxonomy. One operation can have one primary business intent while traversing multiple contributing/supporting capabilities.

## Behavior Families
Represent success, rejection, exception, retry/fallback, async continuation, human/manual handoffs and other materially distinct outcomes.

## Uncertainty Rule
Attach unresolved boundaries and unknown semantics directly to the behaviors they affect. Gap is part of current-state truth, not a disconnected error list.

## Outputs
CBH/current behavior model; Service Context; behavior family; capability mapping; behavior-linked evidence; unresolved boundaries; behavior confidence/completeness.
