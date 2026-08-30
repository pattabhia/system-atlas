# Adapter — event-resolver

**Kind:** integration / cross-cutting
**Binds when:** a boundary of kind *asynchronous message/event* is reached — a Kafka publish/subscribe, JMS/RabbitMQ send/listen, SQS/SNS, or an event-bus emit. Bound **by boundary kind**, not by the caller's language.
**Implements:** `resolve_event_target`.
**Tools:** `Read`, `Grep`, `find`; optional `python3` for the correlation helper.

Its job: turn an async boundary into a **producer → destination → consumer(s)** resolution across repositories, so traversal continues from a publish into the consumer(s) that react to it. The break in the call chain (fire-and-forget) is exactly where naive analysis stops — this adapter re-links it by **destination name**.

Emit results per the [Adapter Output Contract](../../.claude/skills/shared/stack-adapter-contract.md#adapter-output-contract).

---

## resolve_event_target — Tier 1 (+ optional Tier-2 correlation)

### 1. Collect producers
Producer side = code that publishes to a destination. Get the destination (topic/queue/exchange+routing-key) — usually a `${placeholder}` resolved via `resolve_configuration`.
```bash
grep -rEn 'KafkaTemplate|\.send\(|StreamBridge|@SendTo|kafkaProducer|SnsClient|SqsClient|rabbitTemplate|jmsTemplate|@Output' <root>
```
Record `{destination, ref (class#method), source}` per producer.

### 2. Collect consumers
Consumer side already appears in the entry-point catalog (Skill 03) — reuse it. Otherwise:
```bash
grep -rEn '@KafkaListener|@JmsListener|@RabbitListener|@SqsListener|@StreamListener|@KafkaHandler|MessageListener|@Incoming' <root>
```
Record `{destination, group (consumer group / subscription), ref, source}` per consumer.

### 3. Resolve destination names
Destinations are frequently indirected through config or constants. Resolve each `${topic.name}` / constant to its literal via `resolve_configuration` and code constants **before** matching. Keep the logical name when the literal is environment-specific.

### 4. Correlate producers ↔ consumers
```bash
python3 scripts/topic_match.py --producers producers.json --consumers consumers.json \
        [--config resolved-config.json] > event-links.json
```
Matching is by resolved destination (exact), then by normalized/logical name. Resolution levels:
- destination + consumer(s) located with source → **L3**
- destination named, contract (AsyncAPI/schema) matched, consumer source not reachable → **L2**
- destination identified, no consumer found in scope → **L1** + boundary gap ("consumer outside analyzed scope")
- unresolved destination → **L0**.

Also check **AsyncAPI** specs when present:
```bash
find . -iname 'asyncapi*.y*ml' -o -iname 'asyncapi*.json'
```

### 5. Cross-repo / fan-out
One destination may have **many** consumers in **different** repositories — enqueue each (Skill 05), rebind capabilities per target stack, and hand every consumer entry point back to Skill 04. A publish with no in-scope consumer is a legitimate `→ UNRESOLVED` boundary, not an error.

## Outputs
Producer catalog; consumer catalog; resolved destinations; producer→consumer link set (with fan-out); consumer groups/subscriptions; schema/AsyncAPI references; resolution levels; unresolved/out-of-scope/ambiguous gaps; discovered next targets (consumer repos).

## Guardrails
- Unresolved topic placeholder → `? UNKNOWN` destination; do not assume a name.
- Fan-out is expected: never collapse multiple consumers into one.
- A producer with no discoverable consumer is `→ UNRESOLVED` (consumer may be an external system), recorded, not dropped.
- Never publish a test message to resolve wiring — resolution is static.
