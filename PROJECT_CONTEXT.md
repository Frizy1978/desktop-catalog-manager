# PROJECT_CONTEXT.md

## Project
Fish Olha Desktop Catalog Manager v1

## Current progress

Completed:
- Phase 1 foundation
- Phase 2 SQLite models + WooCommerce import
- Phase 3 catalog editing UI
- Phase 4 local image management
- Phase 4.5 media upload to WordPress works via:
  - `wp/v2/media`
  - Basic Auth
  - WordPress username
  - WordPress Application Password
- Phase 5 draft/publish stabilization completed:
  - pending changes preview
  - scoped publish selection for categories/products
  - select-all behavior in publish dialog
  - future publish-target placeholder with only WooCommerce active
  - image-only product changes correctly mark product as `modified_local`
  - visible splitter handle for left/right panel resize
  - publish selection counter updates correctly when row checkboxes change
  - selected product publish auto-includes required unpublished categories
  - selected category publish auto-includes required unpublished parent categories

Important technical decision:
- keep WooCommerce Consumer Key / Secret for `wc/v3` category/product operations
- keep separate WordPress Application Password auth for `wp/v2/media` uploads
- do not merge these auth flows

Next goal:
- move to Phase 6 bulk editing
- SEO work is deferred to a later phase
- active SEO plugin confirmed: `Yoast SEO`

## Current state

The product is:
- a desktop Windows application
- focused on catalog and photo management
- not a Telegram or mini app product
- not an order collection system

## Current MVP focus

The current MVP is focused on:
- local desktop admin application
- catalog import from WooCommerce
- local storage of categories/products/images
- category/product editing
- bulk editing
- image handling
- draft -> publish workflow
- publication back to WooCommerce
- operation log
- local authentication

## Development environment

Development is done locally on a Windows laptop.

Ubuntu VM is not part of the current development workflow.

## Chosen technology direction

Preferred direction:
- Python
- PySide6
- SQLite
- WooCommerce REST API
- local file storage for media

## Accepted product decisions

1. Separate desktop application
2. Main business focus in MVP: catalog and photo management
3. Required workflow: draft -> publish
4. WooCommerce remains storefront and import/publication target
5. Local login/password instead of WooCommerce SSO
6. Yandex channel is deferred; only architectural placeholder may exist
7. SEO plugin on the live site is `Yoast SEO`, but SEO implementation is postponed to a later phase

## Current phase

**Ready for Phase 6 - Bulk editing**

## What Phase 5 completion means

- pending changes screen exists
- categories/products can be published selectively
- publish selection is checkbox-based
- media upload remains split from WooCommerce catalog publish
- publication still runs through the publish job / sync-run architecture
- left category panel and right workspace can be resized more clearly by the user
- publish selection safely resolves unpublished category dependencies before publish

## What is explicitly out of scope right now

- AI image integration
- real Yandex channel integration
- full bulk editing logic / advanced table workflow
- SEO import/export implementation
- buyer-facing UI
- Telegram
- orders

## Immediate goal for Codex

Codex should first:
1. read source-of-truth files
2. summarize the current phase and assumptions
3. continue from the existing implementation, not from scratch
4. keep phase discipline
5. update docs when phase state changes
6. implement only the approved next scoped task

## Test environment status

- local project venv is working again
- verified manually:
  - `.\.venv\Scripts\python.exe --version` -> `Python 3.12.3`
  - `.\.venv\Scripts\python.exe -m pytest -q` -> `5 passed`
- if Codex tool session cannot see the refreshed Python installation, restart the Codex session before relying on automated checks
