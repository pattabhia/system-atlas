# system-atlas

**Current-behavior discovery for any codebase.** system-atlas reconstructs what an application actually does *today* — from source, dependencies, configuration, data stores and integrations — and produces an evidence-backed current-state behavior baseline suitable for later modernization comparison.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

## Usage

### Install (once per machine) — clone anywhere, then run the installer
```bash
git clone https://github.com/pattabhia/system-atlas
cd system-atlas
./install.sh          # self-locating; works wherever you cloned it
```
`install.sh` is **location-independent**: it detects its own path, copies the skills + `/atlas` command to `~/.claude/`, sets `env.ATLAS_HOME` (the absolute path to this clone) in `~/.claude/settings.json`, registers the Stop hook with that absolute path, installs the Python deps, and builds the Stage-B jar. Everything the skills/command run is referenced via `$ATLAS_HOME`, so it works from any repo regardless of where the client cloned system-atlas. **Restart the Claude Code session** afterward so `ATLAS_HOME` + the hook load.

### Run
- **Slash command (recommended):**
  ```
  /atlas <root-path> [operation-name]
  ```
  `/atlas ./some-repo` discovers the stack + operations and reconstructs each; `/atlas ./some-repo CreateAccount` deep-reconstructs one operation.
- **Or invoke the skill directly:** `/current-behavior-orchestrator` and describe the scope. The orchestrator is the **single entry point** — it routes the 8 worker skills (as subagents) and binds adapters by stack profile / boundary kind. (All 9 skills are registered, but workers are marked "routed by the orchestrator", so a top-level request lands on the orchestrator.)

### Output
Packs are written to `<workspace-root>/.haiintel/behavior-baselines/<project-id>/` — outside the analyzed repo. Start reading at each pack's `MANIFEST.md` (auto-generated) → `application-behavior-summary.md`.

### Guaranteed finalize (manifest + lint) on every run
Three layers ensure it never gets skipped:
1. The orchestrator's Final Aggregation runs `tools/finalize_pack.sh <pack>` (emits `MANIFEST.md`, runs the self-consistency lint gate; FAIL blocks completion).
2. `/atlas` ends with the same finalize.
3. A **Stop hook** (`$ATLAS_HOME/tools/hook_finalize.sh`, wired by `install.sh`) finalizes any pack changed since its last manifest whenever a session stops — idempotent, non-blocking.

### Tools you can run standalone (on any pack / repo)
| Tool | Purpose |
|------|---------|
| `tools/finalize_pack.sh <pack>` | emit MANIFEST.md + run lint gate |
| `tools/pack_lint.py <pack>` | self-consistency + evidence-grounding lint (families↔BDD, silent-failures, reachable-grounded, codes-in-catalog, open-gaps-only) |
| `tools/pack_manifest.py <pack>` | (re)generate the root MANIFEST.md |
| `tools/seq_diagram.py <callgraph.json> <entry>` | per-operation Mermaid sequence diagram |
| `tools/characterize.sh <project>` | run the target's own tests as an executed oracle |
| `adapters/java-maven/scripts/run-coverage.sh <src> "<entries>" <out>` | full per-run analysis substrate (model, call graph, reachability, branches, exceptions, error codes, config) |
| `tools/smoke/smoke_test.py` (or `.sh` wrapper) | regression guards on a **non-MOSIP** fixture: interface→impl override edges emit generically, `seq_diagram` infers the package, finalize survives a degraded pack. Portable harness (all file I/O via Python tempfiles). Run in CI / after install. |

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
Claude is the runtime. It reads the orchestrator + worker skills (markdown) and reasons in neutral terms; **adapters** tell it which real tools satisfy each canonical capability. An adapter is an `ADAPTER.md` (instructions calling real CLIs/tools) plus optional bundled `scripts/` where the read-source fallback is not precise enough (mainly `build_call_graph`). Adapters live in [`adapters/`](adapters/) and are bound per Stack Profile (language/source) or per boundary kind (data store / service / event). See the [adapter registry](adapters/README.md).

**Reference adapters shipped:**
- [`java-maven`](adapters/java-maven/ADAPTER.md) — language/build; Tier-1 (`mvn`/`jdeps`/`javap`) + Tier-2 source analysis in two stages: **Stage A** [`java_ast.py`](adapters/java-maven/scripts/java_ast.py) on tree-sitter-java (MIT) — full Java 21 parse, source model, entry points, heuristic call graph; **Stage B** [`callgraph-jvm/`](adapters/java-maven/callgraph-jvm) JavaParser + SymbolSolver (Apache-2.0) — sound, fully-qualified call resolution. Both free/OSS.
- [`relational-db`](adapters/relational-db/ADAPTER.md) — `inspect_datastore`; live introspection ([Postgres reference SQL](adapters/relational-db/scripts/postgres_introspect.sql), Oracle/SQL Server/MySQL equivalents) or offline DDL/migration parsing, plus reference-data value resolution.
- [`service-resolver`](adapters/service-resolver/ADAPTER.md) — `resolve_service_target`; matches a client REST/gRPC call to the serving endpoint (across repos) via the entry-point catalog, OpenAPI ([indexer](adapters/service-resolver/scripts/openapi_index.py)) or `.proto`.
- [`event-resolver`](adapters/event-resolver/ADAPTER.md) — `resolve_event_target`; re-links async producers to consumer(s) by destination, preserving fan-out, via config-resolved topics and a [correlation helper](adapters/event-resolver/scripts/topic_match.py).
- [`generic-fallback`](adapters/generic-fallback/ADAPTER.md) — always-on; partial evidence via Read/Grep for any capability with no specialized adapter, with mandatory `⊘ CAPABILITY` gaps.

All 12 canonical capabilities now have a specialized adapter for a Java/Maven + relational-DB + REST + event stack. Still binding to generic-fallback: non-Java language adapters and NoSQL/document stores.

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

## Output location
Deliverable packs are written to a dedicated, workspace-scoped store **outside** the analyzed repo — so the target is never polluted and packs survive deleting a cloned target:

```
<workspace-root>/.haiintel/behavior-baselines/<project-id>/
```

`<workspace-root>` is the directory holding the analyzed repos (e.g. `10.HAIINTEL`). Supply an explicit output path in the run prompt to override.

## Deliverable structure

**Project-level run** (rooted at `~/.haiintel/behavior-baselines/`)
```
<project-id>/
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
├── 04-coverage/         coverage.yaml   (closure-driven proof: every reachable method visited; unreached classified)
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
Skills scaffolded + reference adapters shipped: java-maven, relational-db, service-resolver, event-resolver, generic-fallback — full capability coverage for a Java/Maven + relational-DB + REST + event stack. **Next:** additional language adapters (.NET, Node/TS, Python) and NoSQL stores as boundaries demand. First end-to-end validation run recommended against a representative Java/Maven operation.
