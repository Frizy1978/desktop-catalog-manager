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
- Phase 6 bulk editing completed:
  - checkbox-based multi-selection in the products table
  - selection of the full filtered result set for bulk actions
  - bulk actions for `price_unit`, `price`, `category`, `published_state`, `visibility`, `is_featured`, `stock_status`, and archive
  - practical table filtering for bulk workflow
  - local editing of WooCommerce-facing product state fields
  - compact state visibility directly in the products table

Important technical decision:
- keep WooCommerce Consumer Key / Secret for `wc/v3` category/product operations
- keep separate WordPress Application Password auth for `wp/v2/media` uploads
- do not merge these auth flows

Approved success criteria:
- phase acceptance now follows `docs/phase_bdd_success_criteria.md`
- phase review and implementation decisions should be checked against the approved BDD criteria before coding

Next goal:
- move to Phase 7 architecture foundation for deferred AI-ready provider abstraction
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

**Phase 6 - Bulk editing completed**

## What current phase means

- pending changes screen exists
- categories/products can be published selectively
- publish selection is checkbox-based
- media upload remains split from WooCommerce catalog publish
- publication still runs through the publish job / sync-run architecture
- left category panel and right workspace can be resized more clearly by the user
- publish selection safely resolves unpublished category dependencies before publish
- toolbar uses a compact two-row desktop layout:
  - primary commands on the first row
  - search and filters on the second row
  - secondary commands moved to overflow
- product table supports checkbox-based mass selection for bulk operations
- current filtered result set can be selected for bulk operations in one action
- first bulk actions are available for selected products:
  - mass change of `price_unit`
  - mass change of price
  - mass replacement of category
  - mass change of `published_state`
  - mass change of `visibility`
  - mass change of `is_featured`
  - mass change of `stock_status`
  - mass archive
- product editor now supports:
  - `published_state`
  - `visibility`
  - `is_featured`
  - `stock_status`
- practical table filtering for bulk workflow is now supported through:
  - text search
  - category selection
  - `sync_status` filter
  - `published_state` filter
  - `visibility` filter
  - `is_featured` filter
  - `stock_status` filter
- products table now also shows compact WooCommerce-facing state columns:
  - `visibility`
  - `is_featured`
  - `stock_status`

Phase 6 acceptance status:
- approved BDD criteria for `Phase 6` are satisfied on the current branch
- deferred spreadsheet-like workflow and advanced table redesign remain out of scope and do not block phase completion

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

## Phase acceptance reference

- Use `docs/phase_bdd_success_criteria.md` as the agreed acceptance baseline for completed and in-progress phases
- Use `docs/phase_scope_review_2026-04-14.md` for current active scope and manual verification guidance

## Test environment status

- local project venv is working again
- verified manually:
  - `.\.venv\Scripts\python.exe --version` -> `Python 3.12.3`
  - `.\.venv\Scripts\python.exe -m pytest -q` -> `11 passed`
- if Codex tool session cannot see the refreshed Python installation, restart the Codex session before relying on automated checks
