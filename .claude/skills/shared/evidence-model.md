# Shared — Evidence & Gap Model

Every skill writes evidence, provenance, uncertainty and gaps into one shared model.

## Status Vocabulary
```
✓ PROVEN       source-backed fact
~ INFERRED     interpretation supported but not authoritative
? UNKNOWN      semantic meaning unresolved
⚠ AMBIGUOUS    multiple plausible targets/interpretations
✗ MISSING      required artifact unavailable
→ UNRESOLVED   behavior-relevant boundary not resolved
⊘ CAPABILITY   requested analysis capability unavailable/partial
```

**Invariant:** Unknown is a valid result. Guessing is not.

### `→ UNRESOLVED` vs `⊘ CAPABILITY`
These can co-occur on the same behavior and must not be conflated:
- `→ UNRESOLVED` attaches to a **boundary** — a specific target the traversal could not resolve (a JAR without source, an unreachable service, an unknown topic consumer).
- `⊘ CAPABILITY` attaches to a **capability** — an analysis operation that had no specialized adapter and ran in fallback or not at all (no call-graph builder for a stack, no datastore inspector).

A behavior may carry both: e.g. a boundary is unresolved *because* the capability needed to resolve it was unavailable.

## Evidence Levels (semantics)
`L0 UNKNOWN`; `L1 INFERRED`; `L2 CORROBORATED`; `L3 AUTHORITATIVE`.

## Resolution Levels (boundaries)
`L0 Unknown`; `L1 Target identified`; `L2 Contract resolved`; `L3 Source resolved`; `L4 Fully resolved (source + config + verification)`.

## Provenance Requirement
Every claim states **why it is believed**, with a pointer to the source construct, artifact, config, schema object or downstream usage that backs it. LLM confidence is not evidence.
