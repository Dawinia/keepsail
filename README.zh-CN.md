# Keepsail

面向多种编程 Agent 的开源产品工作控制层。

[English](README.md) | **简体中文**

使用 Keepsail，产品负责人可以批准一项工作要交付什么、划定 Agent 的权限，并在交付时核查哪一版成果经过了审查和验证。Agent 可以在批准范围内自行决定实现办法。如果实施中需要改变已约定的要求，就要为这项变化取得新的批准。

Keepsail 通过 CLI、Agent hooks 和 CI 检查接入现有开发流程。集成包括 Claude Code、
Codex（实验性）、OpenSpec、Superpowers，以及直接使用 CLI 的 plain 工作流。

**状态：Alpha。** 各种接入方式的覆盖范围见[当前限制](#当前限制)。

## 为什么使用 Keepsail？

- **给 Agent 留出实施空间。** 为已批准的验收测试补一份测试数据，Agent 可以自行处理并记录理由。取消这项测试会改变原有承诺，需要重新审查计划。
- **让偏离及时显现。** 本地 hook 检查指定工具发起的编辑。合并前，配置好的检查可以指出哪些验证缺失，或某份审查结论只覆盖了旧版代码。
- **让下一次会话接得上。** 新会话可以找回已批准的计划、适用的约束和未决问题，继续推进同一项工作。
- **追踪产品知识的变化。** 一条已获认可的约束更新后，可以查到哪些工作收到过旧版本，并记录每项受影响的工作该如何继续。

[项目概览](docs/overview.md)通过示例介绍工作方式；
[产品架构](docs/product-architecture.md)定义产品职责。

## 安装

Keepsail 要求 **Python 3.10+**。按下面的步骤从源码安装，还需确保在终端中可以运行
Git 和 pipx。安装当前版本的 pipx 需要 **Python 3.11+**，详见
[pipx 安装指南](https://pipx.pypa.io/stable/how-to/install-pipx.html)。

```sh
git clone https://github.com/Dawinia/keepsail.git
cd keepsail
pipx install .
keepsail --version
```

如需启用可选的 GitHub 集成，请安装 [GitHub CLI](https://cli.github.com/)
并运行 `gh auth login`。

从 **super-harness** 升级？请先阅读[迁移指南](docs/keepsail-migration.md)。

## 快速开始

在一个 Git 仓库中体验本地生命周期门禁。先初始化 Keepsail：

```sh
cd path/to/your-repo
keepsail init
```

初始化时选择 Agent 集成，或显式安装其中一个：

```sh
keepsail adapter install claude-code
# 或者：
keepsail adapter install codex
```

在该仓库打开新的 Agent 会话，并完成宿主要求的 hook 信任步骤。
Codex 用户需先通过 `/hooks` 查看并信任 Keepsail hooks。
具体接入说明见 [Claude Code](docs/adapters/claude-code.md) 和
[Codex](docs/adapters/codex.md) 指南。

从终端声明一次变更：

```sh
keepsail change start my-change
keepsail status my-change
```

此时变更处于 `INTENT_DECLARED`。hook 生效后，Agent 通过覆盖范围内的编辑工具
尝试修改源文件，会因计划尚未获批而被阻止。这展示的是本地门禁；手动编辑器操作、
shell 命令和 MCP 写入不在该拦截范围内。

继续工作时，按[入门指南](docs/getting-started.md)配置所有者认可的审查流程、
提交计划并导入结论。正常路径是：

```text
声明变更 → 计划审查 → 实施 → 验证 → 代码审查 → 合并归档
```

Keepsail 导入所选流程的审查结论，不负责运行审查者。计划获批后，Agent 可以记录
批准范围内的实施调整；改变原有承诺需要取得相应的新批准。

### 知识与会话上下文

[知识指南](docs/knowledge.md)介绍策略激活、约束版本、交付和影响处理，这些能力
需要显式配置。若要接入会话绑定的交付与获取观察，请按可选的
[上下文集成指南](docs/knowledge-context.md)操作，其中包括选定的 Windows 本地
Codex 桌面接入方式。基础快速开始不会启用该模式。

## 当前限制

- 本地 hooks 只覆盖选定工具，且必须由宿主实际启用。CI 检查需要安装并配置为
  分支保护的必需检查，才能约束合并。
- 知识交付在单仓库内运行，依据显式规则和获认可的适用性判断选择约束。
- 获取记录不证明理解，Agent 的采用声明不证明遵从。审查质量仍由获认可的流程负责。

[实现覆盖报告](docs/product-architecture-coverage.md)记录带日期的证据；
[限制与常见问题](docs/limitations.md)提供运行细节。

## 文档

| 目标 | 指南 |
|---|---|
| 完成一次变更 | [入门指南](docs/getting-started.md) · [核心概念](docs/concepts.md) |
| 管理知识与会话连续性 | [知识](docs/knowledge.md) · [会话上下文](docs/knowledge-context.md) |
| 检查架构决策 | [接入项目](docs/adopting.md) |
| 配置集成 | [Agent 与框架适配器](docs/adapters/) |
| 查询命令 | [CLI 参考](docs/cli-reference.md) |
| 理解设计 | [产品架构](docs/product-architecture.md) · [内部架构](docs/ARCHITECTURE.md) |

完整指南见[文档索引](docs/README.md)。链接保留各文档现有语言。

## 求助与贡献

请通过 [GitHub Issues](https://github.com/Dawinia/keepsail/issues) 报告问题或提出改进建议。
报告问题时，请附上操作系统、Keepsail 版本、Agent 集成、复现步骤，以及去除敏感信息的
相关输出。

修改项目之前，请阅读 [AGENTS.md](AGENTS.md) 中的计划、审查和验证流程。
开发时先创建并激活 Python 虚拟环境，再在仓库根目录安装：

```sh
python -m pip install -e ".[dev]"
```

项目使用 Ruff、mypy 和 pytest。配置的检查通过 `keepsail verify` 执行，
详见 [CLI 参考](docs/cli-reference.md)。

## 许可证

[MIT](LICENSE)。
