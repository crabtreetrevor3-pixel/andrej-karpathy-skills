# CONTRIBUTING

This file provides guidance to Claude Code (claude.ai/code) — and human contributors — when working in this repository.

## What this repo is

This is **not** an application codebase. There is no build, lint, or test tooling, no package manifest, and no source code to compile. The repo's entire purpose is to distribute a single piece of content — four behavioral guidelines for LLM coding agents, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) — through three different distribution channels at once.

## Critical convention: the content is triplicated and must stay in sync

The four principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) exist verbatim in **three files**:

| File | Distribution channel |
|---|---|
| `CLAUDE.md` | Curled directly into other projects' `CLAUDE.md` (see install instructions in `README.md`); also the root instructions Claude Code loads when working *in this repo* |
| `skills/karpathy-guidelines/SKILL.md` | Installed as an Agent Skill via the Claude Code plugin (`.claude-plugin/`) or copied into `~/.cursor/skills` |
| `.cursor/rules/karpathy-guidelines.mdc` | Committed Cursor project rule (`alwaysApply: true`), same content with Cursor frontmatter |

**If you edit the principles, edit all three and keep the prose identical** (frontmatter/headers aside). This is stated explicitly in `CURSOR.md`. Do not treat `CLAUDE.md` in this repo as ordinary "project instructions" scaffolding — its body text is the shipped product, so avoid adding repo-maintenance content, tool-usage notes, or anything else into it that isn't meant to be curled into a stranger's project.

`README.md` and `README.zh.md` are parallel English/Chinese translations of the same content; update both when changing install instructions, principles, or structure.

## Repository layout

- `CLAUDE.md` — the four-principles payload (see above)
- `README.md` / `README.zh.md` — project overview, rationale, install instructions (plugin + per-project CLAUDE.md), bilingual
- `CURSOR.md` — Cursor-specific setup notes and the sync requirement across the three files
- `EXAMPLES.md` — worked before/after code examples illustrating each of the four principles in practice
- `.claude-plugin/plugin.json` — plugin manifest (name, version, points to `./skills/karpathy-guidelines`)
- `.claude-plugin/marketplace.json` — marketplace listing wrapping the plugin, owner `forrestchang`
- `skills/karpathy-guidelines/SKILL.md` — the Agent Skill version, with `name`/`description`/`license` frontmatter used for skill discovery
- `.cursor/rules/karpathy-guidelines.mdc` — the Cursor rule version, with `description`/`alwaysApply` frontmatter

## Versioning

`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` both carry a `version` field (currently `1.0.0`). Bump these when the shipped principles or plugin structure change, so plugin-marketplace users pick up updates.

## No build/test workflow

There is nothing to install, build, lint, or run. "Verification" for a change here means: re-reading the three synced copies side by side for drift, and checking that the install commands in `README.md`/`README.zh.md` (the `curl` URLs, `/plugin marketplace add` / `/plugin install` commands) still point at valid paths.
