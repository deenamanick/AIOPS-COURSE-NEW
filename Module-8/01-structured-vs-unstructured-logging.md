# 01 — Structured vs Unstructured Logging

Every production system produces logs. Whether a human or a machine can reliably extract meaning from those logs depends entirely on how they are structured. In this lesson, you will compare the two fundamental approaches and understand why structured logging is a prerequisite for automated correlation.

---

## Unstructured Logging

A traditional Nginx access log line looks like:

```text
192.168.1.42 - - [06/Aug/2026:14:01:23 +0000] "GET /api/users HTTP/1.1" 200 1534 "-" "curl/8.5.0" 0.042
```

This is human-readable, but a machine must parse it with a regular expression or a format-aware parser to extract the IP address, timestamp, HTTP method, path, status code, response time, and user agent. If the format changes—even slightly—the parser breaks silently.

### Problems with Unstructured Logs

| Problem | Consequence |
|---|---|
| Format is implicit | Every consumer must reverse-engineer the structure |
| Multi-line exceptions | Stack traces break line-by-line parsers |
| No standard field names | `status_code` vs `statusCode` vs `status` |
| No embedded context | Hostname, service name, and trace ID are absent |
| Difficult to query | `grep` works, but Boolean combinations are fragile |

---

## Structured Logging (JSON)

The same event as structured JSON:

```json
{
  "timestamp": "2026-08-06T14:01:23Z",
  "level": "info",
  "service": "nginx",
  "hostname": "web-01",
  "client_ip": "192.168.1.42",
  "method": "GET",
  "path": "/api/users",
  "status": 200,
  "body_bytes": 1534,
  "response_time_ms": 42,
  "user_agent": "curl/8.5.0",
  "trace_id": "abc123def456"
}
```

### Advantages

- **Self-describing**: field names travel with the data.
- **Machine-parseable**: `json.loads()` or `jq` work without custom regex.
- **Enrichable**: add `hostname`, `service`, `trace_id` at emit time.
- **Queryable**: filter on any field combination.
- **Correlation-ready**: `trace_id` links logs across services.

---

## When Each Applies

| Situation | Recommendation |
|---|---|
| Application code you control | Emit structured JSON from the start |
| Third-party software (Nginx, Postgres) | Use built-in JSON log formats or parse to JSON at ingestion |
| Legacy systems with fixed formats | Parse at a sidecar or pipeline stage (Fluentd, Vector, Logstash) |
| Local development debugging | Human-readable is fine; switch to JSON in staging and production |

---

## Lab: Compare the Two Formats

The lab stack emits both plain-text and JSON Nginx logs simultaneously.

```bash
cd Module-8/lab
docker compose up -d --build
```

Generate traffic:

```bash
for i in $(seq 1 50); do
  curl -s http://localhost:8080/ > /dev/null
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s http://localhost:8080/slow > /dev/null
  curl -s http://localhost:8080/error > /dev/null
done
```

Inspect the plain-text log:

```bash
docker compose exec nginx cat /var/log/nginx/access.log | head -5
```

Inspect the JSON log:

```bash
docker compose exec nginx cat /var/log/nginx/access_json.log | head -5 | python3 -m json.tool
```

### Questions

1. Which format is easier to filter for requests slower than 100 ms?
2. Which format can a Python `json.loads()` call parse without a regex?
3. If you add a new field (e.g., `request_id`), which format requires updating every downstream parser?

---

## Key Takeaway

Structured logging is not a luxury—it is the foundation of automated log analytics. Every lesson that follows assumes logs are structured JSON. If your source is plain text, the first step is always: **parse it into structure**.

In the next lesson, you will build a Python parser that converts raw Nginx access logs into structured JSON and enriches them with context.
