# 01 — Zero Trust Architecture

The traditional network security model draws a perimeter around your data centre and trusts everything inside it. This model fails catastrophically the moment any device inside the perimeter is compromised — which is the *starting point* of most modern breaches, not the endpoint.

**Zero Trust** replaces perimeter trust with a simple principle: **never trust, always verify**. Every request — whether it comes from inside or outside the network — must be authenticated, authorised, and encrypted before it is served.

---

## The Google BeyondCorp Model

Google published the BeyondCorp research (2014–2018) after their own network was breached in Operation Aurora. The key insight: access decisions should be based on **who you are** and **device health**, not *where* your network packet originates.

BeyondCorp has five pillars:

| Pillar | What It Means |
|---|---|
| **Device inventory** | Every device is catalogued and assigned a trust tier |
| **Strong identity** | No network-level trust; every request carries a verified identity |
| **Device health checks** | Access is gated on patch level, disk encryption, OS version |
| **Context-aware access** | Access policies consider time, location, and resource sensitivity |
| **Micro-segmentation** | No flat network; each service can only reach what it needs |

In infrastructure terms, micro-segmentation is implemented using **firewall rules at the host level** (`iptables`, `nftables`, or cloud security groups), not just at the network perimeter.

---

## The AIOps Connection

Zero Trust generates enormous amounts of access log data — every request is evaluated and logged. This data is exactly what AIOps anomaly detection and SIEM correlation (Lessons 02 and 03) need. Zero Trust and AIOps are complementary: Zero Trust generates the telemetry; AIOps makes sense of it at scale.

---

## Zero Trust Lab: Configure iptables

In this lab you will configure `iptables` rules on `db-server` (the VM holding sensitive data) to enforce the Zero Trust principle of explicit access.

### Lab Goal

After configuration:
- `web-server` **can** connect to `db-server` on port `5432` (PostgreSQL).
- `db-server` **cannot** initiate any outbound internet connection.
- All other inbound traffic to `db-server` from outside the VPC is **dropped**.

### Step 1: Verify Current State

SSH into `db-server`:

```bash
ssh user@10.0.2.11
```

Check existing rules:

```bash
sudo iptables -L -v -n
```

By default you should see only a few rules — likely accepting everything:

```text
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
```

### Step 2: Flush and Apply Zero Trust Rules

```bash
# Flush existing rules
sudo iptables -F

# Allow loopback (essential — never block this)
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Allow established/related connections (responses to our own requests)
sudo iptables -A INPUT  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH from the host only (replace 10.0.2.1 with your host IP)
sudo iptables -A INPUT -p tcp -s 10.0.2.1 --dport 22 -j ACCEPT

# Allow PostgreSQL from web-server only
sudo iptables -A INPUT -p tcp -s 10.0.2.10 --dport 5432 -j ACCEPT

# Allow ICMP (ping) from the host for diagnostics
sudo iptables -A INPUT -p icmp -s 10.0.2.1 -j ACCEPT

# Drop all other inbound
sudo iptables -A INPUT -j DROP

# Block all NEW outbound connections to the internet
# (only allow traffic to the VPC subnet 10.0.2.0/24)
sudo iptables -A OUTPUT -d 10.0.2.0/24 -j ACCEPT
sudo iptables -A OUTPUT -d 127.0.0.0/8  -j ACCEPT
sudo iptables -A OUTPUT -j DROP
```

### Step 3: Verify the Rules

```bash
sudo iptables -L -v -n --line-numbers
```

Expected output:

```text
Chain INPUT (policy ACCEPT)
num  target  prot opt source        destination
1    ACCEPT  all  --  0.0.0.0/0    0.0.0.0/0    /* loopback */
2    ACCEPT  all  --  0.0.0.0/0    0.0.0.0/0    ctstate RELATED,ESTABLISHED
3    ACCEPT  tcp  --  10.0.2.1     0.0.0.0/0    dpt:22
4    ACCEPT  tcp  --  10.0.2.10    0.0.0.0/0    dpt:5432
5    ACCEPT  icmp --  10.0.2.1     0.0.0.0/0
6    DROP    all  --  0.0.0.0/0    0.0.0.0/0

Chain OUTPUT (policy ACCEPT)
num  target  prot opt source        destination
1    ACCEPT  all  --  0.0.0.0/0    0.0.0.0/0    /* loopback */
2    ACCEPT  all  --  0.0.0.0/0    0.0.0.0/0    ctstate RELATED,ESTABLISHED
3    ACCEPT  all  --  0.0.0.0/0    10.0.2.0/24
4    ACCEPT  all  --  0.0.0.0/0    127.0.0.0/8
5    DROP    all  --  0.0.0.0/0    0.0.0.0/0
```

### Step 4: Test — db-server Cannot Reach the Internet

From `db-server`, attempt an internet connection:

```bash
curl --max-time 5 https://google.com
```

Expected result:

```text
curl: (28) Connection timed out after 5001 milliseconds
```

**This is the correct Zero Trust behaviour** — the database server has no reason to initiate internet connections, and now it cannot.

### Step 5: Test — web-server CAN Reach db-server

From `web-server`:

```bash
nc -zv 10.0.2.11 5432
```

Expected result:

```text
Connection to 10.0.2.11 5432 port [tcp/postgresql] succeeded!
```

### Step 6: Make Rules Persistent

`iptables` rules are lost on reboot. Persist them:

```bash
# On Ubuntu/Debian
sudo apt install iptables-persistent -y
sudo netfilter-persistent save

# On CentOS/RHEL
sudo service iptables save
```

---

## Zero Trust in Cloud Environments

In AWS, GCP, and Azure, the same principles are implemented without manual `iptables`:

| On-prem Tool | Cloud Equivalent |
|---|---|
| `iptables` DROP rules | Security Group deny rules |
| Per-host firewall | VPC subnet ACLs |
| SSH key management | IAM instance roles + SSM Session Manager |
| Explicit egress control | VPC endpoints, NAT gateway allowlists |

The principle is identical — the tooling is managed by the cloud control plane instead of SSH sessions.

---

## Validation Checklist

- [ ] `iptables` rules applied and visible with `iptables -L -v -n`.
- [ ] `curl https://google.com` from `db-server` times out.
- [ ] `nc -zv 10.0.2.11 5432` from `web-server` succeeds.
- [ ] Rules persisted with `netfilter-persistent save` or `service iptables save`.
- [ ] You can explain the difference between perimeter security and Zero Trust.
