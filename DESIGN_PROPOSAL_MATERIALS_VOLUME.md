# Proposal: Volume-like Materials Syntax (Experimental)

This document outlines a proposed enhancement to the Ansible deployment framework to make `materials` behave more like Docker volumes.

## Current Limitations
Currently, `materials` requires manual specification of a `dest` (host path) and doesn't automatically mount the file into the container.

## Proposed Syntax

### Shorthand (Auto-sync + Auto-mount)
```yaml
app_name:
  materials:
    - "configs/nginx.conf:/etc/nginx/nginx.conf"
```
- **Local Path**: `configs/nginx.conf`
- **Host Path (Managed)**: `/opt/ansible_deploy/{{app_name}}/materials/nginx.conf` (automatically managed by framework)
- **Container Path**: `/etc/nginx/nginx.conf` (automatically added to `docker run -v`)

### Full Object (For Manual Control)
```yaml
app_name:
  materials:
    - src: "materials/data"
      dest: "/data/host_path" # Manually managed host path
```

## Implementation Plan

### 1. Pre-process logic in `_deploy_start.yml`
- Iterate through `materials`.
- If a string with `:` is found, split into `src` and `container_path`.
- Assign a default `dest` on the host: `/opt/ansible_deploy/{{app_name}}/materials/{{basename}}`.
- Store the `host:container` mapping for the `docker run` command.

### 2. Update `final_run_cmd`
- Append the new volume mappings to the `docker run` command string.

### 3. Ensure idempotency
- The framework should ensure the host directory exists before syncing.

---
*Created on: 2026-01-07*
