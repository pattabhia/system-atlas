---
name: 04-behavior-flow-traversal
description: Perform the deep, evidence-backed traversal of current execution behavior across languages, packages, services and data stores. Use to follow control, call, data and state flow (plus exceptions, transactions, async, retries, fallbacks), hand boundaries to Skill 05, and switch adapters on cross-ecosystem hops. Normally routed by the current-behavior-orchestrator.
---

# Skill 04 — Behavior Flow Traversal

## Mission
Perform deep, evidence-backed traversal of current execution behavior across languages, packages, services and data stores.

## Technology Neutrality Invariant
Reason in terms of control flow, call flow, data flow and state flow. Obtain AST/call-graph/source-analysis mechanics from the active adapter.

## Traverse
Control flow; call flow; data flow; state flow; exceptions; transaction paths; async continuation; retries; fallbacks; cache paths; configuration-driven branches; and relevant executable source constructs.

```
ENTRY
 ↓
source/control flow
 ↓
call or effect
 ↓
boundary?
 ├─ yes → Skill 05 → resolved target → return here
 └─ no  → continue
```

## Cross-Ecosystem Hop
When traversal crosses into another technology ecosystem, preserve the same behavior state but switch to the adapter set selected for that target stack profile.

## Source Accounting
Source-construct accounting is a **completeness discipline**, not the reasoning unit. Analyze methods/functions/blocks/paths while accounting for behavior-relevant executable constructs.

## Outputs
Flow graph; path variants; calls; reads/writes; state transitions; technical termination points; business-outcome candidates; traversal-queue additions; evidence provenance; unresolved paths.

## Guardrails
Do not stop at repository, package, compiled artifact, service, event or data-store boundaries. Do not declare technical return/response as business completion without evidence.
