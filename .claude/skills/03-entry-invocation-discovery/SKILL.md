---
name: 03-entry-invocation-discovery
description: Find where behavior can begin and map technical invocation points to candidate business operations. Use to catalog HTTP/RPC endpoints, message/event consumers, schedulers, batch jobs, CLI/command handlers, serverless triggers and framework hooks, with source provenance and input contracts. Normally routed by the current-behavior-orchestrator.
---

# Skill 03 — Entry & Invocation Discovery

## Mission
Find where behavior can begin and map technical invocation points to candidate business operations using the active stack adapters.

## Discover
HTTP/RPC endpoints; message/event consumers; schedulers; batch jobs; CLI/command handlers; serverless/function triggers; framework hooks/callbacks; public library APIs; and other externally or internally invokable boundaries.

## Responsibilities
- Ask the active adapter for ecosystem-specific invocation discovery (`discover_entrypoints`).
- Map each entry point to source provenance, input contract and invocation mechanism.
- Associate entry points with candidate operations without assuming technical names equal business meaning.
- In project mode, use entry points to discover the operation landscape.
- In operation mode, resolve all known entry points capable of initiating the supplied operation.

## Outputs
Entry-point catalog; operation mapping; invocation mechanism; source provenance; input contract; confidence/evidence level; unresolved invocation paths.

## Guardrail
An entry point is a technical start. It is not automatically the business start, business boundary or business end.
