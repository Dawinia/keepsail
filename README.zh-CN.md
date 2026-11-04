# Keepsail

让决策与产品知识在持续的 AI 编程会话中保持有效。

[English](README.md) | **简体中文**

Keepsail 是面向开发者和产品负责人的开源产品工作控制层。它记录哪些工作已经获批、
哪些产品约束适用，以及什么证据支持完成结论，让编程 Agent 在约定范围内自主推进，
并在恢复工作时找回已记录的上下文。

Keepsail 通过 CLI、Agent hooks 和 CI 检查接入现有开发流程。集成包括 Claude Code、
Codex（实验性）、OpenSpec、Superpowers，以及直接使用 CLI 的 plain 工作流。

**状态：Alpha。** 当前知识交付在单仓库内运行，依据显式规则和获认可的适用性判断。
不同 Agent 和接入模式的覆盖范围有所不同，见[当前限制](#当前限制)。

## 为什么使用 Keepsail？

持续的 Agent 工作需要保留超出当前对话的信息：

- **延续批准依据。** 保存目标、验收义务和明确限制。计划获批后，Agent 可以在这些
  边界内调整实现、补充文件，无需因每次新发现都重新走一遍批准流程。
- **演进产品知识。** 保留约束的版本及理由。约束变化时，记录它对在途工作的影响，
  以及继续、调整或重新申请批准的处置结论。
- **恢复工作依据。** 跨会话恢复批准、已交付知识和未决事项。可选的上下文集成
  分别记录提供了什么，以及实际获取操作返回了什么。
- **核查完成依据。** 将审查和验证证据绑定到对应的计划或代码，并在已接入的工具
  和流程环节执行配置的规则检查。

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
- 知识选择依赖显式规则和获认可的判断。跨仓库共享知识权威与完整语义召回尚未实现。
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
