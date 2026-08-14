"""
ML Accuracy Test: Golden Dataset Validation
This is the most important test for AI/ML systems. A 'golden dataset' is a curated set of 
known inputs and their expected outputs. We run the classifier against these inputs and 
assert that its accuracy meets a minimum threshold (80%).

At Jeevisoft, we use a similar concept — our AI-FALSE-POSITIVES-CATALOG.MD acts as a 
production golden dataset, injected directly into the LLM prompt to calibrate its accuracy.
"""


# Golden dataset: 10 known incidents with expected root cause categories.
# Each entry has the incident text (input) and the correct category (expected output).
# This dataset was curated by experienced SREs who manually classified each incident.
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

# Keyword lookup table: maps each category to a list of keywords that indicate it.
# This simulates what a real ML model does — but instead of learned neural weights,
# we use explicit keyword rules for simplicity and determinism.
CATEGORY_KEYWORDS = {
    "CPU": ["cpu", "load average", "processor"],
    "Memory": ["memory", "oom", "out of memory"],
    "Disk": ["disk", "mount", "capacity", "storage"],
    "Network": ["network", "connection", "timeout", "dns"],
    "Certificate": ["ssl", "certificate", "tls"],
    "Latency": ["latency", "slow", "response time"],
}


def classify_incident(incident_text: str) -> str:
    """
    Simple keyword-based classifier (simulating ML model output).
    
    In production, this would be a trained ML model (e.g., a fine-tuned BERT classifier).
    For this lab, we use keyword matching to demonstrate the golden dataset testing pattern
    without needing GPU infrastructure.
    """
    # Convert to lowercase so "CPU" matches "cpu".
    text_lower = incident_text.lower()

    # Check each category's keywords against the incident text.
    # The first category that matches wins (order matters!).
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category

    # If no keywords match, return "Unknown".
    # In a real system, this would trigger a human review.
    return "Unknown"


def test_golden_dataset_accuracy():
    """The classifier must achieve at least 80% accuracy on the golden dataset."""

    correct = 0
    total = len(GOLDEN_DATASET)

    # Run the classifier against every entry in the golden dataset.
    for test_case in GOLDEN_DATASET:
        predicted = classify_incident(test_case["incident"])
        # Compare the predicted category against the known correct answer.
        if predicted == test_case["expected_category"]:
            correct += 1

    # Calculate accuracy as a percentage (e.g., 9/10 = 0.9 = 90%).
    accuracy = correct / total

    # The minimum acceptable accuracy is 80%.
    # If a code change or model update drops accuracy below this threshold,
    # the CI/CD pipeline will FAIL and block the deployment.
    # This is how golden datasets prevent regressions in AI systems.
    assert accuracy >= 0.8, (
        f"Golden dataset accuracy is {accuracy:.0%} ({correct}/{total}). "
        f"Minimum required: 80%"
    )
