# Proposal: Ansible-Helm Bridge Architecture (Maximum Foresight)

This architecture is designed for users who want the simplicity of Ansible/Docker today but want to be "K8s-ready" by reusing their application definitions.

## The Core Concept
The **App Definition** is decoupled from the **Execution Engine**. We use a schema that is 100% compatible with Helm's `values.yaml`.

## Directory Structure
```text
deploy-framework/
  apps/
    order-service/
      values.yaml       # <--- The Source of Truth (Helm Compatible)
      templates/
        docker-run.j2   # Ansible uses this today
        k8s-deploy.yaml # K8s (Helm) will use this tomorrow
  ansible/
    engine.yml          # Processes values.yaml and runs Docker
```

## How it works Today (Ansible + Docker)

### 1. The "Helm-like" Values (`apps/my-app/values.yaml`)
```yaml
image:
  repository: nginx
  tag: 1.21
service:
  port: 80
env:
  DB_HOST: "prod-db"
```

### 2. The Ansible Engine (`_deploy_start.yml`)
Instead of hardcoding logic, Ansible reads the `values.yaml` and passes it to a standard Docker template.
```yaml
- name: Load app values
  include_vars:
    file: "apps/{{ item_plan.app_name }}/values.yaml"
    name: app_values

- name: Render Docker Command
  set_fact:
    final_run_cmd: "{{ lookup('template', 'templates/docker-run.j2') }}"
```

## How it works Tomorrow (K8s + Helm)
When you move to K8s, your `values.yaml` **stays exactly the same**. You simply:
1.  Create a standard Helm Chart.
2.  Point Helm to your existing `values.yaml`:
    `helm install my-app ./my-chart -f apps/my-app/values.yaml`

## Why this is "High Foresight" (远见)
1.  **Zero Migration Cost**: Your business logic (ports, envs, images) is already captured in the Helm format.
2.  **Schema Consistency**: You aren't inventing a "fake" Ansible schema; you are using the industry-standard Helm schema.
3.  **Low Friction**: You get the speed of Ansible + SSH today without the technical debt of a custom framework.

## Implementation Steps
1.  **Refactor**: Move `apps.yml` definitions into individual `values.yaml` files.
2.  **Standardize**: Align the key names (e.g., `image.repository` instead of just `image`) with Helm conventions.
3.  **Template**: Create a high-quality `docker-run.j2` that can handle any standard `values.yaml`.

---
*Created on: 2026-01-07*
