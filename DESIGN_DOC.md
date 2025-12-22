# Ansible Docker 容器编排系统 - 详细设计文档

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [模块设计](#3-模块设计)
4. [部署流程](#4-部署流程)
5. [时序图](#5-时序图)
6. [配置规范](#6-配置规范)
7. [扩展指南](#7-扩展指南)

---

## 1. 项目概述

### 1.1 项目背景

本项目是一个基于 Ansible 的 Docker 容器编排部署系统，旨在提供一个灵活、模块化的容器部署解决方案。它支持**分组并行执行**、**依赖管理**和**健康检查驱动**的工作流程。

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| **分组并行** | 应用按逻辑分组（如基础服务、业务服务），同组内应用并行触发以加速部署 |
| **依赖管理** | 组间顺序执行，确保基础服务（如数据库）健康后才启动依赖服务（如后端应用） |
| **健康检查** | 集成健康检查验证步骤，等待容器报告 `healthy` 状态后再继续 |
| **物料分发** | 支持在容器启动前同步目录或单文件到目标主机 |

### 1.3 适用场景

- 多主机 Docker 容器批量部署
- 微服务架构的有序启动
- 需要物料（配置文件、静态资源）预分发的应用部署
- CI/CD 流水线中的容器编排

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Ansible Docker Orchestrator                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         主控制层 (Master Controller)                     │   │
│  │                              deploy.yml                                  │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐    │   │
│  │  │ 加载配置     │ -> │ 遍历分组    │ -> │ 生成部署摘要              │    │   │
│  │  │ vars/*.yml  │    │ deploy_groups│   │ _deploy_summary.yml      │    │   │
│  │  └─────────────┘    └─────────────┘    └──────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         分组处理层 (Group Processor)                     │   │
│  │                           _process_group.yml                             │   │
│  │  ┌────────────────────────────┐    ┌────────────────────────────┐      │   │
│  │  │ Phase 1: 触发启动序列      │ -> │ Phase 2: 健康检查验证       │      │   │
│  │  │ _deploy_start.yml         │    │ _deploy_verify.yml          │      │   │
│  │  └────────────────────────────┘    └────────────────────────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                        ┌─────────────┴─────────────┐                           │
│                        ▼                           ▼                           │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────────┐ │
│  │      物料分发模块               │   │        健康检查模块                  │ │
│  │      sync_v2.yml                │   │        healthcheck_v2.yml           │ │
│  │  ┌──────────┐ ┌──────────┐     │   │  ┌────────────────┐ ┌──────────────┐│ │
│  │  │ 目录归档 │ │ 文件复制 │     │   │  │Docker健康检查  │ │容器状态检测  ││ │
│  │  │ 分发     │ │ 分发     │     │   │  │(has_healthcheck)│ │(no_healthcheck)│ │
│  │  └──────────┘ └──────────┘     │   │  └────────────────┘ └──────────────┘│ │
│  └─────────────────────────────────┘   └─────────────────────────────────────┘ │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                               目标主机层 (Target Hosts)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │
│  │ Host 1      │ │ Host 2      │ │ Host 3      │ │ ...                     │   │
│  │ (localhost) │ │ (remote)    │ │ (remote)    │ │                         │   │
│  │  Docker     │ │  Docker     │ │  Docker     │ │  Docker                 │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 文件结构说明

```
.
├── deploy.yml              # 主入口 Playbook，编排控制器
├── _process_group.yml      # 分组处理逻辑，协调启动和验证
├── _deploy_start.yml       # 容器启动任务（含物料分发）
├── _deploy_verify.yml      # 健康检查验证任务
├── _deploy_task.yml        # 完整部署任务（启动+验证合一，备用）
├── _deploy_summary.yml     # 部署摘要生成入口
├── _summary_per_app.yml    # 遍历应用获取信息
├── _summary_fetch_info.yml # 获取单个容器部署信息
├── healthcheck_v2.yml      # 模块化健康检查逻辑
├── sync_v2.yml             # 模块化文件同步逻辑
├── check_summary.yml       # 独立摘要检查 Playbook
├── ansible.cfg             # Ansible 配置文件
├── inventory.ini           # 主机清单
├── vars/
│   ├── apps.yml            # 应用定义（Docker 配置、健康检查参数）
│   └── plan.yml            # 部署计划（分组、主机映射）
├── materials/              # 静态资源物料目录
│   └── index.html          # 示例静态文件
└── tests/
    └── integration_test.py # Python 集成测试套件
```

### 2.3 核心组件职责

| 组件 | 文件 | 职责 |
|------|------|------|
| **主控制器** | `deploy.yml` | 加载配置、遍历分组、调用分组处理器 |
| **分组处理器** | `_process_group.yml` | 协调组内应用的启动和验证流程 |
| **启动执行器** | `_deploy_start.yml` | 物料分发、命令构建、容器启动 |
| **验证执行器** | `_deploy_verify.yml` | 加载配置、调用健康检查模块 |
| **健康检查模块** | `healthcheck_v2.yml` | 智能判断检查类型、等待容器就绪 |
| **文件同步模块** | `sync_v2.yml` | 目录归档分发、单文件复制 |
| **摘要生成器** | `_deploy_summary.yml` | 收集并展示部署结果信息 |

---

## 3. 模块设计

### 3.1 主控制器 (deploy.yml)

**功能描述**：作为整个部署流程的入口点，负责加载配置并协调各分组的部署。

**执行逻辑**：

```yaml
# 简化的执行流程
1. 加载 vars/apps.yml      # 应用定义
2. 加载 vars/plan.yml      # 部署计划
3. 打印启动信息            # 显示分组数量
4. 循环遍历 deploy_groups  # 顺序处理每个分组
   └── include_tasks: _process_group.yml
5. 生成部署摘要            # 展示最终结果
   └── include_tasks: _deploy_summary.yml
```

**关键变量**：
- `deploy_groups`: 从 `plan.yml` 加载的分组列表
- `app_definitions`: 从 `apps.yml` 加载的应用配置字典

---

### 3.2 分组处理器 (_process_group.yml)

**功能描述**：处理单个分组的部署逻辑，分为两个阶段执行。

**两阶段设计**：

```
┌─────────────────────────────────────────────────────────────┐
│                     分组处理流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 1: 触发启动序列 (Trigger Start Sequence)       │   │
│  │                                                      │   │
│  │  遍历 group_item.apps:                               │   │
│  │    ├── app_1 → _deploy_start.yml                    │   │
│  │    ├── app_2 → _deploy_start.yml                    │   │
│  │    └── app_n → _deploy_start.yml                    │   │
│  │                                                      │   │
│  │  说明: 所有应用的容器启动命令被触发（并行效果）        │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase 2: 健康检查验证 (Trigger Health Checks)        │   │
│  │                                                      │   │
│  │  遍历 group_item.apps:                               │   │
│  │    ├── app_1 → _deploy_verify.yml (等待 healthy)     │   │
│  │    ├── app_2 → _deploy_verify.yml (等待 healthy)     │   │
│  │    └── app_n → _deploy_verify.yml (等待 healthy)     │   │
│  │                                                      │   │
│  │  说明: 确保所有应用健康后才进入下一个分组             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**输入变量**：
- `group_item`: 当前处理的分组对象
  - `group_item.name`: 分组名称
  - `group_item.apps`: 应用列表

---

### 3.3 启动执行器 (_deploy_start.yml)

**功能描述**：执行单个应用的完整启动流程。

**执行步骤**：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 加载配置 | 从 `app_definitions` 获取当前应用配置 |
| 2 | 调试连接 | 打印目标主机和连接方式信息 |
| 3 | 目录物料分发 | 若配置了 `materials` 且类型为 `archive_dir`，调用 `sync_v2.yml` |
| 4 | 文件物料分发 | 若配置了 `materials` 且类型为 `file`，直接复制文件 |
| 5 | 构建启动命令 | 根据 `raw_command` 或自动拼接 Docker 命令 |
| 6 | 清理旧容器 | 执行 `docker rm -f` 移除同名容器 |
| 7 | 启动新容器 | 执行构建的 Docker run 命令 |

**命令构建逻辑**：

```jinja2
{% if current_app.raw_command is defined %}
  {{ current_app.raw_command }}
{% else %}
  docker run -d 
  --name {{ app_name }} 
  --restart always 
  {% for port in current_app.ports | default([]) %}-p {{ port }} {% endfor %}
  {% for volume in current_app.volumes | default([]) %}-v {{ volume }} {% endfor %}
  {% for k,v in current_app.env | default({}).items() %}-e {{ k }}='{{ v }}' {% endfor %}
  {% for env in current_app.env_file | default([]) %}--env-file {{ env }} {% endfor %}
  {{ current_app.image }}
{% endif %}
```

---

### 3.4 健康检查模块 (healthcheck_v2.yml)

**功能描述**：智能检测容器健康状态，支持两种检查模式。

**检查模式决策树**：

```
                    ┌──────────────────┐
                    │ 获取容器健康状态  │
                    │ docker inspect   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ 健康状态值是否为: │
                    │ starting/healthy/│
                    │ unhealthy ?      │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌───────▼───────┐
       │ 是           │              │ 否            │
       │ has_healthcheck│            │ no_healthcheck │
       └──────┬──────┘              └───────┬───────┘
              │                             │
       ┌──────▼──────────────┐      ┌───────▼───────────────┐
       │ 等待 Docker 原生    │      │ 等待容器退出且        │
       │ Health.Status       │      │ ExitCode = 0          │
       │ 变为 "healthy"      │      │ (适用于一次性任务)    │
       └─────────────────────┘      └───────────────────────┘
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `app_name` | string | 必填 | 容器名称 |
| `delegate_host` | string | localhost | 目标主机 |
| `retries` | int | 30 | 最大重试次数 |
| `interval` | int | 5 | 重试间隔（秒） |
| `debug_mode` | bool | false | 是否打印调试信息 |

---

### 3.5 文件同步模块 (sync_v2.yml)

**功能描述**：将本地物料文件或目录分发到目标主机。

**处理流程**：

```
                    ┌──────────────────┐
                    │ 检查源路径类型   │
                    │ stat: sync_src   │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌───────▼───────┐
       │ 目录         │              │ 文件          │
       │ isdir: true │              │ isdir: false  │
       └──────┬──────┘              └───────┬───────┘
              │                             │
       ┌──────▼──────────────┐      ┌───────▼───────────────┐
       │ 1. 本地归档目录     │      │ 1. 确保父目录存在     │
       │    (tar.gz)         │      │ 2. 复制文件到目标     │
       │ 2. 复制归档到目标   │      │    (支持备份)         │
       │ 3. 解压到目标目录   │      └───────────────────────┘
       │ 4. 清理临时归档     │
       └─────────────────────┘
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sync_src` | string | 必填 | 源文件/目录路径 |
| `sync_dest` | string | 必填 | 目标路径 |
| `sync_owner` | string | root | 文件所有者 |
| `sync_group` | string | root | 文件所属组 |
| `sync_mode` | string | 0755/0644 | 权限模式 |
| `delegate_host` | string | localhost | 目标主机 |

---

### 3.6 部署摘要生成器 (_deploy_summary.yml)

**功能描述**：收集所有已部署容器的信息并生成汇总表格。

**信息收集流程**：

```
_deploy_summary.yml
    │
    ├── 初始化 deployment_summary = []
    │
    ├── 遍历 deploy_groups
    │   └── _summary_per_app.yml
    │       └── 遍历 group_item.apps
    │           └── _summary_fetch_info.yml
    │               ├── docker inspect 获取 Image ID
    │               ├── docker inspect 获取 Image Source
    │               └── 追加到 deployment_summary
    │
    └── 打印汇总表格
        ┌────────────────────────────────────────────────────────┐
        │ Application | DeploymentIP | ImageID | OriginalImage  │
        ├────────────────────────────────────────────────────────┤
        │ db_mysql    | localhost    | sha256..| alpine:latest  │
        │ app_backend | 192.168.1.10 | sha256..| nginx:alpine   │
        └────────────────────────────────────────────────────────┘
```

---

## 4. 部署流程

### 4.1 完整部署流程图

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              完整部署流程                                        │
└──────────────────────────────────────────────────────────────────────────────────┘

开始
  │
  ▼
┌─────────────────────────────────┐
│ 1. 加载配置文件                 │
│    ├── vars/apps.yml            │
│    └── vars/plan.yml            │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. 打印部署启动信息             │
│    显示总分组数量               │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. 遍历 deploy_groups           │◄──────────────────────────────┐
│    当前: group_item             │                               │
└──────────────┬──────────────────┘                               │
               │                                                   │
               ▼                                                   │
┌─────────────────────────────────┐                               │
│ 4. _process_group.yml           │                               │
│    处理当前分组                 │                               │
├─────────────────────────────────┤                               │
│ 4.1 Phase 1: 启动序列           │                               │
│     ┌───────────────────────┐   │                               │
│     │ 遍历 group_item.apps  │   │                               │
│     │ → _deploy_start.yml   │   │                               │
│     │   ├── 物料分发        │   │                               │
│     │   ├── 构建命令        │   │                               │
│     │   ├── 清理旧容器      │   │                               │
│     │   └── 启动新容器      │   │                               │
│     └───────────────────────┘   │                               │
├─────────────────────────────────┤                               │
│ 4.2 Phase 2: 健康检查           │                               │
│     ┌───────────────────────┐   │                               │
│     │ 遍历 group_item.apps  │   │                               │
│     │ → _deploy_verify.yml  │   │                               │
│     │   └── healthcheck_v2  │   │                               │
│     │       等待 healthy    │   │                               │
│     └───────────────────────┘   │                               │
└──────────────┬──────────────────┘                               │
               │                                                   │
               ▼                                                   │
        ┌──────────────┐                                          │
        │ 还有更多分组? │──────────── 是 ─────────────────────────┘
        └──────┬───────┘
               │ 否
               ▼
┌─────────────────────────────────┐
│ 5. _deploy_summary.yml          │
│    生成部署摘要表格             │
└──────────────┬──────────────────┘
               │
               ▼
             结束
```

### 4.2 单应用启动详细流程

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            单应用启动流程 (_deploy_start.yml)                    │
└──────────────────────────────────────────────────────────────────────────────────┘

输入: item_plan (包含 app_name, target_ip)
  │
  ▼
┌─────────────────────────────────┐
│ 1. 加载应用配置                 │
│    current_app = app_definitions│
│                  [item_plan.app_name]
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. 检查是否需要物料分发         │
│    current_app.materials ?      │
└──────────────┬──────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼ 是              ▼ 否
┌───────────────┐   ┌───────────────┐
│ 2a. 遍历      │   │ 跳过物料分发  │
│   materials   │   └───────┬───────┘
│               │           │
│ type=archive_ │           │
│ dir?          │           │
│ → sync_v2.yml │           │
│               │           │
│ type=file?    │           │
│ → copy模块    │           │
└───────┬───────┘           │
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│ 3. 构建 Docker 启动命令         │
│                                 │
│ raw_command 存在?               │
│   是 → 直接使用                 │
│   否 → 自动拼接:                │
│        docker run -d            │
│        --name xxx               │
│        -p port1 -p port2        │
│        -v vol1 -v vol2          │
│        -e ENV1=val1             │
│        --env-file xxx           │
│        IMAGE                    │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 4. 清理旧容器                   │
│    docker rm -f {{ app_name }}  │
│    (delegate_to: target_ip)     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 5. 执行启动命令                 │
│    shell: {{ final_run_cmd }}   │
│    (delegate_to: target_ip)     │
└──────────────┬──────────────────┘
               │
               ▼
             完成
```

### 4.3 健康检查详细流程

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            健康检查流程 (healthcheck_v2.yml)                     │
└──────────────────────────────────────────────────────────────────────────────────┘

输入: app_name, delegate_host, retries, interval
  │
  ▼
┌─────────────────────────────────┐
│ 1. 检查容器健康检查配置         │
│                                 │
│    docker inspect --format=     │
│    '{{.State.Health.Status}}'   │
│    {{ app_name }}               │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. 判断健康检查类型             │
│                                 │
│    status ∈ {starting,          │
│              healthy,           │
│              unhealthy} ?       │
└──────────────┬──────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼ 是              ▼ 否
┌───────────────────┐ ┌───────────────────────┐
│ has_healthcheck   │ │ no_healthcheck        │
│                   │ │                       │
│ 循环等待:         │ │ 循环等待:             │
│ until: status ==  │ │ until: 容器状态 ==    │
│        "healthy"  │ │   exited && exit_code │
│                   │ │   == 0                │
│ retries: N        │ │                       │
│ delay: M秒        │ │ retries: N            │
│                   │ │ delay: M秒            │
└─────────┬─────────┘ └───────────┬───────────┘
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
┌─────────────────────────────────┐
│ 3. 健康检查通过                 │
│    容器已就绪，可继续部署流程   │
└──────────────┬──────────────────┘
               │
               ▼
             完成
```

---

## 5. 时序图

### 5.1 完整部署时序图

```
┌─────────┐ ┌─────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────────┐ ┌───────────┐
│ 用户    │ │ deploy.yml  │ │_process_group │ │_deploy_start  │ │_deploy_verify│ │ 目标主机  │
└────┬────┘ └──────┬──────┘ └───────┬───────┘ └───────┬───────┘ └──────┬───────┘ └─────┬─────┘
     │             │                │                 │                │               │
     │ 执行        │                │                 │                │               │
     │────────────>│                │                 │                │               │
     │             │                │                 │                │               │
     │             │ 加载配置       │                 │                │               │
     │             │ vars/*.yml     │                 │                │               │
     │             │                │                 │                │               │
     │             │                │                 │                │               │
     │             │================== Group 1: Foundation Services ==================│
     │             │                │                 │                │               │
     │             │ include_tasks  │                 │                │               │
     │             │───────────────>│                 │                │               │
     │             │                │                 │                │               │
     │             │                │ [Phase 1]       │                │               │
     │             │                │ include_tasks   │                │               │
     │             │                │────────────────>│                │               │
     │             │                │                 │                │               │
     │             │                │                 │ 物料分发       │               │
     │             │                │                 │───────────────────────────────>│
     │             │                │                 │                │               │
     │             │                │                 │ docker rm -f   │               │
     │             │                │                 │───────────────────────────────>│
     │             │                │                 │                │               │
     │             │                │                 │ docker run     │               │
     │             │                │                 │───────────────────────────────>│
     │             │                │                 │                │     容器启动  │
     │             │                │                 │<───────────────────────────────│
     │             │                │<────────────────│                │               │
     │             │                │                 │                │               │
     │             │                │ [Phase 2]       │                │               │
     │             │                │ include_tasks   │                │               │
     │             │                │───────────────────────────────-->│               │
     │             │                │                 │                │               │
     │             │                │                 │                │ healthcheck   │
     │             │                │                 │                │──────────────>│
     │             │                │                 │                │  (循环等待)   │
     │             │                │                 │                │<──────────────│
     │             │                │                 │                │   healthy     │
     │             │                │<─────────────────────────────────│               │
     │             │<───────────────│                 │                │               │
     │             │                │                 │                │               │
     │             │================== Group 2: Business Services =====================│
     │             │                │                 │                │               │
     │             │ (重复上述流程)  │                 │                │               │
     │             │───────────────>│                 │                │               │
     │             │                │                 │                │               │
     │             │                │ (所有应用并行触发，然后逐个验证) │               │
     │             │                │                 │                │               │
     │             │<───────────────│                 │                │               │
     │             │                │                 │                │               │
     │             │ 生成摘要       │                 │                │               │
     │             │ _deploy_summary│                 │                │               │
     │             │                │                 │                │               │
     │<────────────│                │                 │                │               │
     │  部署完成    │                │                 │                │               │
     │             │                │                 │                │               │
```

### 5.2 分组执行时序对比

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              分组执行时序                                        │
└──────────────────────────────────────────────────────────────────────────────────┘

时间轴 ─────────────────────────────────────────────────────────────────────────────>

【串行执行模式 (组间)】

Group 1: Foundation Services
├── db_mysql_demo
│   ├──[启动]────[健康检查等待......]────[ready]
│   │
└── 完成 ─────────────────────────────────────────┐
                                                  │
                                                  ▼
                                        Group 2: Business Services
                                        ├── app_backend_1
                                        │   ├──[启动]──[健康检查]──[ready]
                                        │
                                        ├── app_backend_2
                                        │   ├──[启动]──[健康检查]──[ready]
                                        │
                                        └── 完成


【并行执行模式 (组内)】

Group 2: Business Services
时间 ─────────────────────────────────────────────────────>

app_backend_1:  [启动]═══════════[健康检查]═══[ready]
                    ↓ (几乎同时)
app_backend_2:  [启动]═══════════[健康检查]═══[ready]

说明:
- 同一分组内的应用启动命令被快速触发（接近并行）
- 健康检查阶段会依次等待每个应用就绪
- 整体效果：启动阶段并行，验证阶段顺序等待
```

### 5.3 健康检查等待时序

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            健康检查等待机制                                      │
└──────────────────────────────────────────────────────────────────────────────────┘

【有 Docker 原生健康检查的容器】

时间 ─────────────────────────────────────────────────────────────────────────>

容器状态:  [starting]──────[starting]──────[starting]──────[healthy]
               │              │              │              │
检查循环:     [check]        [check]        [check]        [check] ✓
              interval       interval       interval       
              (2s)           (2s)           (2s)           

结果: 健康检查通过，继续部署流程


【无健康检查的一次性任务容器】

时间 ─────────────────────────────────────────────────────────────────────────>

容器状态:  [running]───────[running]───────[exited (0)]
               │              │              │
检查循环:     [check]        [check]        [check] ✓
              "waiting"      "waiting"      "success"
              interval       interval       
              (5s)           (5s)           

结果: 容器成功退出 (exit_code=0)，继续部署流程


【健康检查超时失败】

时间 ─────────────────────────────────────────────────────────────────────────>

容器状态:  [starting]──────[unhealthy]─────[unhealthy]─────...
               │              │              │
检查循环:     [check]        [check]        [check]        ... retry N
              retries=1      retries=2      retries=3      

结果: 达到最大重试次数，部署失败
```

---

## 6. 配置规范

### 6.1 应用定义配置 (vars/apps.yml)

**完整配置结构**：

```yaml
app_definitions:
  # 应用名称（作为字典 key）
  app_name:
    # === 镜像配置（必填） ===
    image: "registry/image:tag"
    
    # === 端口映射（可选） ===
    ports:
      - "8080:80"        # 主机端口:容器端口
      - "8443:443"
    
    # === 数据卷挂载（可选） ===
    volumes:
      - "/host/path:/container/path"
      - "/data/logs:/app/logs:ro"  # 只读挂载
    
    # === 环境变量（可选） ===
    env:
      DB_HOST: "mysql.local"
      DB_PORT: "3306"
      LOG_LEVEL: "INFO"
    
    # === 环境变量文件（可选） ===
    env_file:
      - "/etc/app/db.env"
      - "/etc/app/secrets.env"
    
    # === 物料分发配置（可选） ===
    materials:
      - type: archive_dir           # 目录归档分发
        src: "materials/app_data"   # 本地源目录
        dest: "/opt/app/data"       # 远程目标目录
        owner: "app"
        group: "app"
        mode: "0755"
      
      - type: file                  # 单文件分发
        src: "materials/config.yml"
        dest: "/etc/app/config.yml"
        owner: "root"
        group: "root"
        mode: "0644"
    
    # === 健康检查参数（可选） ===
    healthcheck:
      retries: 30                   # 最大重试次数
      interval: 5                   # 检查间隔（秒）
    
    # === 原始命令（可选，优先级最高） ===
    raw_command: >-
      docker run -d 
      --name app_name
      --health-cmd="curl -f http://localhost/health || exit 1"
      --health-interval=10s
      --health-retries=3
      registry/image:tag
```

**配置优先级说明**：

| 配置项 | 优先级 | 说明 |
|--------|--------|------|
| `raw_command` | 最高 | 如果定义，直接使用此命令，忽略其他配置 |
| 其他配置 | 正常 | 当 `raw_command` 未定义时，自动拼接 Docker 命令 |

### 6.2 部署计划配置 (vars/plan.yml)

**完整配置结构**：

```yaml
# 分组部署计划
deploy_groups:
  # === 第一个分组 ===
  - name: "Foundation Services"      # 分组名称（用于日志显示）
    apps:
      - app_name: db_mysql           # 应用名称（对应 apps.yml 中的 key）
        target_ip: localhost         # 目标主机（inventory 中定义）
      
      - app_name: redis_cache
        target_ip: 192.168.1.10
  
  # === 第二个分组 ===
  - name: "Business Services"
    apps:
      - app_name: app_backend_1
        target_ip: localhost
      
      - app_name: app_backend_2
        target_ip: 192.168.1.20
  
  # === 第三个分组 ===
  - name: "Frontend Services"
    apps:
      - app_name: nginx_gateway
        target_ip: localhost
```

**分组执行规则**：

```
分组 1 ────> 分组 2 ────> 分组 3
 (串行)       (串行)       (串行)

组内应用：
┌─────────────────────────────────┐
│ app_1 ─┬─> 快速触发启动        │
│ app_2 ─┤                        │
│ app_3 ─┘   然后依次健康检查等待 │
└─────────────────────────────────┘
```

### 6.3 主机清单配置 (inventory.ini)

**配置示例**：

```ini
[all]
localhost ansible_connection=local

[db_servers]
192.168.1.10 ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa

[app_servers]
192.168.1.20 ansible_user=deploy
192.168.1.21 ansible_user=deploy

[web_servers]
192.168.1.30 ansible_user=www-data
```

**常用变量说明**：

| 变量 | 说明 | 示例 |
|------|------|------|
| `ansible_connection` | 连接方式 | local, ssh |
| `ansible_user` | SSH 用户名 | root, deploy |
| `ansible_ssh_private_key_file` | SSH 私钥路径 | ~/.ssh/id_rsa |
| `ansible_python_interpreter` | Python 解释器路径 | /usr/bin/python3 |

### 6.4 Ansible 配置 (ansible.cfg)

**当前配置**：

```ini
[defaults]
stdout_callback = yaml          # 使用 YAML 格式输出
bin_ansible_callbacks = True    # 启用回调插件
callbacks_enabled = timer, profile_tasks  # 启用计时和任务分析
host_key_checking = False       # 禁用 SSH 主机密钥检查
retry_files_enabled = False     # 禁用重试文件生成
inventory = inventory.ini       # 默认清单文件
```

**推荐生产配置**：

```ini
[defaults]
stdout_callback = yaml
callbacks_enabled = timer, profile_tasks
host_key_checking = True        # 生产环境建议开启
retry_files_enabled = True      # 便于失败重试
inventory = inventory.ini
forks = 10                      # 并行任务数
timeout = 30                    # SSH 连接超时
log_path = /var/log/ansible.log # 日志文件路径

[ssh_connection]
pipelining = True               # 提高 SSH 执行效率
control_path = /tmp/ansible-ssh-%%h-%%p-%%r
```

---

## 7. 扩展指南

### 7.1 添加新应用

**步骤 1**: 在 `vars/apps.yml` 中定义应用

```yaml
app_definitions:
  # ... 现有应用 ...
  
  # 新增应用
  my_new_app:
    image: my-registry/my-app:v1.0
    ports:
      - "9000:8080"
    volumes:
      - "/data/my_app:/app/data"
    env:
      ENV: "production"
    healthcheck:
      retries: 20
      interval: 3
```

**步骤 2**: 在 `vars/plan.yml` 中添加到部署计划

```yaml
deploy_groups:
  - name: "Business Services"
    apps:
      # ... 现有应用 ...
      - app_name: my_new_app
        target_ip: 192.168.1.50
```

### 7.2 添加新分组

```yaml
deploy_groups:
  # === 现有分组 ===
  - name: "Foundation Services"
    apps: [...]
  
  - name: "Business Services"  
    apps: [...]
  
  # === 新增分组（会在 Business Services 之后执行） ===
  - name: "Monitoring Stack"
    apps:
      - app_name: prometheus
        target_ip: monitor-server
      - app_name: grafana
        target_ip: monitor-server
```

### 7.3 自定义健康检查

**方式 1**: 在 Docker 命令中定义（推荐）

```yaml
my_app:
  raw_command: >-
    docker run -d --name my_app
    --health-cmd="curl -sf http://localhost:8080/health || exit 1"
    --health-interval=5s
    --health-start-period=30s
    --health-timeout=3s
    --health-retries=5
    my-image:latest
```

**方式 2**: 使用 Dockerfile 定义

```dockerfile
FROM alpine:latest
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
  CMD wget -q --spider http://localhost:8080/health || exit 1
```

**方式 3**: 无健康检查的一次性任务

```yaml
# 适用于初始化脚本、数据迁移等
init_task:
  image: alpine:latest
  raw_command: >-
    docker run --name init_task
    alpine:latest 
    sh -c "echo 'Initializing...'; sleep 5; echo 'Done'"
```

### 7.4 添加物料分发

**目录分发示例**：

```yaml
nginx_web:
  image: nginx:alpine
  ports: ["80:80"]
  materials:
    - type: archive_dir
      src: "materials/web_static"     # 本地 ./materials/web_static/
      dest: "/usr/share/nginx/html"   # 容器启动前同步到此目录
      owner: "nginx"
      group: "nginx"
      mode: "0755"
```

**配置文件分发示例**：

```yaml
my_service:
  image: my-service:latest
  materials:
    - type: file
      src: "materials/config/app.yml"
      dest: "/etc/my-service/config.yml"
      mode: "0644"
    
    - type: file
      src: "materials/secrets/db.env"
      dest: "/etc/my-service/db.env"
      mode: "0600"  # 敏感文件限制权限
```

### 7.5 多环境配置

**目录结构建议**：

```
vars/
├── apps.yml              # 共享的应用定义
├── plan_dev.yml          # 开发环境部署计划
├── plan_staging.yml      # 预发布环境部署计划
└── plan_prod.yml         # 生产环境部署计划
```

**环境特定部署命令**：

```bash
# 开发环境
ansible-playbook deploy.yml -e "@vars/plan_dev.yml"

# 预发布环境
ansible-playbook deploy.yml -e "@vars/plan_staging.yml"

# 生产环境
ansible-playbook deploy.yml -e "@vars/plan_prod.yml" --ask-vault-pass
```

### 7.6 集成 CI/CD

**GitLab CI 示例**：

```yaml
# .gitlab-ci.yml
stages:
  - deploy

deploy_production:
  stage: deploy
  image: ansible/ansible:latest
  script:
    - ansible-playbook deploy.yml -e "@vars/plan_prod.yml"
  only:
    - main
  tags:
    - production-runner
```

**Jenkins Pipeline 示例**：

```groovy
pipeline {
    agent any
    stages {
        stage('Deploy') {
            steps {
                sh 'ansible-playbook deploy.yml -e "@vars/plan_${ENVIRONMENT}.yml"'
            }
        }
    }
}
```

---

## 附录

### A. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| SSH 连接失败 | 主机密钥验证失败 | 检查 `ansible.cfg` 中的 `host_key_checking` |
| 容器启动失败 | 端口冲突 | 检查目标主机端口占用，使用 `netstat -tlnp` |
| 健康检查超时 | 重试次数不足 | 增加 `healthcheck.retries` 值 |
| 物料分发失败 | 目录权限问题 | 检查 `sync_owner` 和 `sync_mode` 配置 |
| 命令拼接错误 | YAML 多行字符串格式 | 使用 `>-` 折叠符并注意缩进 |

### B. 调试技巧

```bash
# 详细输出模式
ansible-playbook deploy.yml -vvv

# 仅检查语法
ansible-playbook deploy.yml --syntax-check

# 模拟执行（不实际执行）
ansible-playbook deploy.yml --check

# 指定标签执行
ansible-playbook deploy.yml --tags "start,verify"

# 从特定任务开始
ansible-playbook deploy.yml --start-at-task="Run Container"
```

### C. 测试验证

运行集成测试套件：

```bash
python3 tests/integration_test.py
```

测试项包括：
1. Playbook 执行成功验证
2. 容器存在性检查
3. 健康状态验证
4. HTTP 端点可达性
5. 分组执行顺序验证

---

**文档版本**: 1.0  
**最后更新**: 2025年12月  
**作者**: 自动生成
