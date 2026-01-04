# Ansible Navigator 离线安装指南

本指南提供了如何在无外网连接的服务器上安装 `ansible-navigator` 的具体操作步骤。

## 准备工作 (有外网的机器)

请在您的本地机器或具有外网访问权限的服务器上执行以下步骤：

1.  **创建包管理器目录**：
    ```bash
    mkdir -p ansible_navigator_offline/packages
    cd ansible_navigator_offline
    ```

2.  **下载所有依赖包**：
    使用 `pip download` 命令获取所有必要的 Wheel 文件。
    ```bash
    pip download ansible-navigator \
        --dest ./packages \
        --only-binary=:all:
    ```

3.  **打包资源**：
    ```bash
    tar -czvf ansible_navigator_bundle.tar.gz ./packages
    ```

## 实施安装 (离线服务器)

请将 `ansible_navigator_bundle.tar.gz` 拷贝到目标离线服务器，并执行以下操作：

1.  **解压安装包**：
    ```bash
    tar -xzvf ansible_navigator_bundle.tar.gz
    cd packages
    ```

2.  **执行离线安装**：
    使用 `--no-index` 和 `--find-links` 参数，强制 pip 只从当前目录寻找安装包。
    ```bash
    pip install --no-index --find-links=. ansible-navigator
    ```

3.  **配置 Navigator**：
    在您的项目根目录下创建 `ansible-navigator.yml`，以确保它在本地环境运行（不依赖 Docker）：
    ```yaml
    ansible-navigator:
      ansible:
        inventory:
          entries:
            - inventory.ini
      execution-environment:
        enabled: false
      mode: interactive
    ```

## 验证安装

安装完成后，运行以下命令验证：

```bash
# 检查版本
ansible-navigator --version

# 启动交互式界面
ansible-navigator run your_playbook.yml
```

> [!TIP]
> 如果离线服务器缺少的基础环境（如 Python 或 Pip）版本过低，建议先升级 Python 环境。
