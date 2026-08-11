# 'csv' lets us read and write comma-separated values (like a simple spreadsheet).
import csv
# 'random' helps us pick random items from a list (to simulate different incidents).
import random
# 'datetime' helps us generate fake timestamps for our alerts.
from datetime import datetime, timedelta

def generate_incidents(num_incidents=50):
    """
    Generates a fake dataset of historical IT incidents.
    We need this so our AI has some 'past experience' to learn from.
    """
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
    # Start creating fake incidents going back 30 days
    base_time = datetime.now() - timedelta(days=30)

    # Loop multiple times to generate the requested number of incidents
    for i in range(num_incidents):
        # Pick a random service and issue template
        svc = random.choice(services)
        template = random.choice(issue_templates)
        
        # Create a dictionary representing one incident row
        incident = {
            "id": f"INC-{1000 + i}",
            "timestamp": (base_time + timedelta(hours=random.randint(1, 720))).isoformat(),
            "service": svc,
            "severity": random.choice(severities),
            # Fill in the {} blank in our template with the service name
            "description": template["desc"].format(svc),
            "root_cause": template["rc"],
            "resolution": template["res"]
        }
        incidents.append(incident)

    # Save all the fake incidents to a CSV file called 'incidents.csv'
    with open("incidents.csv", "w", newline='') as f:
        # DictWriter helps write Python dictionaries to CSV columns
        writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "service", "severity", "description", "root_cause", "resolution"])
        writer.writeheader() # Write the top row (column names)
        writer.writerows(incidents) # Write all the data rows
    
    print(f"Successfully generated incidents.csv with {num_incidents} records.")

# This tells Python: "If someone runs this file directly, execute the function below."
if __name__ == "__main__":
    generate_incidents(100)
