# Shared — Traversal State Contract

The orchestrator carries a common state object between skills. This is a **recursive graph walk**, not a one-pass pipeline: Skill 05 can resolve a new artifact and hand it back to Skill 04, and Skill 06 can discover new downstream reads/dependencies and return them to the traversal queue.

## Carried State
- `runId`
- `rootScope`
- `mode` — project | operation
- `operationId`
- `stackProfiles[]`
- `activeCapabilities` — capability → bound adapter (or `unsupported`)
- `capabilityGaps[]`
- `artifacts[]` — identity + version
- `currentNode`
- `traversalQueue[]`
- `visited[]`
- `entryPoints[]`
- `decisionsEffects[]`
- `stateDataEffects[]`
- `boundaries[]`
- `evidence[]` — with provenance
- `behaviorCandidates[]`
- `capabilityCandidates[]`
- `gaps[]`
- `evidenceLevels`
- `technicalTermination[]`
- `businessOutcomes[]`
- `verificationStatus`
- `completenessDimensions`

## Binding Rules
- **Language/source capabilities** bind per Stack Profile.
- **Infrastructure capabilities** (`inspect_datastore`, `resolve_service_target`, `resolve_event_target`) bind per boundary kind, by the target's type — not the calling profile's language.
- On a cross-ecosystem hop, rebind capabilities for the subtree; **run/operation/behavior state is unchanged**.

## Stop Condition
Stop when every reachable behavior-bearing path/boundary is either resolved-and-analyzed or explicitly represented as unresolved/ambiguous/unknown, and every required-but-unavailable capability is recorded as a capability gap.
