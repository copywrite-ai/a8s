# Architecture Analysis & Feature Roadmap

## 1. Tool Positioning & Comparison

The current project is a **"Lightweight Orchestrator based on Ansible"**. It sits nicely between simple shell scripts and heavy container orchestrators.

| Dimension | Ansible Orchestrator (Current) | Docker Compose | Kubernetes (K8s) |
| :--- | :--- | :--- | :--- |
| **Scenarios** | Medium-scale single/multi-node, strong sequential dependencies, hybrid deployment (Docker + Binary + Script) | Local dev, simple single-node deployment | Large-scale clusters, microservices, high availability, auto-scaling |
| **Orchestration** | **Strong Procedural Control** (Group/Serial/Wait), flexible custom logic | **Strong Declarative** (depends_on), simple & intuitive | **Eventual Consistency** (Reconcile Loop), complex |
| **Multi-host** | **Native Support** (SSH trust) | Weak (requires Swarm or manual management) | **Native Strength** (Unified scheduling) |
| **Config Mgmt** | Very Strong (Jinja2 templates, Vault, Fact gathering) | Weak (Env vars only) | Strong (ConfigMap/Secret), but verbose YAML |
| **Ops Threshold** | Medium (Requires Ansible/Linux knowledge) | Low | High (Requires dedicated Control Plane maintenance) |

### Unique Advantages of Current Solution
1.  **Hybrid Orchestration Capability**: Seamlessly mix Docker containers, Shell commands (`app_type: cmd`), file distribution (`sync_v2`), and API probing in a single Plan. This is hard for K8s/Compose which focus solely on containers.
2.  **Process Controllability**: Features like `serial: true` allow precise control (e.g., "Wait for App A to be fully Ready and run a post-script before starting App B"), which often requires complex Operators or InitContainers in K8s.
3.  **Agentless Architecture**: No need to install anything on target machines other than Python/SSH access.

---

## 2. Feature Suggestions (Roadmap)

To enhance productivity and robustness, the following features are recommended:

### A. Observability & Debugging (Priority: High)
*   **Deployment Report**: Generate an HTML/Markdown summary after deployment (Success/Fail status, Duration, Final Image IDs, Health Check outputs).
*   **Real-time Log Streaming**: A UI or TUI to aggregate and stream logs of the currently deploying Group, avoiding manual `docker logs`.

### B. Security (Priority: High)
*   **Secret Management**: Integrate **Ansible Vault**. Avoid plaintext passwords in `apps.yml`. Use `{{ vault_db_password }}` or read from external secure sources.

### C. Networking & Discovery (Priority: Medium)
*   **Dynamic Port Management**: Allow defining ports via variables (`port: "{{ base_port + 1 }}"`) to avoid conflicts.
*   **Simple Service Discovery**: Automatically maintain `/etc/hosts` on target machines so apps can communicate via domain names instead of hardcoded IPs.

### D. Rollback & Reliability (Priority: Medium)
*   **Quick Rollback**: Track the last successful Image ID (`.deploy_history`). Provide a `./rollback.sh` to revert all apps to the previous stable state if deployment fails.
*   **Auto-Prune**: Policy to clean up old Docker images and exited containers to prevent disk exhaustion.

### E. Multi-Environment Support (Priority: Low)
*   **Environment Overlays**: Adopt a Kustomize-like approach. Keep `apps.yml` as base, and merge `env/prod/apps_override.yml` at runtime.

### Summary
The current system outperforms Docker Compose in **Flexibility** and **Logic Control**. Unless dynamic auto-scaling is required, optimizing this Ansible-based system provides a high ROI.
