# News Data Directory

This directory is the local source of truth for the financial intelligence graph.

The server writes live RSS snapshots here automatically:

- `rss-latest.json`
- `rss-archive-YYYY-MM-DD.json`

You can add your own intelligence files at any time:

- JSON: an array of news items or `{ "items": [...] }`
- Markdown: one document per file; title is the first `# heading`

Recommended JSON item shape:

```json
{
  "title": "Fed signals rates path",
  "summary": "Short description of the event.",
  "category": "经济数据",
  "source": "Custom source",
  "publishedAt": "2026-06-22T09:00:00.000Z",
  "url": "https://example.com",
  "symbols": ["^TNX", "DX-Y.NYB"],
  "region": "Americas"
}
```

The graph builder maps items to assets, regions, themes, entities, and causal relations.
