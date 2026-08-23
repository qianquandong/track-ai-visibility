# Track AI Visibility

[English](./README.md) | **中文**

一个本地优先的 Agent Skill，用来审计一个品牌在 AI 搜索和推荐结果里出现的频率。Codex 和 Claude Code 里都能跑，证据保存为人能直接读的本地文件，不需要 OpenAI、Anthropic、CrowdReply、Reddit 或任何模型服务商的 API key。

## 它做什么

- 追踪品牌在已调研 prompt 和各个平台上的可见度。
- 找出竞品出现了、被追踪品牌却没出现的 prompt。
- 汇总引用域名，找出还没拿到的引用机会。
- 把公开的 Reddit 和网络讨论记录为证据。
- 生成带样本量和采集日期的 Markdown 报告。
- 本地写入类操作走「先预览、再确认」流程。

联网调研由 Codex 或 Claude 自带的浏览工具完成，附带的 Python 脚本只负责校验、存储、汇总和出报告。

## 安装（Codex 和 Claude Code）

```bash
git clone https://github.com/qianquandong/track-ai-visibility.git
cd track-ai-visibility
./install.sh
```

安装脚本会在两个个人 skill 目录里建软链：

- Codex：`~/.codex/skills/track-ai-visibility`
- Claude Code：`~/.claude/skills/track-ai-visibility`

已有的安装会被移到带时间戳的备份。只装一边可以用 `./install.sh --codex` 或 `./install.sh --claude`。如果这是对应目录里的第一个 skill，重启应用生效。

### 使用

在 Codex 里：

```text
用 $track-ai-visibility 检查 example.com 的 AI 可见度，并找出最值得优先补的内容缺口。
```

在 Claude Code 里：

```text
/track-ai-visibility 检查 example.com 的 AI 可见度。
```

### 通过 Claude 插件市场安装

这个仓库同时是一个 Claude 插件市场：

```bash
claude plugin marketplace add qianquandong/track-ai-visibility
claude plugin install track-ai-visibility@qianquandong-tools
```

插件命令带命名空间：

```text
/track-ai-visibility:track-ai-visibility 检查 example.com 的 AI 可见度。
```

## 本地数据

每个被追踪的项目把状态存在 `.ai-visibility/` 下：

```text
.ai-visibility/
├── config.json
├── prompts.jsonl
├── observations.jsonl
├── mentions.jsonl
├── tasks.jsonl
├── pending-actions.jsonl
└── reports/
```

全部是可迁移的 JSON、JSONL 和 Markdown。别把密钥放进这个目录。仓库默认忽略本地可见度数据。

## 安全与限制

- 结果只描述实际检查过的 prompt、公开平台和日期。
- 被墙或必须登录的 AI 平台会记为 unobserved，skill 不会模拟私有模型的结果。
- 永远不需要服务商 API key。
- 发布、发帖、投票、约稿、花钱这类动作属于独立的外部操作，执行时需要单独确认。
- 本地任务确认是幂等的，同一个 token 重试不会产生重复记录。

## 开发

存储工具只用 Python 标准库。

```bash
python3 -m unittest discover -s tests -v
python3 skills/track-ai-visibility/scripts/visibility_store.py --help
sh -n install.sh uninstall.sh
```

装了 Claude CLI 的话，可以顺便校验插件和市场配置：

```bash
claude plugin validate .
```

## License

MIT
