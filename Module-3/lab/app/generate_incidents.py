import csv
import random
from datetime import datetime, timedelta

def generate_incidents(num_incidents=50):
    services = ["billing-api", "user-auth", "inventory-db", "frontend-web", "payment-gateway"]
    severities = ["P1", "P2", "P3", "P4"]
    
    # Pre-defined templates for realistic IT ops issues
    issue_templates = [
        {"desc": "High CPU utilization on {} due to heavy garbage collection.", "rc": "Memory leak in Java microservice.", "res": "Restarted pods and applied patch for memory leak."},
        {"desc": "Database connection pool exhausted in {}.", "rc": "Unclosed connections in legacy API endpoint.", "res": "Increased pool size and fixed unclosed connections in code."},
        {"desc": "SSL Certificate expired on {}.", "rc": "Automated renewal script failed due to permissions.", "res": "Manually renewed cert and fixed cronjob permissions."},
        {"desc": "API latency spiked to 5000ms on {}.", "rc": "Missing index on users table causing full table scans.", "res": "Created covering index on users table."},
        {"desc": "Out of Memory (OOM) killer terminated process in {}.", "rc": "Node process consuming excess RAM during bulk export.", "res": "Optimized export query and increased pod memory limits."},
        {"desc": "502 Bad Gateway errors on {}.", "rc": "Upstream service crashed and failed health checks.", "res": "Rolled back recent deployment that introduced crash."},
        {"desc": "Disk space full on {} volume.", "rc": "Log rotation was not configured properly.", "res": "Cleared old logs and configured logrotate."},
        {"desc": "Redis cache eviction rate extremely high for {}.", "rc": "Cache size too small for new feature rollout.", "res": "Scaled up Redis cluster memory."}
    ]

    incidents = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(num_incidents):
        svc = random.choice(services)
        template = random.choice(issue_templates)
        
        incident = {
            "id": f"INC-{1000 + i}",
            "timestamp": (base_time + timedelta(hours=random.randint(1, 720))).isoformat(),
            "service": svc,
            "severity": random.choice(severities),
            "description": template["desc"].format(svc),
            "root_cause": template["rc"],
            "resolution": template["res"]
        }
        incidents.append(incident)

    with open("incidents.csv", "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "service", "severity", "description", "root_cause", "resolution"])
        writer.writeheader()
        writer.writerows(incidents)
    
    print(f"Successfully generated incidents.csv with {num_incidents} records.")

if __name__ == "__main__":
    generate_incidents(100)
