---
name: current-behavior-orchestrator
description: Orchestrate end-to-end current-behavior discovery of an application or a single business operation. Use when asked to reconstruct what a system actually does today, build a current-state behavior baseline, map legacy behavior before modernization, or run "system-atlas" discovery over a repo/workspace. Owns traversal state, capability-to-adapter binding, recursion, degraded-mode handling, stopping criteria and final aggregation across the 8 worker skills.
---

# Orchestrator — Current Behavior Skill Chain

## Role
A **thin orchestration skill** that coordinates the eight domain skills. It owns traversal state, routing, recursion, capability-to-adapter binding, adapter switching, hand-offs, degraded-mode handling, stopping criteria and final aggregation. It must **not** duplicate the detailed reasoning instructions inside the worker skills.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

## Important Distinction
The behavioral architecture is **8 core skills**. This orchestrator is the control-plane skill used to wire them together. It is the primary invocation surface — worker skills should normally be routed by it rather than invoked manually one by one.

## Chain
```
01 Scope + Stack Profile
        ↓
02 Artifacts / Dependencies
        ↓
03 Entry / Invocation
        ↓
04 Behavior Traversal
        ↕
05 Boundary Resolution
        ↕
06 Decision / Semantic Discovery
        ↓
07 Behavior Reconstruction
        ↓
08 Verification
```

## Execution Model — Subagent Dispatch
The orchestrator stays the single control surface, but each worker skill runs as its **own subagent** (via the Agent tool). The orchestrator never reasons a worker skill's step inline.

