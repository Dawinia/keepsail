# Keepsail

> 跨 agent harness 的产品工作控制层。

[English](README.md) | **简体中文**

## Keepsail 是什么?

Keepsail 让有效人类承诺与长期产品知识在连续工作中持续生效，支持授权范围内的
自主行动、知识演进、连续性与可追溯性。产品定位以
[产品架构](docs/product-architecture.md)为准，现有 CLI、hooks 与 CI 的覆盖情况见
单独的[实现覆盖报告](docs/product-architecture-coverage.md)。

Keepsail 原名 super-harness。[迁移说明](docs/keepsail-migration.md)列出直接迁移、
本地使用项目的更新方式和交付边界。

关于它解决的问题、v0.1 交付了什么、以及跟邻近工具的关系,见
[Overview](docs/overview.md)。

## 安装

```bash
# 在包含本次迁移的源码 checkout 中安装；注册表发布尚待完成：
pipx install .
brew install gh && gh auth login   # gh 是 init --setup-github 的前置依赖
```

## Quickstart

引导一个仓库，观察一个已实现的控制面：门会拦住一次“越出生命周期”的编辑。

```bash
# 先在 Keepsail checkout 中执行 pipx install .
cd your-repo && keepsail init            # 创建 .harness/ 数据面
keepsail adapter install claude-code     # 接入你的 agent(若有 .claude/,init 会自动装)
#   Codex 用法:     keepsail adapter install codex   → 再在 Codex 里跑 /hooks 信任它
keepsail change start "my-change"        # → INTENT_DECLARED
# 现在让你的 agent(或你)去改代码 → 门会拦住,
# 因为还没经过 plan review。这展示了一个控制面。
```

这是"看见 keepsail 工作"的最短路径。完整流程 —— 装框架适配器、过 plan review、
实现、验证、评审、合并 —— 是 10 分钟的 [Getting started](docs/getting-started.md) 走查。
想不跑任何东西就看一个预置的非平凡 `.harness/` 状态,见仓内示例
[`examples/demo-openspec-claude/`](examples/demo-openspec-claude/)。走查也展示了
当前 review 契约：用户在 `.harness/review-recognition.yaml` 认可外部审查流程，
由该流程提供准确 subject、明确 plan/code 结论、原始证据和来源，再通过
`keepsail review import` 导入。获批承诺内的实施调整以 assessment 和实际
文件 coverage 留痕；执行和重试由外部流程负责。历史配置与事件保留可读，
demo 是历史样例数据，不是当前 review 的执行指南。

## 链接

- [文档索引](docs/README.md)
- [Overview](docs/overview.md) —— 它是什么、v0.1 交付了什么、邻近工具
- [Getting started](docs/getting-started.md) —— 完整端到端走查
- [Concepts](docs/concepts.md) —— 生命周期,以及 harness *不*替你做的事
- [Adopting](docs/adopting.md) —— 在你自己的项目里锁住架构规则
- [Limitations & FAQ](docs/limitations.md)
- [Agent 适配器](docs/adapters/) —— [Claude Code](docs/adapters/claude-code.md) · [Codex](docs/adapters/codex.md)(实验性)
- [CLI reference](docs/cli-reference.md)
- [Architecture](docs/ARCHITECTURE.md)

> 说明:深度文档(`docs/`)目前仅有英文;本页是面向中文读者的入口,链接指向同一份英文文档。

## License

MIT —— 见 [`LICENSE`](LICENSE)。
