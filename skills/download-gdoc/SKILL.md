---
name: download-gdoc
description: Download content from a Google Doc by URL or ID and bring it into the conversation. Use when the user mentions a Google Doc, wants to read a gdoc, or references a docs.google.com URL. Docs are cached at ~/.claude/gdocs/ and reused across sessions.
user-invocable: true
argument-hint: <google-doc-url-or-id>
allowed-tools: Bash(python3 *), Read, Grep, Glob
---

# Download Google Doc

Download a Google Doc as Markdown, cached to `~/.claude/gdocs/` for reuse across sessions and projects.

## Prerequisites

Python dependencies installed: `pip install google-auth google-api-python-client`

## Steps

1. Run the download script. It will cache the doc and print its content:

```bash
python3 ~/.claude/skills/download-gdoc/scripts/download_gdoc.py $ARGUMENTS
```

The script handles auth automatically via gcloud ADC. If no credentials exist or they've expired, it runs `gcloud auth application-default login` which opens a browser. This only happens once (credentials are cached).

The script automatically caches to `~/.claude/gdocs/{doc_id}.md` with a `.meta.json` sidecar. If the doc hasn't changed since last download, it serves from cache.

Use `--force` to re-download even if cached. Use `--path-only` to get just the file path.

2. Present the content to the user. Summarize if they asked for a summary, or present the full text if they want raw content.

## Searching cached docs

All downloaded docs live at `~/.claude/gdocs/*.md`. To search across them:

- Use Grep to search content: `Grep pattern ~/.claude/gdocs/`
- Use Glob to list cached docs: `Glob ~/.claude/gdocs/*.md`
- Read a specific cached doc by its path: `Read ~/.claude/gdocs/{doc_id}.md`
- Read metadata (title, URL, modifiedTime): `Read ~/.claude/gdocs/{doc_id}.meta.json`
