---
name: 01-scope-operation-discovery
description: Establish what is being analyzed and detect the technology/stack context. Use as the first step of current-behavior discovery to set root scope, detect project vs operation mode, discover Stack Profile(s), bind adapter capabilities, seed traversal, and record capability gaps. Normally routed by the current-behavior-orchestrator.
---

# Skill 01 — Scope & Operation Discovery

## Mission
Establish exactly what is being analyzed and determine the technology context needed to inspect it.

## Technology Neutrality Invariant
Express discovery intent in technology-neutral terms. Delegate ecosystem mechanics to the active Stack Adapter. Technology names may appear only as adapter-specific documentation, never as discovery rules.

## First Step — Technology / Stack Profile Discovery
Detect one or more active stack profiles from available project artifacts. Capture language(s), build/dependency system(s), framework(s), data stores, messaging systems, packaging model and test framework where discoverable.

## Unsupported or Undetectable Stack
If a stack cannot be confidently identified, or one or more required adapter capabilities are unavailable, activate **degraded discovery mode** rather than stopping or guessing. Use generic text/source/configuration inspection capabilities where available, record each unsupported capability as an explicit capability gap, and propagate the limitation into traversal completeness and confidence.

## Inputs
Project/application scope, repository/workspace path, package/dependency identifiers when supplied, optional business operation name, and available organizational metadata.

## Responsibilities
- Detect project/application mode vs operation mode.
- Discover build/project manifests, source roots and logical modules/components using available adapter capabilities.
- Emit Stack Profile(s) and capability-to-adapter bindings.
- In project mode, identify candidate business operations for deeper analysis.
- In operation mode, locate likely operation anchors without assuming one function/method equals the whole business behavior.
- Establish artifact/version/environment scope and initial traversal seeds.
- Record unsupported or unavailable analysis capabilities explicitly.

## Outputs
Scope Manifest; Stack Profile(s); active capability bindings; component/module inventory; operation candidates or selected operation; initial traversal seeds; scope evidence; capability gaps; initial unresolved boundaries.

## Guardrails
Do not treat repository, package, class, function or module boundaries as business-operation boundaries. Do not invent operation semantics. Preserve ambiguity as evidence. Missing adapter support must never be silently ignored.

## Handoff
Pass scope, stack profile(s), operation identifiers, capability bindings, capability gaps and traversal seeds to Skills 02 and 03.
