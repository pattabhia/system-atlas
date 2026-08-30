# Shared — Gap Model

Gaps are first-class current-state truth, not a disconnected error list. Every gap attaches to the behavior(s) it affects and propagates into completeness/confidence.

## Gap Kinds
| Kind | Attaches to | Example |
|------|-------------|---------|
| **Boundary gap** (`→ UNRESOLVED`) | a target the traversal hit | dependency JAR without source; service in an unreachable repo; unknown event consumer |
| **Semantic gap** (`? UNKNOWN` / `⚠ AMBIGUOUS`) | a value/identifier | a status code with no reference-data or config backing |
| **Artifact gap** (`✗ MISSING`) | a required artifact | schema not accessible; config file absent |
| **Version gap** | an artifact | manifest requires X, only Y is available |
| **Capability gap** (`⊘ CAPABILITY`) | an analysis capability | no call-graph adapter for the stack; datastore inspector unavailable |

## Required Handling
1. **Never silently reduce coverage.** A missing adapter or artifact becomes a recorded gap, not a quietly shallower analysis.
2. **Continue where feasible.** Preserve what is known, attach the gap, and keep walking other reachable paths.
3. **Escalate only when materially necessary** — human intervention required to proceed at all.
4. **Propagate** every gap into the completeness and confidence dimensions of the run.

## Registries (deliverables)
- Project level: `91-gaps/gap-registry.yaml` and `91-gaps/capability-gap-registry.yaml`
- Operation level: `10-gaps/behavior-linked-gaps.yaml` and `10-gaps/capability-gaps.yaml`
