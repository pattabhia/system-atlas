# Adapter — java-maven

**Kind:** language / build
**Binds when:** a Stack Profile reports language = Java and build system = Maven.
**Prerequisites (check first, record as capability limitations if absent):** `mvn`, a JDK (`javap`, `jdeps`, `jar`), `git`; optional `python3` + `javalang` for the AST script.

This adapter owns the **language/source** capabilities for a Java/Maven profile. It does **not** own `inspect_datastore`, `resolve_service_target` or `resolve_event_target` — it only *discovers the call sites* for those and hands the boundary to the orchestrator, which binds the cross-cutting adapter by boundary kind.

Always emit results per the [Adapter Output Contract](../../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract). When a prerequisite is missing, return `unsupported`/`fallback` with a reason — never silently skip.

---

## resolve_project_structure — Tier 1
Discover the module tree and source roots.
```bash
# module tree (reactor)
mvn -q -o help:evaluate -Dexpression=project.modules -DforceStdout 2>/dev/null || true
# fall back to walking POMs when offline / no network
find . -name pom.xml -not -path '*/target/*'
```
For each `pom.xml`: read `<groupId>/<artifactId>/<version>/<packaging>`, `<modules>`, `<build><sourceDirectory>` (default `src/main/java`), and resource roots. Emit a component/module inventory with source roots and parent/child links. Evidence level: **L3 AUTHORITATIVE** (declared in POM).

## resolve_dependencies — Tier 1
Resolve *effective* coordinates and versions (after inheritance, `dependencyManagement`, properties, profiles).
```bash
mvn -q -o dependency:tree -DoutputType=text 2>/dev/null
mvn -q -o help:effective-pom 2>/dev/null            # authoritative resolved versions
```
If offline resolution fails, parse `pom.xml` + parent POMs textually and mark unresolved version properties as `~ INFERRED`. Classify each dependency: same-repo module | internal library | third-party | BOM/import. Record `scope` (compile/runtime/test/provided) — it changes runtime reachability.
**Version invariant:** if the manifest requires version X, do not analyze Y. Resolve the matching source/tag/artifact; otherwise register a **version gap**.

## inspect_packaged_artifact — Tier 1
For a dependency JAR reached during traversal:
```bash
# prefer attached sources
mvn -q -o dependency:sources -Dartifact=<g:a:v> 2>/dev/null
jar tf <artifact.jar> | head              # contents
javap -p -c -classpath <artifact.jar> <fqcn>   # bytecode when no source
jdeps <artifact.jar>                       # package-level dependencies
```
Resolution: source-jar present → **L3**; bytecode only → **L2** (contract) with a boundary gap noting source unavailable.

## discover_entrypoints — Tier 2 (script) → Tier 1 (grep fallback)
Find invocation surfaces. Preferred: run the AST script, which flags entrypoint annotations.
```bash
python3 scripts/java_ast.py --root <source-root> --entrypoints
```
Recognized surfaces (examples, not an exhaustive rule): `@RestController`/`@RequestMapping`/`@GetMapping`… , JAX-RS `@Path`, `@KafkaListener`/`@JmsListener`/`@RabbitListener`, `@Scheduled`, Spring Batch jobs, `@MessageMapping`, `CommandLineRunner`/`main(String[])`, `@EventListener`.
Fallback if the script/`javalang` is unavailable:
```bash
grep -rEn '@(RestController|RequestMapping|Get|Post|Put|Delete|Patch)Mapping|@Path|@KafkaListener|@Scheduled|CommandLineRunner|public static void main' --include='*.java' <root>
```
Map each entry point → source provenance + invocation mechanism + input contract. Guardrail: an entry point is a *technical* start, not automatically the business start/end.

## build_source_model — Tier 2 (script)
```bash
python3 scripts/java_ast.py --root <source-root> --model > source-model.json
```
Emits per file: package, classes, methods (name, params, return, annotations), fields, and imports. If `javalang` is missing, degrade to grep-based class/method extraction and mark the model **partial (`⊘ CAPABILITY`)**.

## build_call_graph — Tier 2 (script)  ← the one real-code capability
```bash
python3 scripts/java_ast.py --root <source-root> --callgraph > callgraph.json
```
Produces caller→callee edges by **heuristic name/type resolution** (see the script's own limitations block). Edges carry a `confidence`. Overload/dynamic-dispatch/reflection cases are marked ambiguous, not guessed.
**Precision honesty:** this is AST-heuristic, not a soundness-guaranteed graph. It must never be presented as equivalent to a compiler/bytecode call graph. When the script is unavailable, fall back to grep for callsites and mark the capability `⊘ CAPABILITY partial`.

## trace_data_state_flow — Tier 2 (script + reasoning)
Use `source-model.json` + `callgraph.json` to follow reads/writes to fields, parameters, persisted entities and returned values along a path. Record state transitions and data lineage with provenance. Where dispatch is ambiguous, branch the path and attach an ambiguity gap rather than picking one.

## resolve_configuration — Tier 1
```bash
find . -name 'application*.properties' -o -name 'application*.y*ml' -o -name 'bootstrap*.y*ml'
```
Read property/YAML config and Spring profiles; resolve `${placeholder}` and profile-specific overrides where evidence permits. Config-driven branches and targets (URLs, topic names, feature flags) feed Skills 05/06. Unresolved placeholders → `? UNKNOWN`.

## run_characterization_tests — Tier 1
```bash
mvn -q -o test -Dtest=<GeneratedCharacterizationTest>
```
Run existing or generated JUnit tests so the **current implementation is the oracle**. Capture actual observed outcomes. If the build cannot run (missing deps, no network, no DB), record a capability gap and fall back to structural verification only. Never fabricate expected values the implementation did not produce.

---

## Explicitly unsupported by this adapter
`inspect_datastore`, `resolve_service_target`, `resolve_event_target` — bound by the orchestrator to the relevant cross-cutting adapter by boundary kind.
