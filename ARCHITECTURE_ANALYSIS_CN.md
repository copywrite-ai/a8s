# 架构分析与功能规划

## 1. 工具定位与对比

当前的工程是一个**“基于 Ansible 的轻量级编排器”**。它的定位介于简单脚本和重型编排之间，非常灵活。

| 维度 | Ansible Orchestrator (当前) | Docker Compose | Kubernetes (K8s) |
| :--- | :--- | :--- | :--- |
| **适用场景** | 中等规模单机/多机部署、特定顺序依赖强、混合部署(Docker+二进制+脚本) | 单机开发环境、轻量级单机部署 | 大规模集群、微服务、高可用、自动扩缩容 |
| **编排能力** | **强过程控制** (Group/Serial/Wait)、自定义逻辑灵活 | **强声明式** (depends_on)、简单直观 | **终态一致性** (Reconcile Loop)、极其复杂 |
| **跨主机** | **原生支持** (SSH 互信即可) | 弱 (需 Swarm 或手动管理) | **原生强项** (统一调度) |
| **配置管理** | 极强 (Jinja2 模板、Vault 加密、Fact 收集) | 弱 (仅环境变量) | 强 (ConfigMap/Secret)，但 yaml 冗长 |
| **运维门槛** | 中 (需懂 Ansible/Linux) | 低 | 高 (需专业团队维护 Control Plane) |

### 当前方案的独特优势
1.  **混合编排能力**：你可以轻松地在一个 Plan 中混合 Docker 容器、Shell 命令 (`app_type: cmd`)、文件分发 (`sync_v2`) 和 API 探测。这是 K8s 和 Compose 很难做到的（它们只管容器）。
2.  **过程可控性**：`serial: true` 就是典型例子。在 K8s 中要实现“等上一个 Pod 完全 Ready 并运行一段脚本后再启动下一个”，通常需要编写 Operator 或复杂的 InitContainer，而你只需要几行 Ansible Task。
3.  **无 Agent 架构**：不需要在目标机器装 kubelet 或 docker engine 以外的东西。

---

## 2. 功能建议 (Feature Roadmap)

如果要让这个工程更完善、更具生产力，建议从以下几个 Feature 入手：

### A. 提升“可观测性”与“调试体验” (优先级: 高)
目前部署失败看 log 比较痛苦，需要翻 Ansible 冗长的输出。
*   **Feature: 部署报告 (Deployment Report)**
    *   在部署结束后，生成一个 HTML 或 Markdown 汇总报告，列出：哪些 App 成功、耗时多少、Final Image ID 是什么、Health Check 输出是什么。
*   **Feature: 实时日志流 (Log Streaming)**
    *   提供一个简单的 UI 或 TUI，不用 tail docker logs，而是聚合展示当前 Group 正在部署的 App 日志。

### B. 增强“安全性” (优先级: 高)
目前 `apps.yml` 中可能包含敏感环境变量。
*   **Feature: Secret 管理**
    *   集成 **Ansible Vault**。不要在 `apps.yml` 明文写密码，而是用 `{{ vault_db_password }}`。
    *   或者支持从外部文件/环境变量读取敏感信息，避免提交到 Git。

### C. 完善“网络与发现” (优先级: 中)
目前依赖 `host` 网络或手动映射端口 (`localhost:xxxx`)。
*   **Feature: 动态端口管理 / Rendered Config**
    *   支持在 `apps.yml` 中使用变量定义端口，如 `port: "{{ base_port + 1 }}"`，避免冲突。
*   **Feature: 简易服务发现 (DNS/Hosts)**
    *   Ansible 可以自动维护目标机器的 `/etc/hosts`，把 `db_mysql_demo` 指向对应的 IP，这样 App 之间可以用域名互访，不需要硬编码 IP。

### D. 增强“回滚与容灾” (优先级: 中)
*   **Feature: 快速回滚 (Rollback)**
    *   记录上一次成功的 Image ID (`.deploy_history`)。如果本次部署失败，提供一个 `./rollback.sh` 脚本，快速把所有 App 恢复到上一个版本。
*   **Feature: 清理策略 (Prune)**
    *   自动清理旧的 Docker Image 和 Exited Container，防止磁盘占满。

### E. 提升“多环境支持” (优先级: 低，看需求)
*   **Feature: Environment Overlays**
    *   类似 Kustomize。保持 `apps.yml` 为基准配置，创建 `env/prod/apps_override.yml` 和 `env/test/apps_override.yml`，部署时自动合并。

### 总结
你现在的系统在 **“灵活性”** 和 **“部署逻辑控制”** 上已经超过了 Docker Compose。
如果你的业务规模不需要 K8s 那种级别的自动扩缩容，**坚持优化这套 Ansible 系统是完全可行的，且 ROI 很高**。

建议下一步优先做 **Secrets 管理** 或 **部署报告**。
