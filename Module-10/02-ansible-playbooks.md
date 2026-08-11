# 02 — Ansible Playbook Lab

Ansible is an agentless automation tool that executes tasks on remote (or local) machines over SSH. A **playbook** is a YAML file that describes the tasks to perform. In this lesson, you will write three playbooks that cover the three most common infrastructure remediation scenarios, then run each one manually and verify the fix worked.

---

## Ansible Basics

```text
Playbook (YAML file)
  └── Play (targets a group of hosts)
       └── Tasks (sequential steps)
            ├── Module (ansible built-in action: service, file, shell, ...)
            ├── Handler (runs once at end of play, if notified)
            └── Variables (parameterize playbooks for reuse)
```

### Inventory

The inventory tells Ansible which hosts to target:

```ini
# playbooks/inventory.ini
[webservers]
localhost ansible_connection=local

[appservers]
localhost ansible_connection=local
```

Using `ansible_connection=local` means Ansible runs tasks on the same machine rather than connecting via SSH—ideal for the lab environment running inside Docker.

### Running a Playbook

```bash
ansible-playbook -i playbooks/inventory.ini playbooks/restart-service.yml
```

---

## Playbook 1: restart-service.yml

**Trigger**: Nginx process is not running.
**Action**: Restart the Nginx service and verify it is listening on port 80.

```yaml
# playbooks/restart-service.yml
---
- name: Restart Nginx when it crashes
  hosts: webservers
  become: true
  vars:
    service_name: nginx
    verify_port: 80
    max_retries: 3

  tasks:
    - name: Check if Nginx is running
      ansible.builtin.service_facts:

    - name: Log current state
      ansible.builtin.debug:
        msg: "Nginx status: {{ ansible_facts.services[service_name + '.service'].state | default('not found') }}"

    - name: Restart Nginx service
      ansible.builtin.service:
        name: "{{ service_name }}"
        state: restarted
      notify: Verify Nginx is listening

    - name: Wait for Nginx to become healthy
      ansible.builtin.wait_for:
        port: "{{ verify_port }}"
        timeout: 30
        msg: "Nginx did not come up on port {{ verify_port }} within 30 seconds"

  handlers:
    - name: Verify Nginx is listening
      ansible.builtin.command: "curl -sf http://localhost:{{ verify_port }}/health"
      register: health_check
      failed_when: health_check.rc != 0
```

### Run It

```bash
ansible-playbook -i playbooks/inventory.ini playbooks/restart-service.yml -v
```

Expected output:

```text
PLAY [Restart Nginx when it crashes] *******************************************

TASK [Check if Nginx is running] ***********************************************
ok: [localhost]

TASK [Log current state] *******************************************************
ok: [localhost] => {
    "msg": "Nginx status: stopped"
}

TASK [Restart Nginx service] ***************************************************
changed: [localhost]

TASK [Wait for Nginx to become healthy] ****************************************
ok: [localhost]

RUNNING HANDLER [Verify Nginx is listening] ************************************
ok: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=4    changed=1    unreachable=0    failed=0
```

### Verify the Fix

```bash
curl -s http://localhost:80/health
# {"status": "healthy"}
```

---

## Playbook 2: clear-logs.yml

**Trigger**: Disk usage exceeds 85%.
**Action**: Delete log files older than 7 days in `/var/log/app/`, then verify disk usage dropped.

```yaml
# playbooks/clear-logs.yml
---
- name: Clear old application logs when disk is above 85%
  hosts: webservers
  become: true
  vars:
    log_dir: /var/log/app
    max_age_days: 7
    disk_threshold_pct: 85
    disk_target_pct: 80

  tasks:
    - name: Gather current disk facts
      ansible.builtin.setup:
        gather_subset:
          - hardware

    - name: Calculate disk usage percent for /
      ansible.builtin.set_fact:
        disk_usage_pct: >-
          {{ ((ansible_facts.mounts | selectattr('mount', 'equalto', '/')
               | list | first).size_total
              - (ansible_facts.mounts | selectattr('mount', 'equalto', '/')
               | list | first).size_available)
             / (ansible_facts.mounts | selectattr('mount', 'equalto', '/')
               | list | first).size_total * 100 | round(1) }}

    - name: Skip cleanup if disk is already below threshold
      ansible.builtin.meta: end_play
      when: disk_usage_pct | float < disk_threshold_pct

    - name: Find log files older than {{ max_age_days }} days
      ansible.builtin.find:
        paths: "{{ log_dir }}"
        age: "{{ max_age_days }}d"
        recurse: true
        file_type: file
      register: old_logs

    - name: Report files to be deleted
      ansible.builtin.debug:
        msg: "Found {{ old_logs.files | length }} files to delete ({{ (old_logs.files | map(attribute='size') | sum / 1024 / 1024) | round(1) }} MB)"

    - name: Delete old log files
      ansible.builtin.file:
        path: "{{ item.path }}"
        state: absent
      loop: "{{ old_logs.files }}"
      loop_control:
        label: "{{ item.path }}"

    - name: Verify disk usage dropped below target
      ansible.builtin.shell: |
        df / | awk 'NR==2 {print $5}' | tr -d '%'
      register: new_disk_pct
      changed_when: false

    - name: Report result
      ansible.builtin.debug:
        msg: >-
          Disk cleanup complete.
          Before: {{ disk_usage_pct }}% | After: {{ new_disk_pct.stdout }}%
          Files removed: {{ old_logs.files | length }}
      failed_when: new_disk_pct.stdout | int >= disk_threshold_pct
```

