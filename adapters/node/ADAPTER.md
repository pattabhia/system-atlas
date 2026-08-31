# Adapter — node (scaffold)

**Kind:** language / build · **Binds when:** Stack Profile language = JS/TS, build = npm/pnpm/yarn.
**Status:** SCAFFOLD — capability contract defined; implementations pending.

| Capability | Tool (free/OSS) |
|-----------|------|
| resolve_project_structure / resolve_dependencies | `package.json` + lockfile, `npm ls` |
| inspect_packaged_artifact | `node_modules` resolution |
| build_source_model / build_call_graph | **ts-morph** / TS compiler API (typed) or **tree-sitter-typescript** (parse) |
| discover_entrypoints | route scan (Express `app.get`, Nest `@Controller`, Fastify, serverless handlers) |
| run_characterization_tests | `jest` / `vitest` |

Infra capabilities bind per boundary kind. Until built, binds to generic-fallback with a capability gap.
