# Local data schema

All state lives in `<project-root>/.ai-visibility/`.

## Files

- `config.json`: brand, project, competitors, tracked keywords, schema version.
- `prompts.jsonl`: one prompt record per line.
- `observations.jsonl`: one researched prompt/surface result per line.
- `mentions.jsonl`: Reddit or other listening evidence.
- `tasks.jsonl`: confirmed local action tasks.
- `pending-actions.jsonl`: short-lived task previews and confirmation tokens.
- `reports/`: generated Markdown reports.

## Prompt record

```json
{"id":"prm_...","text":"best AI agent newsletters","status":"active","tags":["category"],"created_at":"2026-08-06T12:00:00Z"}
```

## Observation record

Required: `prompt_id` or `prompt_text`, `surface`, and `brand_mentioned`.

```json
{
  "id": "obs_...",
  "prompt_id": "prm_...",
  "prompt_text": "best AI agent newsletters",
  "captured_at": "2026-08-06T12:00:00Z",
  "surface": "codex-web-research",
  "brand_mentioned": false,
  "brand_position": null,
  "answer_summary": "Three newsletters were recommended; the tracked brand was absent.",
  "competitors": [{"name":"Competitor A","position":1}],
  "citations": [{"url":"https://example.org/list","domain":"example.org","title":"AI newsletters"}],
  "evidence_urls": ["https://example.org/list"]
}
```

## Mention record

```json
{
  "id": "mnt_...",
  "source": "reddit",
  "keyword": "AI agent newsletter",
  "title": "What newsletters are worth reading?",
  "url": "https://www.reddit.com/r/example/comments/...",
  "snippet": "Short evidence-grounded excerpt or paraphrase",
  "author": "u/example",
  "published_at": "2026-08-05T12:00:00Z",
  "captured_at": "2026-08-06T12:00:00Z",
  "engagement": {"score": 12, "comments": 4}
}
```

## Task record

```json
{
  "id": "tsk_...",
  "kind": "content",
  "title": "Publish a comparison page",
  "details": "Target the highest-opportunity missing prompt.",
  "status": "queued",
  "cost_credits": 0,
  "idempotency_key": "...",
  "created_at": "2026-08-06T12:00:00Z",
  "updated_at": "2026-08-06T12:00:00Z"
}
```

## Import behavior

- The script generates missing IDs and capture timestamps.
- It derives missing citation domains from URLs.
- It rejects malformed required fields.
- Existing IDs are skipped, making repeated imports idempotent.
- Never place passwords, cookies, API keys, or private browsing data in these files.