### Run It

```bash
ansible-playbook -i playbooks/inventory.ini playbooks/clear-logs.yml -v
```

Expected output:

```text
TASK [Find log files older than 7 days] ****************************************
ok: [localhost]

TASK [Report files to be deleted] **********************************************
ok: [localhost] => {
    "msg": "Found 142 files to delete (2340.7 MB)"
}

TASK [Delete old log files] ****************************************************
changed: [localhost] => (item=/var/log/app/access-2026-07-31.log)
...

TASK [Report result] ***********************************************************
ok: [localhost] => {
    "msg": "Disk cleanup complete. Before: 87.2% | After: 61.8%\nFiles removed: 142"
}
```

---

## Playbook 3: scale-up.yml

**Trigger**: Average CPU load across app servers exceeds 80% for 5 minutes.
**Action**: Start an additional Docker container replica of the app service and verify it registers as healthy.

```yaml
# playbooks/scale-up.yml
---
- name: Scale up app server when CPU load is high
  hosts: appservers
  become: true
  vars:
    compose_file: /opt/app/docker-compose.yml
    service_name: app
    max_replicas: 5
    replica_healthy_wait_sec: 30

  tasks:
    - name: Get current replica count
      ansible.builtin.shell: |
        docker compose -f {{ compose_file }} ps --quiet {{ service_name }} | wc -l
      register: current_replicas
      changed_when: false

    - name: Fail if already at max replicas
      ansible.builtin.fail:
        msg: "Already at max replicas ({{ max_replicas }}). Escalate to human."
      when: current_replicas.stdout | int >= max_replicas

    - name: Scale up by one replica
      ansible.builtin.shell: |
        docker compose -f {{ compose_file }} up \
          --scale {{ service_name }}={{ current_replicas.stdout | int + 1 }} \
          --no-recreate -d
      register: scale_result

    - name: Wait for new replica to become healthy
      ansible.builtin.shell: |
        docker compose -f {{ compose_file }} ps {{ service_name }} \
          | grep -c "healthy"
      register: healthy_count
      until: healthy_count.stdout | int == current_replicas.stdout | int + 1
      retries: 6
      delay: 5
      changed_when: false

    - name: Report scale result
      ansible.builtin.debug:
        msg: >-
          Scaled {{ service_name }} from {{ current_replicas.stdout }}
          to {{ current_replicas.stdout | int + 1 }} replicas.
          All replicas healthy: {{ healthy_count.stdout }}
```

### Run It

```bash
ansible-playbook -i playbooks/inventory.ini playbooks/scale-up.yml -v
```

Expected output:

```text
TASK [Get current replica count] ***********************************************
ok: [localhost]

TASK [Scale up by one replica] *************************************************
changed: [localhost]

TASK [Wait for new replica to become healthy] **********************************
ok: [localhost]

TASK [Report scale result] *****************************************************
ok: [localhost] => {
    "msg": "Scaled app from 1 to 2 replicas. All replicas healthy: 2"
}

PLAY RECAP *********************************************************************
localhost                  : ok=4    changed=1    unreachable=0    failed=0
```

---

## Lab: Run All Three Playbooks

The lab includes a helper script to simulate each failure condition and then run the appropriate playbook:

```bash
cd Module-10/lab

# Scenario 1: Kill the Nginx process, then fix it
python3 scripts/run_drill.py --scenario nginx-down
# Expected: restart-service.yml runs, Nginx recovers

# Scenario 2: Fill the disk past 85%, then clean it
python3 scripts/run_drill.py --scenario disk-full
# Expected: clear-logs.yml runs, disk drops below 80%

# Scenario 3: Spike CPU above 80%, then scale
python3 scripts/run_drill.py --scenario high-load
# Expected: scale-up.yml runs, new replica registered
```

---

## Debrief Questions

- What happens if the Ansible task fails halfway through? Which tasks already ran?
- Why does `clear-logs.yml` check disk usage again at the end instead of trusting that files were deleted?
- `scale-up.yml` caps at `max_replicas`. What should the human receive when that cap is hit?
- Could you combine all three playbooks into one? Why or why not?

---

## Validation Checklist

- [ ] `restart-service.yml` ran successfully; Nginx responded healthy after.
- [ ] `clear-logs.yml` deleted old logs and disk dropped below 80%.
- [ ] `scale-up.yml` added one replica; all replicas registered healthy.
- [ ] All three drills passed end-to-end via `run_drill.py`.
- [ ] `PLAY RECAP` shows `failed=0` for all three playbooks.
