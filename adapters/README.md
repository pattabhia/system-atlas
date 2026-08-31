# Adapters

Adapters are the technology-specific layer behind the [Stack Adapter Contract](../.claude/skills/shared/stack-adapter-contract.md). Each adapter is an `ADAPTER.md` (instructions telling Claude which real tools/commands satisfy each canonical capability) plus optional bundled `scripts/` for capabilities the read-source fallback cannot deliver with enough precision.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

**Claude is the runtime.** It reads an `ADAPTER.md` and runs the tools it names via `Bash`/`Read`/`Grep`. Nothing here is a standalone engine.

## Registry

| Adapter | Kind | Binds when | Capabilities |
|---------|------|-----------|--------------|
| [java-maven](java-maven/ADAPTER.md) | language / build | Stack Profile language = Java, build = Maven | `resolve_project_structure`, `resolve_dependencies`, `inspect_packaged_artifact`, `discover_entrypoints`, `build_source_model`, `build_call_graph`, `trace_data_state_flow`, `resolve_configuration`, `run_characterization_tests` |
| [relational-db](relational-db/ADAPTER.md) | data store (cross-cutting) | boundary kind = relational database | `inspect_datastore` |
| [service-resolver](service-resolver/ADAPTER.md) | integration (cross-cutting) | boundary kind = synchronous service call (REST/gRPC) | `resolve_service_target` |
| [event-resolver](event-resolver/ADAPTER.md) | integration (cross-cutting) | boundary kind = async message/event | `resolve_event_target` |
| [generic-fallback](generic-fallback/ADAPTER.md) | fallback | always available; used when no specialized adapter supports a capability | partial: all capabilities, low precision |

## Binding rules
- **Language/source capabilities** bind per **Stack Profile** (java-maven serves a Java/Maven profile).
- **Infrastructure capabilities** (`inspect_datastore`, `resolve_service_target`, `resolve_event_target`) bind per **boundary kind** — selected by the *target's* type, not the calling profile's language. A Java service hitting Postgres binds `inspect_datastore` → relational-db.
- If a required capability has no specialized adapter, the orchestrator binds it to **generic-fallback**, records a `⊘ CAPABILITY` gap, and continues.

## Implementation tiers
- **Tier 1 — prompt-only:** the `ADAPTER.md` tells Claude which existing CLI to run (`mvn`, `jdeps`, `psql`, `git`). Most capabilities.
- **Tier 2 — bundled script:** a helper in `scripts/` for what no CLI gives directly (mainly `build_call_graph`). The `ADAPTER.md` says how to run it and what to do if it fails.
- **Tier 3 — external/MCP:** not used yet.

## Adapter output contract
Every capability result returns, where relevant: capability invoked; target identity; version; source location; resolution status; evidence/provenance; evidence level; discovered next targets; explicit limitations; and unsupported/fallback status. See the [contract](../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract).

## Language adapter scaffolds
[`dotnet`](dotnet/ADAPTER.md), [`node`](node/ADAPTER.md), [`python`](python/ADAPTER.md) — capability contracts + tooling maps defined (Roslyn / ts-morph / ast+LibCST), implementations pending. Until built, these bind to generic-fallback with a recorded capability gap.

## Cross-cutting tools (`../tools/`)
- `pack_lint.py` — self-consistency + evidence-grounding linter (mandatory completion gate).
- `pack_manifest.py` — emit the pack's root-level `MANIFEST.md` (self-documenting layout; every run).
- `seq_diagram.py` — per-operation Mermaid sequence diagram from the resolved call graph.
- `characterize.sh` — run the target's own tests as an executed oracle (Skill 08).

## java-maven analysis modes (all via `java_ast.py --<mode>`)
`--model --callgraph --entrypoints --branches --exceptions --errorcodes --config`; plus `reachability.py`, `lineage.py`, `idempotency.py`. `run-coverage.sh` chains the per-run substrate.

## Not yet implemented
Additional data stores as first-class adapters (NoSQL/document, other RDBMS dialects — dialect notes are inline in relational-db today); full language-adapter implementations (scaffolds above).
