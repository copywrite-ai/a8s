# Ansible Docker Orchestrator

A flexible, modular Ansible pipeline for orchestrating Docker container deployments. It supports **grouped parallel execution**, **dependency management**, and **health-check-driven** workflows.

## Key Features

- **Grouped Parallelism**: 
  - Deploy applications in logical groups (e.g., `Foundation`, `Business`).
  - Applications within the same group are triggered in parallel for faster execution.
- **Dependency Management**:
  - Sequential group execution ensures foundational services (like Databases) are healthy *before* dependent services (like Backends) start.
- **Robust Health Checks**:
  - Integrated verification step waits for containers to report `healthy` status before proceeding.
  - Configurable retries and intervals.
- **Material Distribution**:
  - Supports syncing directories or single files to target hosts before container startup.

## Project Structure

```text
.
├── deploy.yml              # Main entry point playbook
├── _process_group.yml      # Group orchestration logic
├── _deploy_start.yml       # Task: Trigger container startup
├── _deploy_verify.yml      # Task: Verify health status
├── healthcheck_v2.yml      # Modular health check logic
├── sync_v2.yml             # Modular file sync logic
├── vars/
│   ├── apps.yml            # Application definitions (Docker config, healthchecks)
│   └── plan.yml            # Deployment plan (Groups, Hosts)
└── tests/
    └── integration_test.py # Python integration test suite
```

## Configuration

### 1. Define Applications (`vars/apps.yml`)
Describe your Docker containers, including images, ports, volumes, and raw commands.

```yaml
app_definitions:
  db_mysql_demo:
    image: alpine:latest
    raw_command: >-
      docker run -d 
      --name db_mysql_demo
      --health-cmd="test -f /tmp/db_ready || exit 1"
      alpine:latest 
      sh -c "echo 'DB Ready' > /tmp/db_ready; tail -f /dev/null"
```

### 2. Define Deployment Plan (`vars/plan.yml`)
Organize apps into groups. Groups run sequentially; apps within a group run in parallel.

```yaml
deploy_groups:
  - name: "Foundation Services"
    apps:
      - app_name: db_mysql_demo
        target_ip: localhost

  - name: "Business Services"
    apps:
      - app_name: app_backend_1
        target_ip: localhost
```

## Usage

### Prerequisites
- Ansible installed locally.
- Docker installed on target hosts (and localhost for testing).
- SSH access to target hosts (if remote).

### Run Deployment
```bash
ansible-playbook deploy.yml
```

## Testing

This project includes a Python-based integration test suite that verifies:
1. Clean environment setup.
2. Playbook execution success.
3. Container existence and status.
4. Health check validation.
5. Service endpoint reachability.
6. Correct group execution order.

### Run Tests
```bash
python3 tests/integration_test.py
```

## License
MIT
