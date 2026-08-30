# Adapters

Adapters are the technology-specific layer behind the [Stack Adapter Contract](../.claude/skills/shared/stack-adapter-contract.md). Each adapter is an `ADAPTER.md` (instructions telling Claude which real tools/commands satisfy each canonical capability) plus optional bundled `scripts/` for capabilities the read-source fallback cannot deliver with enough precision.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

**Claude is the runtime.** It reads an `ADAPTER.md` and runs the tools it names via `Bash`/`Read`/`Grep`. Nothing here is a standalone engine.

## Registry

| Adapter | Kind | Binds when | Capabilities |
|---------|------|-----------|--------------|
| [java-maven](java-maven/ADAPTER.md) | language / build | Stack Profile language = Java, build = Maven | `resolve_project_structure`, `resolve_dependencies`, `inspect_packaged_artifact`, `discover_entrypoints`, `build_source_model`, `build_call_graph`, `trace_data_state_flow`, `resolve_configuration`, `run_characterization_tests` |
| [relational-db](relational-db/ADAPTER.md) | data store (cross-cutting) | boundary kind = relational database | `inspect_datastore` |
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

## Not yet implemented
Cross-cutting infra: `resolve_service_target` (REST/OpenAPI, gRPC), `resolve_event_target` (Kafka and others). Additional languages: .NET, Node/TS, Python. Additional data stores: NoSQL/document, other RDBMS dialects. Until present, these bind to generic-fallback with a recorded capability gap.
