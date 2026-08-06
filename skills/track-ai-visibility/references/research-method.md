# Research method

## Visibility scan

1. Select 5–20 active prompts representing buyer intent, comparisons, alternatives, and problem-aware questions.
2. For each prompt, inspect only the surfaces the user requested or that are publicly available.
3. Record whether the brand appears, its ordinal position when meaningful, named competitors, answer summary, citations, and evidence URLs.
4. Import observations and calculate metrics with the bundled script.

Do not rewrite the prompt between competitors. Keep the same wording within a comparison batch.

## Metric definitions

- **Visibility rate** = observations mentioning the brand / all observations.
- **Prompt coverage** = prompts with at least one observation / active prompts.
- **Citation rate** = observations citing the brand's canonical domain / all observations.
- **Average position** = mean recorded ordinal position, excluding observations without a meaningful rank.
- **Competitor mention share** = competitor mentions / all recorded competitor mentions.
- **Opportunity score (0–100)** = 60% brand absence + 25% competitor presence + 15% external citation concentration. Treat it as prioritization, not a forecast.

Always show denominators. A 50% visibility rate from 2 observations is not equivalent to 50% from 100.

## Citation analysis

- Capture a URL only when it is visibly cited or used as evidence in the researched answer.
- Normalize domains by removing `www.` and lowercasing.
- Group repeated domains and identify which high-frequency sources do not mention or link to the tracked brand.
- Distinguish owned-domain citations from third-party citations.

## Competitor comparison

- Start from configured competitors, but also record unconfigured brands that repeatedly appear.
- Preserve the observed order; do not infer a numeric rank from unordered prose.
- Call a prompt a gap when at least one competitor appears and the tracked brand does not.
- Rank gaps by repeated evidence, buyer intent, and feasible content/distribution actions.

## Reddit listening

- Search current public threads by tracked keyword, brand name, category, and pain-point language.
- Prefer direct Reddit thread URLs and capture published date, subreddit when visible, engagement, and a short paraphrase.
- Separate requests for recommendations, complaints, comparisons, and purchase intent.
- Do not post, vote, message, or log in without explicit user authorization at action time.

## Freshness

- Default current scan window: 30 days.
- Treat visibility observations older than 30 days as historical unless the user selects another window.
- Record the exact capture date and surface for every observation.
