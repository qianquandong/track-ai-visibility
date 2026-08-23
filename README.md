# Track AI Visibility

**English** | [中文](./README.zh-CN.md)

A local-first Agent Skill for auditing how often a brand appears in AI-assisted search and recommendation surfaces. It works in both Codex and Claude Code, keeps evidence in readable local files, and does not require an OpenAI, Anthropic, CrowdReply, Reddit, or model-provider API key.

## What it does

- Tracks brand visibility across researched prompts and surfaces.
- Finds prompts where competitors appear but the tracked brand does not.
- Aggregates citation domains and surfaces missing citation opportunities.
- Records public Reddit and web discussions as evidence.
- Produces Markdown reports with sample sizes and capture dates.
- Uses preview-and-confirm flows for local action tasks.

The agent performs current web research with the browsing tools already available in Codex or Claude. The bundled Python script only validates, stores, summarizes, and reports the evidence.

## Install for Codex and Claude Code

```bash
git clone https://github.com/qianquandong/track-ai-visibility.git
cd track-ai-visibility
./install.sh
```

The installer creates symlinks in both personal skill directories:

- Codex: `~/.codex/skills/track-ai-visibility`
- Claude Code: `~/.claude/skills/track-ai-visibility`

Existing installations are moved to timestamped backups. Run `./install.sh --codex` or `./install.sh --claude` to install only one integration. Restart the app if this is the first skill in its personal skills directory.

### Use it

In Codex:

```text
Use $track-ai-visibility to audit the AI visibility of example.com.
```

In Claude Code after personal-skill installation:

```text
/track-ai-visibility Audit the AI visibility of example.com.
```

### Claude plugin marketplace installation

The repository is also a Claude plugin marketplace:

```bash
claude plugin marketplace add qianquandong/track-ai-visibility
claude plugin install track-ai-visibility@qianquandong-tools
```

The plugin command is namespaced:

```text
/track-ai-visibility:track-ai-visibility Audit the AI visibility of example.com.
```

## Local data

Each tracked project stores its state under `.ai-visibility/`:

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

The files are portable JSON, JSONL, and Markdown. Do not put secrets in this directory. The repository ignores local visibility data by default.

## Safety and limitations

- Results describe only the prompts, public surfaces, and dates that were actually checked.
- A blocked or sign-in-only AI surface is reported as unobserved; the skill does not simulate private model results.
- It never needs provider API keys.
- Publishing, posting, voting, ordering content, or spending money remains a separate external action and requires explicit confirmation at action time.
- Local task confirmation is idempotent, so retrying the same token does not create a duplicate.

## Development

The storage tool uses only the Python standard library.

```bash
python3 -m unittest discover -s tests -v
python3 skills/track-ai-visibility/scripts/visibility_store.py --help
sh -n install.sh uninstall.sh
```

If the Claude CLI is available, validate the plugin and marketplace with:

```bash
claude plugin validate .
```

## License

MIT
