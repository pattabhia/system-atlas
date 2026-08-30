# system-atlas

**Current-behavior discovery for any codebase.** system-atlas reconstructs what an application actually does *today* — from source, dependencies, configuration, data stores and integrations — and produces an evidence-backed current-state behavior baseline suitable for later modernization comparison.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

## Design principles
- **Follow behavior, not repository or technology boundaries.** A repo, module, package, JAR, service or database is not automatically a behavior boundary.
- **Unknown is a valid result. Guessing is not.** Every claim carries provenance; unresolved boundaries and unavailable capabilities are recorded as gaps, never hidden.
- **Technology-neutral by construction.** Skills reason in neutral terms; concrete ecosystem mechanics live behind the [Stack Adapter Contract](.claude/skills/shared/stack-adapter-contract.md).
- **Discover → Resolve → Narrate → Continue.** Runs autonomously across boundaries; escalates to a human only when materially required.

## Architecture — 8 skills + 1 orchestrator
| # | Skill | Job |
|---|-------|-----|
| — | [current-behavior-orchestrator](.claude/skills/current-behavior-orchestrator/SKILL.md) | Routing, traversal state, recursion, capability binding, degraded mode, aggregation |
| 01 | [scope-operation-discovery](.claude/skills/01-scope-operation-discovery/SKILL.md) | Scope, Stack Profile(s), project vs operation mode, traversal seeds |
| 02 | [artifact-dependency-discovery](.claude/skills/02-artifact-dependency-discovery/SKILL.md) | Artifacts, dependency topology, versions |
| 03 | [entry-invocation-discovery](.claude/skills/03-entry-invocation-discovery/SKILL.md) | Entry points → candidate operations |
| 04 | [behavior-flow-traversal](.claude/skills/04-behavior-flow-traversal/SKILL.md) | Control/call/data/state flow walk |
| 05 | [boundary-artifact-resolution](.claude/skills/05-boundary-artifact-resolution/SKILL.md) | Resolve boundaries L0–L4, hand back to 04 |
| 06 | [decision-rule-semantic-discovery](.claude/skills/06-decision-rule-semantic-discovery/SKILL.md) | Decisions/effects, value lineage, rules, semantics |
| 07 | [business-behavior-reconstruction](.claude/skills/07-business-behavior-reconstruction/SKILL.md) | CBH, Service Context, behavior families, capabilities |
| 08 | [behavior-verification](.claude/skills/08-behavior-verification/SKILL.md) | Structural → BDD → characterization tests |

Shared contracts: [stack-adapter-contract](.claude/skills/shared/stack-adapter-contract.md) · [evidence-model](.claude/skills/shared/evidence-model.md) · [gap-model](.claude/skills/shared/gap-model.md) · [traversal-state](.claude/skills/shared/traversal-state.md)

## How it runs
Claude is the runtime. It reads the orchestrator + worker skills (markdown) and reasons in neutral terms; **adapters** tell it which real tools satisfy each canonical capability. An adapter is an `ADAPTER.md` (instructions calling real CLIs/tools) plus optional bundled `scripts/` where the read-source fallback is not precise enough (mainly `build_call_graph`, sometimes `trace_data_state_flow`). Adapters live under each capability owner and are bound per Stack Profile (language/source) or per boundary kind (data store / service / event). *No adapters are implemented yet — runs currently operate in degraded/fallback mode and record capability gaps accordingly.*

## Prompting

**Project / application scope**
```
Run current-behavior discovery on this application/project.
Root scope: <path/repository/workspace>.
Discover stack profiles, components, dependencies, entry points and business operations
automatically. Reconstruct each reachable operation using the full skill chain. Resolve
boundaries autonomously where access/evidence permits. If a required adapter capability is
unavailable, use degraded discovery mode, record the capability gap and continue where
feasible. Do not invent unresolved semantics. Produce the standard deliverable pack under
<output path>.
```

**Specific business operation**
```
Run the current-behavior skill chain for operation <operation name> in <root scope>.
Discover the technical entry point(s) automatically; do not assume the operation name is a
method/class name. Trace all reachable behavior across source, repositories, packages,
services, events, configuration and data stores. Resolve semantics from available evidence,
attach unresolved boundaries and capability gaps to affected behaviors, and generate the
standard behavior baseline, BDD and characterization assets where feasible.
```

## Deliverable structure

**Project-level run**
```
behavior-baseline/
└── <project-id>/
    ├── application-behavior-summary.md
    ├── 00-run-manifest/       run-summary.md, scope.yaml, stack-profiles.yaml, adapter-capability-coverage.yaml
    ├── 01-topology/           component-map.md, dependency-graph.md, artifact-inventory.yaml, version-resolution.yaml
    ├── 02-entrypoints/        entrypoint-catalog.yaml
    ├── 03-operations/         operation-catalog.yaml, <operation-id>/ ... operation pack ...
    ├── 90-evidence/           evidence-registry.yaml
    ├── 91-gaps/               gap-registry.yaml, capability-gap-registry.yaml
    └── 99-completeness/       completeness-report.md
```

**Operation-level pack**
```
<operation-id>/
├── 01-scope/            operation-scope.yaml, entrypoints.yaml
├── 02-artifacts/        artifact-map.yaml, boundary-registry.yaml
├── 03-flows/            end-to-end-flow.md, flow-graph.mmd, path-variants.yaml
├── 04-decisions-effects/ decisions.yaml, state-effects.yaml, integration-effects.yaml
├── 05-rules-semantics/  rule-catalog.yaml, semantic-resolutions.yaml, value-lineage.yaml
├── 06-behavior/         current-behavior.md, cbh.yaml, service-context.yaml, behavior-family.yaml, capability-map.yaml
├── 07-bdd/              <operation>.feature
├── 08-characterization/ tests/, observed-oracles/
├── 09-evidence/         evidence-registry.yaml
├── 10-gaps/             behavior-linked-gaps.yaml, capability-gaps.yaml
└── 11-confidence/       completeness-confidence.md
```

The structured artifacts are the canonical current-state truth; Markdown reports, diagrams and BDD are projections of that truth.

## Source of truth
Design originates from the Notion page *"Current Behavior Discovery — 8-Skill Architecture & Claude Wiring"*. Keep this repo and that page in sync.

## Status
Skill definitions scaffolded. **Next:** implement the first reference adapters — a language/build adapter for the primary stack, a data-store adapter, plus the generic fallback adapter — so capabilities run for real instead of in fallback.
