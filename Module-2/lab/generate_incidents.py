"""
AIOps Lab — Incident Data Generator
This script creates a fake dataset of historical IT incidents. 
We use this dataset to give our AI 'past experience' to learn from.
"""

# 'csv' helps us read and write comma-separated values files (like a spreadsheet).
import csv

# 'random' lets us make random choices, like picking a random server or error type.
import random

# 'datetime' helps us work with dates and times so our fake incidents have timestamps.
from datetime import datetime, timedelta

def generate_incidents(num_incidents=50):
    # A list of fake services in our imaginary architecture.
    services = ["billing-api", "user-auth", "inventory-db", "frontend-web", "payment-gateway"]
    
    # Priority levels for incidents (P1 is critical, P4 is low priority).
    severities = ["P1", "P2", "P3", "P4"]
    
    # Pre-defined templates for realistic IT operations issues. 
    # Each has a description (desc), root cause (rc), and resolution (res).
    # The '{}' is a placeholder where we will inject the name of the service.
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
    # Start generating timestamps from 30 days ago.
    base_time = datetime.now() - timedelta(days=30)

    # Loop to create exactly 'num_incidents' records.
    for i in range(num_incidents):
        # Randomly pick a service and an issue template.
        svc = random.choice(services)
        template = random.choice(issue_templates)
        
        # Build a dictionary representing one incident.
        incident = {
            "id": f"INC-{1000 + i}",  # E.g., INC-1000, INC-1001...
            "timestamp": (base_time + timedelta(hours=random.randint(1, 720))).isoformat(), # Random time in the last month
            "service": svc,
            "severity": random.choice(severities),
            "description": template["desc"].format(svc), # Injects the service name into the description
            "root_cause": template["rc"],
            "resolution": template["res"]
        }
        # Add it to our list.
        incidents.append(incident)

    # Open a new file called 'incidents.csv' in write mode ('w').
    with open("incidents.csv", "w", newline='') as f:
        # Create a CSV writer and tell it what the column headers are.
        writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "service", "severity", "description", "root_cause", "resolution"])
        
        # Write the top header row.
        writer.writeheader()
        
        # Write all the incidents we generated as rows in the CSV.
        writer.writerows(incidents)
    
    print(f"Successfully generated incidents.csv with {num_incidents} records.")

# This block ensures the code only runs if we run this script directly.
if __name__ == "__main__":
    # Generate exactly 100 fake incidents when this script is run.
    generate_incidents(100)
