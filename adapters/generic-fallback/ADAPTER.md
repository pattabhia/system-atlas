# Adapter — generic-fallback

**Kind:** fallback (always available)
**Binds when:** the orchestrator needs a capability for which **no specialized adapter** exists — an unknown/undetectable stack, or a known stack whose specialized adapter is missing a capability.
**Tools:** only `Read`, `Grep`, `Glob`, `find` — no language/DB/build tooling assumed.

This adapter keeps a run moving in **degraded discovery mode**. It provides *partial* evidence from source text and configuration. It must **never** claim precision equivalent to AST, bytecode, schema or runtime-aware analysis. Every capability it serves is recorded as a `⊘ CAPABILITY` gap with an explicit statement of what could and could not be established.

Emit results per the [Adapter Output Contract](../../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract), always with `fallback: true`.

---

## Capability behavior (all partial)

| Capability | Fallback method | Precision ceiling |
|-----------|-----------------|-------------------|
| `resolve_project_structure` | `find` for known manifest names (`pom.xml`, `build.gradle`, `package.json`, `*.csproj`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `*.sln`, `Makefile`); infer source roots from directory layout | structure only, no reactor/effective resolution |
| `resolve_dependencies` | grep manifests textually for declared deps + versions | declared, not *effective*; transitive graph unknown |
| `inspect_packaged_artifact` | list archive contents if `unzip`/`tar` exist; otherwise mark unresolved | no decompilation |
| `discover_entrypoints` | grep language-agnostic patterns: `main(`, HTTP route strings, handler/route registrations, `@`-annotations, `func Handler`, `app.get(`, cron expressions | pattern hits, not verified wiring |
| `build_source_model` | grep for `class`/`def`/`function`/`func`/`interface` declarations | names only, no types/scopes |
| `build_call_graph` | grep for `<identifier>(` callsites near definitions | callsite candidates, **no resolution** — low confidence edges |
| `trace_data_state_flow` | grep for assignments, DB/IO calls, returns | local observations, no dataflow soundness |
| `inspect_datastore` | grep for `CREATE TABLE`/SQL/migration files, ORM model definitions | DDL text if present, no live state |
| `resolve_configuration` | Read `.properties`/`.yml`/`.env`/`.json`/`.toml` config files | literal values; unresolved placeholders stay `? UNKNOWN` |
| `resolve_service_target` | grep for URLs/base paths/client definitions | endpoint strings, no cross-repo resolution |
| `resolve_event_target` | grep for topic/queue/exchange names and producer/consumer keywords | names only, no producer↔consumer matching |
| `run_characterization_tests` | **not attempted** — no runner assumed | none — structural verification only |

## Mandatory reporting
For every capability served here, the result MUST include:
- `fallback: true` and a `⊘ CAPABILITY` gap entry;
- `established:` — what was found with what (weak) evidence;
- `not_established:` — what a specialized adapter would have resolved (e.g. "effective dependency versions", "resolved call edges", "live reference-data meaning");
- a downgraded evidence level (typically `~ INFERRED` / `? UNKNOWN`, never `✓ PROVEN` for resolution-dependent claims).

## Guardrails
- Never upgrade a grep hit to a proven fact.
- Never invent structure the text does not show.
- Surface the capability gap so completeness/confidence reflect the degraded coverage — silent shallow analysis is the one prohibited outcome.
