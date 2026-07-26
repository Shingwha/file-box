---
name: file-box-cli
description: >-
  CLI tool to operate a shared file-box (Railway deployed). Lists, downloads,
  uploads, deletes files, checks storage. Already configured with the user's
  server. Use this whenever the user wants to check files, upload/download
  something, or manage their file box.
---

# file-box CLI

Already configured — just run commands.

## Setup (one-time)

```bash
file-box config login https://file-box-production.up.railway.app 745632589cxy
```

Already done — config persists in `~/.config/file-box.json`.

## Commands

| Task | Command |
|------|---------|
| List files | `file-box ls` |
| Download files | `file-box dl <name1> <name2> ...` |
| Upload files | `file-box up <local-path> ...` |
| Delete files | `file-box rm <name1> <name2> ...` |
| Storage usage | `file-box df` |
| Show config | `file-box config get` |

All commands have short aliases: `ls`, `dl`/`get`, `up`/`put`, `rm`/`del`, `df`/`space`.

## Examples

```bash
file-box ls                        # list files
file-box dl paper.pdf              # download one
file-box dl a.pdf b.pdf c.pdf      # download multiple
file-box up ./report.pdf           # upload
file-box rm temp.txt old.txt       # batch delete
file-box df                        # check storage
```

## Notes

- Pure Python stdlib — zero external dependencies
- Config file: `~/.config/file-box.json` (auto-saved by `config login`)
- Override with env vars: `FILE_BOX_URL`, `FILE_BOX_TOKEN`
