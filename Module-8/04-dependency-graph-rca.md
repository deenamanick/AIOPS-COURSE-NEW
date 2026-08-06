# 04 — Dependency Graphs & Root Cause Analysis

Time-window correlation tells you that three alerts belong to one incident. It does not tell you **which alert is the root cause** and which are symptoms. For that, you need a model of how your services depend on each other.

---

## What Is a Dependency Graph?

A dependency graph is a directed acyclic graph (DAG) where:

- **Nodes** represent services, infrastructure, or components.
- **Edges** represent "depends on" relationships.

```text
  User
    │
    ▼
  Nginx ──► Flask App ──► PostgreSQL
                │
                ▼
             Redis Cache
```

If PostgreSQL fails, Flask App will produce 5xx errors, Nginx will forward those 5xx responses, and users will see errors. The **root cause** is the deepest node in the dependency chain that is alerting.

---

## Graph Representation

The lab uses a simple Python dictionary:

```python
DEPENDENCY_MAP = {
    "user-frontend": ["nginx"],
    "nginx": ["flask-app"],
    "flask-app": ["postgres", "redis"],
    "postgres": [],
    "redis": [],
}
```

Each key depends on its values. `flask-app` depends on both `postgres` and `redis`. Services with empty dependency lists are leaf nodes—infrastructure with no further downstream dependencies.

### Depth Calculation

```python
def get_depth(service: str, graph: dict, cache: dict = None) -> int:
    """Depth = how deep this service sits in the dependency chain.
    Deeper services are more likely to be root causes."""
    if cache is None:
        cache = {}
    if service in cache:
        return cache[service]
    deps = graph.get(service, [])
    if not deps:
        cache[service] = 0
        return 0
    depth = 1 + max(get_depth(d, graph, cache) for d in deps)
    cache[service] = depth
    return depth
```

| Service | Depth |
|---|---|
| `postgres` | 0 (leaf) |
| `redis` | 0 (leaf) |
| `flask-app` | 1 |
| `nginx` | 2 |
| `user-frontend` | 3 |

---

## Root Cause Analysis Algorithm

Given a correlated incident (from the previous lesson), the RCA algorithm:

```text
1. Take all alerts in the incident.
2. Map each alert to its service in the dependency graph.
3. For each alerting service, calculate its depth.
4. The alerting service with the LOWEST depth (deepest in the stack) is the root cause.
5. All other alerting services are symptoms.
```

### Implementation

```python
def identify_root_cause(incident_alerts: list[dict], graph: dict) -> dict:
    """Given a list of correlated alerts and a dependency graph,
    identify the root cause and symptom alerts."""
    
    # Map alerts to services and calculate depths
    alert_depths = []
    for alert in incident_alerts:
        service = alert["service"]
        depth = get_depth(service, graph)
        alert_depths.append((depth, alert))
    
    # Sort by depth ascending — lowest depth = deepest dependency = root cause
    alert_depths.sort(key=lambda x: x[0])
    
    root_cause = alert_depths[0][1]
    symptoms = [a[1] for _, a in alert_depths[1:] if _ > alert_depths[0][0]]
    
    return {
        "root_cause": root_cause["alertname"],
        "root_service": root_cause["service"],
        "symptoms": [a["alertname"] for a in symptoms],
        "reasoning": f"{root_cause['service']} is the deepest alerting dependency"
    }
```

---

## Lab: Build the RCA Pipeline

```bash
cd Module-8/lab
docker compose up -d --build
```

Trigger the cascading failure:

```bash
# Make the database slow (simulates disk I/O pressure)
curl -X POST http://localhost:5000/drill/db-slow

# Generate traffic that will cascade through the stack
sleep 30
for i in $(seq 1 200); do
  curl -s http://localhost:8080/api/users > /dev/null
done
```

The correlation engine groups the alerts, then the RCA module runs:

```bash
docker compose logs -f correlation-engine
```

Expected output:

```text
[CORRELATOR] Incident #1 closed — 3 alerts correlated in 120s window
[RCA] Analyzing incident #1...
[RCA]   Alert DB_LATENCY      → service: postgres    (depth: 0)
[RCA]   Alert APP_5XX         → service: flask-app   (depth: 1)
[RCA]   Alert USER_COMPLAINTS → service: nginx       (depth: 2)
[RCA] ─────────────────────────────────────────────────────────
[RCA] ROOT CAUSE:  DB_LATENCY (postgres)
[RCA] SYMPTOMS:    APP_5XX, USER_COMPLAINTS
[RCA] REASONING:   postgres is the deepest alerting dependency
```

### Visualize the Graph

The lab also outputs a simple ASCII dependency visualization:

```text
[RCA] Dependency chain:
[RCA]   user-frontend → nginx → flask-app → [postgres] ← ROOT CAUSE
[RCA]                                      → redis (healthy)
```

---

## Limitations of Static Dependency Graphs

| Limitation | Mitigation |
|---|---|
| Graph must be maintained manually | Auto-discover from service mesh or tracing |
| Cannot model transient dependencies | Use dynamic graphs from distributed tracing |
| Multiple leaf nodes may alert simultaneously | Use alert timing and severity as tie-breakers |
| Graph does not capture partial degradation | Combine with metric severity thresholds |

Production systems such as PagerDuty Event Intelligence and ServiceNow ITOM automate graph construction from CMDB, tracing, and network topology. This lab builds the concept manually so you understand the algorithm before delegating it to a platform.

---

## Debrief

- What happens if both `postgres` and `redis` alert at the same time? (Two leaf nodes at depth 0.)
- How would you modify the algorithm to handle that case?
- What if a service is not in the dependency map? Should the engine crash or treat it as unknown?
- In your production environment, what data source would you use to build the dependency graph?

In the next lesson, you will decouple alert ingestion from correlation using an event-driven pub/sub architecture.
