---
name: 02-artifact-dependency-discovery
description: Discover every artifact that may participate in the scoped project/operation and construct the dependency topology, independent of ecosystem. Use to parse build/dependency manifests, resolve effective package coordinates and versions, classify internal vs third-party vs data-store artifacts, and flag version drift. Normally routed by the current-behavior-orchestrator after Skill 01.
---

# Skill 02 — Artifact & Dependency Discovery

## Mission
Discover every artifact that may participate in the scoped project/operation and construct the dependency topology without assuming a specific ecosystem.

## Technology Neutrality Invariant
Reference neutral capabilities such as dependency manifest resolution, package inspection and version resolution. Ecosystem-specific mechanics belong to Stack Adapters.

## Responsibilities
- Parse build/dependency manifests and lockfiles through the active adapter.
- Resolve effective package/dependency coordinates and versions, including inheritance/imports/properties/profiles where the ecosystem supports them.
- Discover logical components/modules/packages and source roots.
- Classify same-repository components, internal packages/libraries, third-party packages, data-store artifacts, configuration and integration contracts.
- Discover repository/source mappings where evidence permits.
- Distinguish the possible dependency graph from behavior actually reached during traversal.

## Version Invariant
If the active manifest requires package version X, do not silently analyze version Y. Resolve matching source/tag/package/binary where possible; otherwise register version drift and its behavioral impact.

## Outputs
Artifact inventory; component/package dependency graph; ownership classification; resolved versions; source/repository candidates; evidence; unresolved artifacts and version gaps.

## Handoff
Feed discovered artifacts and package coordinates to entry discovery (Skill 03), traversal (Skill 04) and the boundary resolver (Skill 05).
