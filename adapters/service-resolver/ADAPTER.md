# Adapter — service-resolver

**Kind:** integration / cross-cutting
**Binds when:** a boundary of kind *synchronous service call* is reached — an HTTP/REST client call, a gRPC stub call, a declarative client (Feign/Retrofit/OpenFeign), or a resolved service URL from config. Bound **by boundary kind**, not by the caller's language.
**Implements:** `resolve_service_target`.
**Tools:** `Read`, `Grep`, `find`; optional `python3` (+ `pyyaml`) for the OpenAPI indexer.

Its job: take a *client-side* call (base URL + path template + HTTP method, or gRPC `service/method`) and resolve the **serving endpoint** — often in another repository — so traversal can continue into the provider. It does **not** re-scan source for endpoints per language; it consumes the **entry-point catalog** the language adapter's `discover_entrypoints` already produced, plus contracts (OpenAPI/proto) and configuration.

Emit results per the [Adapter Output Contract](../../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract).

---

## resolve_service_target — Tier 1 (+ optional Tier-2 indexer)

### 1. Characterize the client call
From the call site + `resolve_configuration` output, extract: base URL / host (usually a `${placeholder}` resolved from config or service discovery), path template, HTTP method, and body/params. For declarative clients, read the interface annotations:
```bash
grep -rEn '@FeignClient|@RetrofitClient|WebClient|RestTemplate|HttpClient|@GET|@POST|@PUT|@DELETE|\.newBlockingStub\(|ManagedChannel' <root>
```
Record the **logical service name** (e.g. Feign `name=`/`url=`, config key, k8s service host) even when the physical URL is environment-specific.

### 2. Resolve the provider contract
Prefer an explicit contract when present:
- **REST/OpenAPI:** find and index specs, then match method+path.
  ```bash
  find . -iname 'openapi*.y*ml' -o -iname 'swagger*.json' -o -iname '*api-docs*'
  python3 scripts/openapi_index.py <spec-or-dir> > openapi-index.json
  ```
- **gRPC:** parse `.proto` — `service <S> { rpc <M>(<Req>) returns (<Resp>); }`.
  ```bash
  grep -rEn 'service +[A-Za-z0-9_]+|rpc +[A-Za-z0-9_]+' --include='*.proto' .
  ```

### 3. Match client → provider
Match by (normalized path template + method) against the provider's OpenAPI index **or** the target repo's entry-point catalog (Skill 03 output). Normalize path variables (`/accounts/{id}` ≡ `/accounts/:id` ≡ `/accounts/%s`). Resolution levels:
- provider endpoint located **with source** (entry-point catalog in a resolved repo) → **L3**
- contract matched (OpenAPI/proto) but source not reachable → **L2**
- only the target service/host identified → **L1**
- nothing → **L0**, record a boundary gap.

### 4. Cross-repo / cross-ecosystem
If the provider lives in another repository, request the orchestrator to enqueue that repo (Skill 05) and, if it is a different stack, rebind capabilities for that subtree. Hand the matched endpoint back to Skill 04 to continue traversal into the provider.

## Outputs
Client call descriptor; logical service name; provider endpoint (method+path/rpc) with source location where resolved; contract reference (OpenAPI operationId / proto rpc); resolution level; discovered next targets (provider repo); unresolved/ambiguous/access gaps.

## Guardrails
- A config placeholder that cannot be resolved to a concrete target → `? UNKNOWN` host, keep the logical name; do not invent a URL.
- Multiple providers matching one path template → `⚠ AMBIGUOUS`, list candidates; do not pick one.
- Never call/probe a live endpoint to resolve it — resolution is static.
