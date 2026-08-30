# Adapter — java-maven

**Kind:** language / build
**Binds when:** a Stack Profile reports language = Java and build system = Maven.
**Prerequisites (check first, record as capability limitations if absent):** `mvn`, a JDK 21 (`javap`, `jdeps`, `jar`), `git`; `python3` + `tree-sitter`/`tree-sitter-java` for the Stage-A AST script; optionally the prebuilt `callgraph-jvm/target/callgraph.jar` for Stage-B symbol-solved call graphs.

## Source analysis — two stages (both free/OSS)
- **Stage A** — `scripts/java_ast.py` on **tree-sitter-java** (MIT). Parses the full Java 21 grammar (records, sealed types, switch expressions, text blocks). Serves `build_source_model`, `discover_entrypoints`, and a **heuristic** `build_call_graph`.
- **Stage B** — `callgraph-jvm/` (JavaParser + SymbolSolver, Apache-2.0). **Resolves** each call to a fully-qualified method (overloads, inheritance, cross-jar) for a **sound** `build_call_graph`. Preferred when available; Stage A is the fallback.

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
Fallback if the script/`tree-sitter` is unavailable:
```bash
grep -rEn '@(RestController|RequestMapping|Get|Post|Put|Delete|Patch)Mapping|@Path|@KafkaListener|@Scheduled|CommandLineRunner|public static void main' --include='*.java' <root>
```
Map each entry point → source provenance + invocation mechanism + input contract. Guardrail: an entry point is a *technical* start, not automatically the business start/end.

## build_source_model — Tier 2 (script)
```bash
python3 scripts/java_ast.py --root <source-root> --model > source-model.json
```
Emits per file: package, classes, methods (name, params, return, annotations), fields, imports, and a `parse_incomplete` flag. Parses full Java 21 via tree-sitter. If `tree-sitter` is missing, degrade to grep-based class/method extraction and mark the model **partial (`⊘ CAPABILITY`)**.

## build_call_graph — prefer Stage B (symbol-solved); fall back to Stage A (heuristic)

**Stage B — sound resolution (preferred).** Build the jar once, resolve the classpath, run:
```bash
# one-time (needs network to Maven Central):
callgraph-jvm/build.sh                                   # -> callgraph-jvm/target/callgraph.jar
# per target:
mvn -q dependency:build-classpath -Dmdep.outputFile=cp.txt   # effective classpath
java -jar callgraph-jvm/target/callgraph.jar --src <source-root> --classpath cp.txt > callgraph.json
```
Each edge resolves to a fully-qualified `owner_fqn` + method `signature` with `resolved:true` (**PROVEN**). Overloads/inheritance/cross-jar are resolved by the symbol solver. Unresolvable calls stay `resolved:false` — never guessed. Without `--classpath`, intra-project + JDK calls still resolve; cross-jar edges to unbuilt dependencies are reported unresolved (a boundary/version gap, not an invention).

**Stage A — heuristic (fallback when the jar/classpath is unavailable).**
```bash
python3 scripts/java_ast.py --root <source-root> --callgraph > callgraph.json
```
Caller→callee edges by **heuristic name/type resolution**; each carries a `confidence` and `resolved` flag. Complex receivers (method chains) are flagged `resolved:false`, not guessed.

**Precision honesty:** Stage A is AST-heuristic, not sound — never present it as a compiler/bytecode graph. Stage B is source-symbol-solved (sound within the resolved classpath); it is still not bytecode-level (does not follow reflection/dynamic proxies — that would be an optional Soot/WALA Stage C). If neither runs, grep for callsites and mark `⊘ CAPABILITY partial`.

## reachability / coverage — closure over the call graph
After building the call graph, compute the reachable-method closure from the entry points to drive complete traversal (Skill 04's coverage discipline):
```bash
python3 scripts/reachability.py --model source-model.json --callgraph callgraph.json \
        --entry "<entryMethod1>,<entryMethod2>,..." > reachability.json
```
Uses **resolved + interface-override edges** (Stage B emits `dispatch:"override"` edges so a call to an interface method expands to its concrete implementors), with a **name-based fallback** for unresolved edges — a *sound over-approximation* (never misses a reachable method). Output classifies every project method as reachable / accessor / unreached; the unreached set is a finding (framework-invoked entry points, cross-cutting handlers, or candidate-dead), not silence.

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
