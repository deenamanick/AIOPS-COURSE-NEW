"""ML Accuracy Test: Validate model performance against a golden dataset of known incidents."""


# Golden dataset: 10 known incidents with expected root cause categories
GOLDEN_DATASET = [
    {"incident": "CPU at 98% on web-server-01 for 15 minutes", "expected_category": "CPU"},
    {"incident": "Out of memory killed process nginx pid 1234", "expected_category": "Memory"},
    {"incident": "Disk /dev/sda1 at 95% capacity on db-server-02", "expected_category": "Disk"},
    {"incident": "Connection timeout to database on port 5432", "expected_category": "Network"},
    {"incident": "SSL certificate expired for api.example.com", "expected_category": "Certificate"},
    {"incident": "High latency 2500ms on payment gateway API", "expected_category": "Latency"},
    {"incident": "Pod CrashLoopBackOff due to OOMKilled exit code 137", "expected_category": "Memory"},
    {"incident": "DNS resolution failed for internal service mesh", "expected_category": "Network"},
    {"incident": "NFS mount point /data/shared became read-only", "expected_category": "Disk"},
    {"incident": "Load average 12.5 on 4-core application server", "expected_category": "CPU"},
]

CATEGORY_KEYWORDS = {
    "CPU": ["cpu", "load average", "processor"],
    "Memory": ["memory", "oom", "out of memory"],
    "Disk": ["disk", "mount", "capacity", "storage"],
    "Network": ["network", "connection", "timeout", "dns"],
    "Certificate": ["ssl", "certificate", "tls"],
    "Latency": ["latency", "slow", "response time"],
}


def classify_incident(incident_text: str) -> str:
    """Simple keyword-based classifier (simulating ML model output)."""
    text_lower = incident_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "Unknown"


def test_golden_dataset_accuracy():
    """The classifier must achieve at least 80% accuracy on the golden dataset."""
    correct = 0
    total = len(GOLDEN_DATASET)

    for test_case in GOLDEN_DATASET:
        predicted = classify_incident(test_case["incident"])
        if predicted == test_case["expected_category"]:
            correct += 1

    accuracy = correct / total
    assert accuracy >= 0.8, (
        f"Golden dataset accuracy is {accuracy:.0%} ({correct}/{total}). "
        f"Minimum required: 80%"
    )
