# Adapter — dotnet (scaffold)

**Kind:** language / build · **Binds when:** Stack Profile language = C#/.NET, build = MSBuild/NuGet.
**Status:** SCAFFOLD — capability contract defined; implementations pending.

Implements the language/source capabilities of the [Stack Adapter Contract](../../.claude/skills/shared/stack-adapter-contract.md) for .NET. Tooling map (free/OSS):

| Capability | Tool |
|-----------|------|
| resolve_project_structure / resolve_dependencies | `dotnet list package`, `.csproj`/`.sln`, `packages.lock.json` |
| inspect_packaged_artifact | `ildasm` / `Mono.Cecil` (DLL/IL) |
| build_source_model / build_call_graph | **Roslyn** (Microsoft.CodeAnalysis) — symbol-solved, MIT |
| discover_entrypoints | Roslyn attribute scan (`[ApiController]`, `[HttpGet]`, minimal APIs, `[Function]`, hosted services) |
| trace_data_state_flow | Roslyn dataflow APIs |
| run_characterization_tests | `dotnet test` (xUnit/NUnit/MSTest) |

Cross-cutting `inspect_datastore` / `resolve_service_target` / `resolve_event_target` bind per boundary kind (relational-db, service-resolver, event-resolver), same as java-maven.
Until built, .NET boundaries bind to generic-fallback with a recorded capability gap.
