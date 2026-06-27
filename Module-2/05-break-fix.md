# 05 — Break/Fix Exercises

Hands-on troubleshooting practice. For each exercise: **Break** → **Detect** → **Diagnose** → **Fix** → **Verify**.

These exercises simulate real production failures in an AI-powered operations pipeline.

---

## Exercise 1: Kill the Streamlit Container

### Break
```bash
vagrant ssh aiops-control
cd /opt/module2-lab

docker compose stop aiops-assistant
```

### Detect
```bash
# From host browser: http://localhost:8501 → connection refused

# From inside the VM:
curl http://localhost:8501
# → curl: (7) Failed to connect to localhost port 8501: Connection refused
```

### Diagnose
```bash
# Check container status
docker compose ps
# → module2-assistant shows "Exited"

# Check logs — was there a crash?
docker compose logs aiops-assistant
```

### Fix
```bash
docker compose start aiops-assistant
```

### Verify
```bash
docker compose ps
# → module2-assistant shows "Up (healthy)"

curl -s http://localhost:8501 | head -5
# → HTML output from Streamlit
```

---

## Exercise 2: Corrupt the Incident Data

### Break
```bash
vagrant ssh aiops-control
cd /opt/module2-lab

# Overwrite incidents.csv with garbage data
echo "id,timestamp,service,severity,description,root_cause,resolution" > incidents.csv
echo "INC-9999,2024-01-01,broken,P1,aaaa bbbb cccc,unknown,unknown" >> incidents.csv

# Restart to reload the data
docker compose restart
```

### Detect
Open `http://localhost:8501` and search for "database connection pool exhausted".

You should see:
- Vector search returns nonsensical matches (only 1 garbage record exists)
- LLM generates a confused or low-confidence RCA

### Diagnose
```bash
# Check the CSV — is the data valid?
wc -l incidents.csv
# → 2 (header + 1 garbage row — should be 101)

cat incidents.csv
# → Only garbage data
```

### Fix
```bash
# Regenerate the dataset
python3 generate_incidents.py
# → "Successfully generated incidents.csv with 100 records."

# Restart the container to reload the new data
docker compose restart
```

### Verify
```bash
wc -l incidents.csv
# → 101

# Open the UI and search again — results should be relevant now
```

---

## Exercise 3: Revoke the OpenAI API Key

### Break
```bash
vagrant ssh aiops-control
cd /opt/module2-lab

# Set an invalid API key
echo "OPENAI_API_KEY=sk-invalid-key-12345" > .env

docker compose restart
```

### Detect
Open `http://localhost:8501` and search for any incident. Click **Analyze Incident**.

- **Vector Search:** ✅ Should still work (ChromaDB doesn't use OpenAI)
- **LLM RCA:** ❌ Will show an error like `"Error connecting to LLM: Incorrect API key provided"`

### Diagnose
```bash
# Check the .env file
cat .env
# → OPENAI_API_KEY=sk-invalid-key-12345

# Check container logs for the error
docker compose logs aiops-assistant | grep -i "error"
```

**Key Insight:** The vector search and the LLM are **decoupled**. When OpenAI is down or the key is bad, you still get historical incident matches. You just lose the auto-generated RCA.

### Fix
```bash
# Restore the correct API key
echo "OPENAI_API_KEY=sk-your-real-key-here" > .env

docker compose restart
```

### Verify
Open the UI, search for an incident, and confirm the LLM generates a proper RCA report.

---

## Exercise 4: Disk Full Simulation

### Break
```bash
vagrant ssh aiops-control

# Create a 500MB file to eat up disk space
dd if=/dev/zero of=/tmp/disk_fill bs=1M count=500
```

### Detect
```bash
df -h /
# → Disk usage jumps significantly

# The container may start logging errors:
docker compose logs aiops-assistant | tail -10
```

### Diagnose
```bash
# What's consuming space?
du -sh /tmp/* | sort -rh | head -5
# → /tmp/disk_fill    500M

# Is the container affected?
docker compose ps
# → May show "unhealthy" if disk prevents writing
```

### Fix
```bash
rm /tmp/disk_fill
```

### Verify
```bash
df -h /
# → Usage drops back to normal

docker compose restart
docker compose ps
# → "Up (healthy)"
```

---

## Exercise 5: Semantic Search Accuracy Test

This is a different kind of "break" — we test the **intelligence** of the pipeline.

### The Test
Open `http://localhost:8501` and run these 3 queries. Record what happens:

#### Test A: Semantically Similar (Different Words)
Enter:
> **"The billing server processor is pegged at 99% and the JVM is struggling to clear memory objects."**

**Expected:** ChromaDB should find "High CPU utilization on billing-api due to heavy garbage collection" even though the words are completely different. The LLM should identify the root cause as a memory leak.

#### Test B: Completely Unrelated Query
Enter:
> **"How do I bake a chocolate cake?"**

**Expected:** ChromaDB will still return its closest 3 matches (it always returns results), but the distances should be **very high** (>1.0). The LLM should recognize the irrelevance and refuse to generate a fake RCA.

#### Test C: Ambiguous Multi-Service Alert
Enter:
> **"Everything is slow. Multiple teams are complaining."**

**Expected:** ChromaDB should return a mix of incidents across different services. The LLM should note the ambiguity and suggest investigating multiple possible causes.

### Results Table

| Test | ChromaDB Matched? | Distance Score | LLM RCA Accurate? | LLM Confidence |
|---|---|---|---|---|
| A (semantic match) | _(record)_ | _(record)_ | _(record)_ | _(record)_ |
| B (unrelated) | _(record)_ | _(record)_ | _(record)_ | _(record)_ |
| C (ambiguous) | _(record)_ | _(record)_ | _(record)_ | _(record)_ |

---

## Summary Table

| Exercise | What Broke | How You Detected | Key Command |
|---|---|---|---|
| Container stopped | UI unreachable | `docker compose ps` | `docker compose start` |
| Corrupt CSV | Bad search results | `wc -l incidents.csv` | `python3 generate_incidents.py` |
| Bad API key | LLM error, vector search still works | `cat .env`, container logs | Fix `.env`, restart |
| Disk full | Container unhealthy | `df -h` | `rm <large file>` |
| Semantic test | N/A — intelligence test | Compare distances and RCA quality | Evaluate output |

---

## Key Takeaway

The diagnostic pattern carries over from Module 1:
1. **What's the symptom?** (UI unreachable, bad results, LLM error)
2. **Is the service running?** (`docker compose ps`)
3. **What do the logs say?** (`docker compose logs`)
4. **What's the data state?** (`wc -l incidents.csv`, `cat .env`)
5. **Fix and verify** (regenerate data, fix key, restart)

**New in Module 2:** The vector search and LLM are **decoupled**. When one breaks, the other can still function. This is a core resilience principle in production AI systems.

---

## What's Next

Proceed to **06-cost-and-performance.md** to understand the production economics of running AI-powered operations.
