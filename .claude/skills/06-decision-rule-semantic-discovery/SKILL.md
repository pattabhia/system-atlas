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

## Branch reconciliation (completeness)
Consume the branch inventory (`java_ast.py --branches`) for every reachable method and **account for each arm**: map it to a decision, a behavior family, a business rule, or mark it explicitly trivial (presence guard / log-only). Branch enumeration is mechanical; classification is the reasoning. This routinely surfaces rules hidden inside helper methods (e.g. a password-composition formula in length-check branches) that a flow-level pass records only implicitly. Emit a branch-completeness reconciliation; never leave an arm unaccounted.

## Code catalogs (error / status / reason / endpoint codes)
Enum constants that carry domain semantics — error codes, status codes, reason codes, API endpoint names — are **catalogued as a set**, not left scattered across the catch blocks and setters that reference them. Extract them mechanically (`java_ast.py --errorcodes`) with their code + message literals, then record each code's meaning and where it is raised/written. This is the authoritative semantic source for status_comment values and thrown-exception codes. Flag anomalies the extraction reveals (e.g. two constants sharing one code). Emit an `error-code-catalog`.

## Silent-failure behavior (exception handling)
Exception handling IS behavior. Consume the handler analysis (`java_ast.py --exceptions`) and treat every **swallowing** catch (log-only, empty, or return null/false/default) as a materially-distinct outcome: the operation continues or reports success while an error is hidden. Each swallow becomes a behavior observation and, where it changes the operation's terminal outcome, a **behavior family** (hand to Skill 07 → projected to BDD by Skill 08). Do not discover these by ad-hoc reading — they are enumerated for you; classify and attach them. Emit an `exception-analysis`.

## Outputs
Decision/effect catalog; rule candidates; confirmed rules; semantic resolutions; value lineage; error-code catalog; exception/silent-failure analysis; semantic evidence; unresolved meanings and ambiguities.

## Guardrail
LLM confidence is not evidence. Every semantic claim must state why it is believed.