For each step:
1. Spawn a subagent for the worker skill (e.g. `Skill 04 — Behavior Flow Traversal`), instructing it to apply that skill's `SKILL.md`.
2. Pass only the **relevant slice of shared state** it needs (scope, current node, bound capabilities, the sub-queue) — not the whole run.
3. Require a **typed handoff** back (the skill's declared Outputs), which the orchestrator merges into shared state.
4. Route the next step from the merged state.

Rules:
- **Adapters are invoked by the subagent**, not the orchestrator — a worker subagent calls the bound adapter capability (e.g. `build_call_graph` → java-maven) and returns evidence.
- **Isolation:** each subagent gets its own context window — essential for deep traversal of large repos.
- **Parallelism:** independent steps fan out concurrently — e.g. Skill 02 alongside the entry scan, or Skill 04 across multiple entry points. Dispatch those in one batch.
- **Recursion preserved:** when a Skill 04 subagent reports a new boundary, the orchestrator spawns a Skill 05 subagent, then re-spawns Skill 04 for the resolved target. The queue lives in the orchestrator, not inside any subagent.
- **State authority:** only the orchestrator mutates shared state. Subagents return data; they do not carry cross-step state themselves.

## Capability Routing
Skill 01 emits one or more **Stack Profiles**. The orchestrator binds the canonical capabilities from the [Stack Adapter Contract](../shared/stack-adapter-contract.md) to available adapter implementations. When traversal crosses into a different ecosystem, **rebind capabilities for that subtree** while preserving the same run/operation/behavior state.

Language/source capabilities bind per **Stack Profile**. Cross-cutting infrastructure capabilities (`inspect_datastore`, `resolve_service_target`, `resolve_event_target`) bind per **boundary kind** encountered, not by the calling profile's language.

## Unsupported Stack / Capability Handling
Absence of a specialized adapter must never silently reduce coverage. For each required capability:
1. use the specialized adapter if available;
2. otherwise use a generic fallback capability where available;
3. record an explicit **capability gap** and limitation;
4. continue all reachable analysis that remains feasible;
5. propagate the limitation into completeness and confidence.

If the stack itself cannot be confidently identified, run in **degraded discovery mode** using generic source/text/configuration inspection and preserve the stack identity as unknown/ambiguous.

```
Required capability
      ↓
Specialized adapter?
  ┌───┴───┐
 YES      NO
  │        ↓
execute   generic fallback?
           ┌──┴──┐
          YES    NO
           │      │
        execute   mark unavailable
           └──┬───┘
              ↓
        CAPABILITY GAP
              ↓
      continue where feasible
```

## Recursive Routing
- Skill 04 finds a new boundary → invoke Skill 05.
- Skill 05 resolves a source/package/repository/data-store/service/event target → enqueue target and return to Skill 04.
- Skill 06 discovers downstream value usage or a new behavioral dependency → enqueue for Skill 04/05.
- When reachable traversal is accounted for, invoke Skill 07.
- Invoke Skill 08 after reconstruction; verification findings may create new evidence or gaps.

This is a **recursive graph walk**, not a one-pass pipeline.

## Shared State Contract
Carry: run ID; root scope; mode; operation ID; Stack Profile(s); `activeCapabilities`; capability gaps; artifact IDs/versions; current traversal node; traversal queue; visited set; entry points; decisions/effects; state/data effects; boundaries; evidence/provenance; behavior candidates; capability candidates; gaps; evidence levels; technical termination; business outcomes; verification status; completeness dimensions.

See [traversal-state.md](../shared/traversal-state.md).

## Autonomous Behavior
Narrate important hops while continuing automatically. Missing artifacts or capabilities normally create behavior-linked or capability-linked gaps rather than interactive questions. Operating rule: **Discover → Resolve → Narrate → Continue.**

## Coverage Discipline — closure-driven, provable
Completeness must be **proven from the call graph, not asserted by judgment**. After Skill 03 gives entry points and `build_call_graph` gives the resolved graph:
1. Compute the **transitive reachable set** of methods from every entry point over the resolved graph, including **interface→implementation (override) edges** (a call resolving to an interface method must expand to its concrete implementors). Offline/unresolved edges fall back to a **name-based over-approximation** (sound: never misses a reachable method) — flag those hops as heuristic.
2. **Visit every reachable behavior-bearing method** (exclude DTO/entity/constant accessors as framework-invoked). Mark each `visited` / `deferred-at-boundary`.
3. Emit a **coverage report** (`04-coverage/coverage.yaml`): total methods, reachable/visited, and the **unreached set explicitly classified** — framework-lifecycle entry points (which are *new operations*, e.g. subscription bootstrap), cross-cutting handlers, and candidate-dead code. Unreached is a finding, not silence.
4. **Re-seed and repeat**: every framework-lifecycle entry point the unreached set surfaces is added to the entry set and the closure recomputed, until the unreached set contains only accessors and genuinely-unused methods.

**Run-loop wiring:** after Skill 03, the orchestrator runs `adapters/java-maven/scripts/run-coverage.sh <src> "<entry-methods>" <out>` — it chains source-model → call graph (Stage B if built) → `reachability.py` → branch inventory (`--branches`), printing reachable/unreached and branch/arm counts. Skill 04 then visits every reachable method; Skill 06 reconciles every branch arm (covered decision / business rule / trivial). This step is **mandatory every run**; a run without a coverage report AND a branch-completeness reconciliation has not met the stop condition.

## Stop Condition
Stop when every reachable behavior-bearing path/boundary discovered from the scoped operation is either resolved and analyzed or explicitly represented as unresolved/ambiguous/unknown, **and** every required-but-unavailable analysis capability is a capability gap, **and** the coverage report accounts for every project method (reachable-visited / accessor / unreached-classified).

## Output Location
Write the deliverable pack to a dedicated, workspace-scoped store **outside** the analyzed repository so it never pollutes the target and survives deletion of a cloned target:

```
<workspace-root>/.haiintel/behavior-baselines/<project-id>/
```

`<workspace-root>` is the directory holding the analyzed repos (e.g. `10.HAIINTEL`). Use an explicit `<output path>` when the run prompt supplies one; otherwise default to the path above. Never write the pack inside the target repo by default.

## Final Aggregation
Produce project/operation summary, stack profile, capability coverage, artifact/dependency topology, operation catalog where applicable, flow topology, decisions/effects, rule catalog, CBH + Service Context, capability mapping, BDD, native characterization assets where supported, evidence registry, behavior-linked gaps, capability gaps and completeness/confidence dimensions.

See the deliverable structure in [README](../../../README.md).
