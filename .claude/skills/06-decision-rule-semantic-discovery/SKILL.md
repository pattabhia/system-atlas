---
name: 06-decision-rule-semantic-discovery
description: Extract technical decisions and effects losslessly, trace value/semantic lineage, classify rule candidates, and resolve domain semantics using every accessible evidence source. Use to preserve condition-branch-effect before business interpretation, resolve the meaning of literals/codes/flags/enums with provenance, and qualify true business rules. Normally routed by the current-behavior-orchestrator, in a loop with Skills 04 and 05.
---

# Skill 06 — Decision, Rule & Semantic Discovery

## Mission
Extract technical decisions/effects losslessly, classify rule candidates, and resolve domain semantics using every accessible evidence source without assuming a relational or JVM stack.

## Technical Model
Preserve condition → branch → effect before attempting business interpretation.

```
SOURCE FACT
   ↓
DECISION / EFFECT
   ↓
RULE CANDIDATE
   ↓
BUSINESS RULE (only with evidence)
```

## Semantic Resolution
For any unresolved literal, identifier, code, status, flag, enum value or persisted value, search through active adapters across code constants/enums, configuration, persistence mappings, schema/reference data or NoSQL/document equivalents, data-store program objects, packaged libraries and downstream reads/usages.

**Unknown meaning does not mean unknown behavior.** Preserve literal truth if semantics cannot be established.

## Evidence Levels
L0 UNKNOWN; L1 INFERRED; L2 CORROBORATED; L3 AUTHORITATIVE.

## Business Rule Qualification
Require a decision/condition + domain-relevant consequence + business context. Not every branch, setter, guard clause or framework condition is a business rule.

## Outputs
Decision/effect catalog; rule candidates; confirmed rules; semantic resolutions; value lineage; semantic evidence; unresolved meanings and ambiguities.

## Guardrail
LLM confidence is not evidence. Every semantic claim must state why it is believed.
