---
name: project-guardian
description: Enforces strict phased development and architectural discipline for the desktop catalog manager project.
---

# Project Guardian

## Purpose
Enforce strict architectural discipline and phased development for the desktop catalog manager.

## Global Rules
- NEVER implement features outside the current phase.
- ALWAYS follow repository -> service -> UI architecture.
- NEVER mix UI with API or DB logic.
- NEVER refactor unrelated modules.
- ALWAYS make minimal, targeted changes.

## Phase Control
Before writing code:
1. Identify current phase.
2. List allowed actions.
3. List forbidden actions.

If the task exceeds the current phase, stop and explain why.

## Architecture Rules

### Layering
UI -> Controller/ViewModel -> Service -> Repository -> DB

- UI must not call WooCommerce directly.
- UI must not execute SQL.
- API calls must live in services only.

## WooCommerce / WordPress Rules

### Separation of APIs
- WooCommerce:
  - endpoint: `/wc/v3`
  - auth: Consumer Key / Consumer Secret

- WordPress Media:
  - endpoint: `/wp/v2/media`
  - auth: Basic Auth with Application Password

NEVER mix these two systems.

## Data Integrity
- Use `external_wc_id` as the primary mapping key.
- NEVER match entities by name.
- NEVER create duplicates.

### Create vs Update
- if `external_wc_id` is null -> CREATE
- if `external_wc_id` exists -> UPDATE

## Image Handling Rules
- `source_url` = remote image
- `local_path` = downloaded local image
- NEVER overwrite existing local files
- NEVER re-download if `local_path` exists

## Sync Status Rules
Allowed statuses:
- synced
- modified_local
- new_local
- publish_pending
- publish_error

Transitions must be explicit and predictable.

## Safety Rules
Before making changes:
1. Analyze impact.
2. Limit scope.
3. Avoid destructive operations.

NEVER:
- delete large parts of code
- rewrite architecture
- introduce breaking changes

## Git Discipline
Before major changes:
- assume a commit exists
- avoid large diffs
- keep changes atomic

## Output Format
Before coding:
1. Explain the plan.
2. Show the structure of changes.
3. List assumptions.
4. Then implement.

## Error Handling
- Never fail silently.
- Always log meaningful errors.
- Do not crash the UI.

## Anti-Patterns (Forbidden)
- Direct API calls from UI
- SQL inside UI layer
- Mixing WooCommerce and WordPress auth
- Re-downloading images every run
- Creating duplicate products/categories
- Refactoring the entire project without request

## Behavior
- Be conservative.
- Prefer minimal change over ideal rewrite.
- Stay within phase scope.