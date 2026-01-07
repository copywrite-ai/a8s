# Proposal: Modular App Definitions (Splitting apps.yml)

This document outlines the professional recommendations for managing a large number of application definitions as the project scales.

## The Problem
As the number of managed applications grows, a single `vars/apps.yml` becomes:
- Difficult to maintain and search.
- Prone to merge conflicts.
- Performance-heavy to parse for every deployment.

## Recommended Solutions

### 1. File Splitting (By Category/Domain)
Instead of one giant file, use a directory structure under `vars/apps/`.

**Proposed Structure:**
```text
vars/
  apps/
    foundation.yml   # Database, Cache, Message Queue
    ai-services.yml   # AI-related microservices
    web-apps.yml      # Frontend and Backend API services
  plan.yml            # Deployment orchestration stays central
```

**Implementation Logic (Ansible):**
In `deploy.yml`, replace `vars_files` with a dynamic loader:
```yaml
- name: Load all app definitions from directory
  include_vars:
    dir: vars/apps
    extensions: ['yml', 'yaml']
```

### 2. Hierarchical Vars (Environment Based)
If applications differ significantly between dev/staging/prod, use specialized directories:
```text
vars/
  common/             # Shared across all environments
  prod/               # Production secrets and specific overrides
  dev/                # Developer-friendly configs
```

### 3. Application-as-a-Folder (Encapsulation)
For complex apps with many dependencies (scripts, localized .env, sidecars), use a folder-per-app approach:
```text
apps/
  my-heavy-app/
    config.yml       # App definition (image, ports, etc.)
    init.sh          # Specific setup script
    templates/       # Config templates
```

## Benefits
- **Readability**: Small, focused files are easier to understand.
- **Isolation**: Changes to one service group don't affect others' files.
- **Scalability**: New teams can add their own `.yml` files without touching yours.

---
*Created on: 2026-01-07*
