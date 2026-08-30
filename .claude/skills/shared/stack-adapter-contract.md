# Shared — Stack Adapter Contract

## Purpose
Define the technology-neutral capability boundary between the eight behavior skills and concrete ecosystem tooling.

> Skills understand behavior. Adapters understand technology. The orchestrator understands routing.

## Canonical Adapter Capabilities
Adapters implement only the capabilities they support. Capability names are the **single canonical vocabulary** used by skills, orchestrator state and adapter registry.

```
resolve_project_structure()
resolve_dependencies()
inspect_packaged_artifact()
discover_entrypoints()
build_source_model()
build_call_graph()
trace_data_state_flow()
inspect_datastore()
resolve_configuration()
resolve_service_target()
resolve_event_target()
run_characterization_tests()
```

## Capability Binding Model
The orchestrator binds each required capability to an available adapter implementation. State should use capability names directly rather than separate aliases such as `projectResolver`, `sourceAnalyzer` or `testRunner`.

Language/source capabilities bind per **Stack Profile**. Cross-cutting infrastructure capabilities (`inspect_datastore`, `resolve_service_target`, `resolve_event_target`) bind per **boundary kind**, selected by the target's type rather than the calling profile's language.

```yaml
stackProfiles:
  - id: <profile-id>
    language: <detected-or-unknown>
    buildSystem: <detected-or-unknown>
    frameworks: []
    datastores: []
    messaging: []
    testFrameworks: []

activeCapabilities:
  resolve_project_structure: <adapter-or-unsupported>
  resolve_dependencies: <adapter-or-unsupported>
  inspect_packaged_artifact: <adapter-or-unsupported>
  discover_entrypoints: <adapter-or-unsupported>
  build_source_model: <adapter-or-unsupported>
  build_call_graph: <adapter-or-unsupported>
  trace_data_state_flow: <adapter-or-unsupported>
  inspect_datastore: <adapter-or-unsupported>
  resolve_configuration: <adapter-or-unsupported>
  resolve_service_target: <adapter-or-unsupported>
  resolve_event_target: <adapter-or-unsupported>
  run_characterization_tests: <adapter-or-unsupported>
```

## Adapter-Specific Implementations
Concrete ecosystem details belong only inside adapter implementations or adapter documentation. They must not become canonical skill vocabulary or discovery rules.

An adapter is an `ADAPTER.md` (instructions telling Claude which real tools/commands satisfy each capability) plus optional bundled `scripts/` for capabilities the LLM-reading-source fallback cannot deliver with enough precision (typically `build_call_graph`, sometimes `trace_data_state_flow`). Claude is the runtime: it reads the ADAPTER.md and runs the tools via Bash/Read/Grep.

## Unsupported Capability Contract
If an adapter cannot implement a capability, it must return an explicit **unsupported** result with reason and evidence. The orchestrator must then activate degraded discovery for that capability where a generic fallback exists, register a capability gap, continue all feasible analysis, and propagate the limitation into completeness/confidence.

```
Capability requested
      ↓
Adapter available?
   ┌──┴──┐
  YES    NO
   │      │
execute  generic fallback if available
   │      │
   │      ├─ record CAPABILITY_GAP
   │      └─ continue reachable analysis
   └──────────────┐
                  ↓
          Evidence + limitations
```

## Generic Fallback Expectations
A generic source/text/configuration inspector may provide partial evidence when specialized capabilities are unavailable. It must **never** claim equivalent precision to AST, binary, schema or runtime-aware analysis. Fallback results must identify what could and could not be established.

## Polyglot Rule
When behavior crosses into a target with a different Stack Profile, the orchestrator rebinds capabilities for that subtree. The behavior/evidence model and run state remain unchanged.

## Adapter Output Contract
Every adapter result should return, where relevant: capability invoked; target identity; version; source location; resolution status; evidence/provenance; evidence level; discovered next targets; explicit limitations; and unsupported/fallback status.

## Guardrails
- Adapters discover mechanics; they do not invent business semantics.
- Missing support must be explicit, never silently ignored.
- Version mismatch must remain visible.
- Adapter-specific terminology must not leak into canonical behavior schemas except as source metadata.
- Application-specific identifiers must never be encoded as adapter-selection or behavioral-relevance rules unless supplied as explicit runtime configuration for that run.
