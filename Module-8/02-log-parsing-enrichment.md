# 02 — Log Parsing & Enrichment

Raw logs from third-party software such as Nginx arrive in a fixed plain-text format. Before you can correlate, aggregate, or alert on them, you must extract individual fields and add contextual metadata. This lesson builds a Python log parser and enrichment pipeline.

---

## Nginx Combined Log Format

The default Nginx `combined` format produces lines like:

```text
192.168.1.42 - - [06/Aug/2026:14:01:23 +0000] "GET /api/users HTTP/1.1" 200 1534 "-" "curl/8.5.0"
```

The lab extends this with `$request_time` appended, so the format becomes:

```text
<client_ip> - - [<timestamp>] "<method> <path> <protocol>" <status> <body_bytes> "<referer>" "<user_agent>" <request_time>
```

---

## The Parser

The lab includes `lab/scripts/log_parser.py`. The core logic:

```python
import re, json, sys
from datetime import datetime

PATTERN = re.compile(
    r'(?P<client_ip>\S+) \S+ \S+ '
    r'\[(?P<timestamp>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<body_bytes>\d+) '
    r'"[^"]*" "(?P<user_agent>[^"]*)"'
    r'(?: (?P<request_time>[\d.]+))?'
)

def parse_line(line: str) -> dict | None:
    m = PATTERN.match(line)
    if not m:
        return None
    d = m.groupdict()
    d["status"] = int(d["status"])
    d["body_bytes"] = int(d["body_bytes"])
    d["request_time_ms"] = int(float(d.pop("request_time") or "0") * 1000)
    d["timestamp"] = datetime.strptime(
        d["timestamp"], "%d/%b/%Y:%H:%M:%S %z"
    ).isoformat()
    return d
```

Each line becomes a dictionary with typed fields. The timestamp is normalized to ISO 8601 for cross-service alignment.

---

## Enrichment

Parsing extracts what is in the log. Enrichment adds what is **not** in the log but is known from the environment:

```python
import os, uuid

def enrich(entry: dict) -> dict:
    entry["hostname"] = os.environ.get("HOSTNAME", "unknown")
    entry["service"] = "nginx"
    entry["environment"] = os.environ.get("ENVIRONMENT", "training")
    entry["trace_id"] = entry.get("trace_id") or str(uuid.uuid4())
    return entry
```

In production, enrichment adds:

| Field | Source |
|---|---|
| `hostname` | Container hostname or EC2 instance metadata |
| `service` | Deployment label or environment variable |
| `environment` | `staging`, `production`, `training` |
| `trace_id` | Propagated from the request header (`X-Request-ID`) |
| `region` | Cloud metadata API |
| `deploy_sha` | Git SHA baked into the container at build time |

---

## Lab: Parse and Analyze Nginx Logs

Generate traffic first:

```bash
cd Module-8/lab
docker compose up -d --build

# Mixed traffic: success, slow, and error
for i in $(seq 1 200); do
  curl -s http://localhost:8080/ > /dev/null
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s http://localhost:8080/slow > /dev/null
  curl -s http://localhost:8080/error > /dev/null
done
```

Run the parser:

```bash
docker compose exec nginx cat /var/log/nginx/access.log \
  | python3 lab/scripts/log_parser.py > parsed_logs.json
```

### Analysis Tasks

**Top 10 slowest endpoints:**

```bash
cat parsed_logs.json | python3 -c "
import json, sys
entries = [json.loads(l) for l in sys.stdin]
ranked = sorted(entries, key=lambda e: e['request_time_ms'], reverse=True)[:10]
for e in ranked:
    print(f\"{e['request_time_ms']:>6}ms  {e['method']} {e['path']}  → {e['status']}\")
"
```

**Error rate per endpoint:**

```bash
cat parsed_logs.json | python3 -c "
import json, sys
from collections import defaultdict
totals = defaultdict(int)
errors = defaultdict(int)
for line in sys.stdin:
    e = json.loads(line)
    totals[e['path']] += 1
    if e['status'] >= 500:
        errors[e['path']] += 1
for path in sorted(totals):
    rate = (errors[path] / totals[path]) * 100
    print(f\"{path:<30} {totals[path]:>5} reqs  {rate:5.1f}% error rate\")
"
```

---

## Why This Matters for Correlation

Structured, enriched logs enable:

- Filtering by `status >= 500` and `request_time_ms > 1000` simultaneously.
- Joining logs across services using `trace_id`.
- Grouping by `hostname` to identify a single bad node.
- Feeding the correlation engine (next lesson) with typed, timestamped events.

---

## Validation Checklist

- [ ] The parser handles every line in the access log without errors.
- [ ] Output is valid JSON (one object per line).
- [ ] Timestamps are in ISO 8601 format.
- [ ] Enrichment adds `hostname`, `service`, and `environment`.
- [ ] Top 10 slowest endpoints and error rate per endpoint are calculated.
