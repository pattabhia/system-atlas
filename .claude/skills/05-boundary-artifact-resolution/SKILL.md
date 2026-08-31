---
name: 05-boundary-artifact-resolution
description: Resolve every behavior-relevant boundary encountered during traversal and return an inspectable target, independent of technology stack. Use to resolve packaged/compiled artifacts, cross-repository code, HTTP/RPC services, event consumers, data-store program objects and configuration-driven dispatch to levels L0-L4, request adapter switches on cross-ecosystem targets, and record boundary gaps. Normally routed by the current-behavior-orchestrator, in a loop with Skill 04.
---

# Skill 05 — Boundary & Artifact Resolution

## Mission
Resolve every behavior-relevant boundary encountered by traversal and return an inspectable target wherever possible, independent of technology stack.

## Resolve
Same-repository components; packaged/compiled artifacts; internal libraries/packages; separate source repositories; HTTP/RPC services; event consumers; data-store program objects; ORM/migration equivalents; rules engines; scripts/native artifacts; configuration-driven dispatch; generated code where behavior-bearing.

## Resolution Levels
- **L4** Fully resolved: source + config + verification evidence
- **L3** Source resolved
- **L2** Contract resolved
- **L1** Target identified
- **L0** Unknown

## Cross-Ecosystem Resolution
If the target belongs to another stack, identify its Stack Profile and request the orchestrator to activate the correct adapter set (rebind capabilities) for that subtree.

## Operating Rule
**Discover → Resolve → Narrate → Continue.** Do not ask the user at each boundary. If unresolved, capture what is known, create a behavior-linked boundary gap, and continue other reachable paths. Escalate only when human intervention is materially necessary.

## Data-store artifacts carry behavior
A resolved data store is not just a schema. Extract its **behavior**: constraints (NOT NULL/PK/FK/CHECK/DEFAULT/length) are DB-enforced rules; triggers/procedures/functions/views are executable logic to traverse like any other reachable code (enqueue their bodies back to Skill 04). When no program objects exist, record that **declarative-only** finding explicitly — absence is inspected, not skipped. Offline, use the adapter's DDL analyzer; live, use introspection.

## Outputs
Resolved target; artifact identity; version; repository/source location; target Stack Profile; data-store constraint rules + program objects (or explicit declarative-only finding); evidence/provenance; or explicit unresolved/ambiguous/version/access boundary.

## Handoff
Resolved implementation returns to Skill 04 for continued traversal.
