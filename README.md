# claude-tools

A collection of custom skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Skills

| Skill | Invocation | Description |
|-------|------------|-------------|
| **download-gdoc** | `/download-gdoc <url-or-id>` | Downloads a Google Doc as Markdown and brings it into the conversation. Docs are cached at `~/.claude/gdocs/` and reused across sessions. Authenticates via gcloud ADC. |

## Installation

```bash
./install.sh
```

This symlinks each skill directory from `skills/` into `~/.claude/skills/`, making them available to Claude Code.
