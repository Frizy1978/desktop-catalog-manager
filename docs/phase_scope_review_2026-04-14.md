# Phase Scope Review - 2026-04-14

## Current confirmed state

Completed:
- Phase 1 foundation
- Phase 2 SQLite models + WooCommerce import
- Phase 3 catalog editing UI
- Phase 4 local image management
- Phase 4.5 WordPress media upload
- Phase 5 safe UI/workflow baseline

Confirmed integration split:
- WordPress media upload:
  - endpoint: `/wp-json/wp/v2/media`
  - auth: WordPress username + Application Password
- WooCommerce categories/products:
  - endpoint: `/wp-json/wc/v3`
  - auth: Consumer Key + Consumer Secret
- these auth methods must remain separate

## Current phase

Phase 5 draft/publish stabilization is complete.

Project is ready to move to `Phase 6 - Bulk editing`.

Phase 5 work completed in the current branch:
- pending changes preview dialog
- explicit checkbox-based publish selection for categories and products
- select-all behavior for both entity groups
- future publish-target placeholder with only WooCommerce active
- publish selection passed through existing publish job / sync-run architecture
- product image changes now mark the product as `modified_local`
- left/right workspace resize affordance improved with a visible splitter handle
- publish selection counter now updates correctly when row checkboxes are toggled

Latest stabilization completed:
- selected product publish now auto-includes required unpublished categories
- selected category publish now auto-includes required unpublished parent categories
- publish dependency handling is covered by automated tests

Allowed continuation from this point:
- Phase 6 planning and implementation
- documentation updates

Forbidden or out-of-phase work for the next step:
- real Yandex integration
- full bulk editing feature set
- advanced configurable product-table workspace redesign
- SEO implementation

## User-validated scope split

### Safe within Phase 5
- publish preview / selection behavior
- publish target placeholder only
- small UI fixes around draft/publish
- resize clarity for the main workspace split

### Deferred to a later phase
- inline editing in the products table
- column visibility menu
- product main image column
- row-level edit action button
- SEO fields implementation and mapping

## Confirmed after clarification

- active SEO plugin: `Yoast SEO`
- SEO work is deferred to later phases
- the local Python test environment is now working again
- verified manually:
  - `.\.venv\Scripts\python.exe --version` -> `Python 3.12.3`
  - `.\.venv\Scripts\python.exe -m pytest -q` -> `7 passed`

## Recommended first prompt for a new Codex session

Use `project-guardian` strictly.

Read and use:
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `fisholha_desktop_catalog_manager_tz_for_codex.md`
- `docs/phase_scope_review_2026-04-14.md`

Current state:
- Phase 1 completed
- Phase 2 completed
- Phase 3 completed
- Phase 4 completed
- Phase 4.5 completed and tested
- Phase 5 safe UI/workflow baseline completed

Important confirmed result:
- WordPress media upload works via `/wp-json/wp/v2/media`
- auth method for media is:
  - WordPress username
  - WordPress Application Password
- WooCommerce category/product operations must still use `wc/v3` with Consumer Key / Consumer Secret
- do not merge these auth methods

Additional confirmed context:
- active SEO plugin: `Yoast SEO`
- SEO implementation is deferred to later phases
- local test environment is working:
  - `.\.venv\Scripts\python.exe --version` -> `Python 3.12.3`
  - `.\.venv\Scripts\python.exe -m pytest -q` -> `5 passed`

Before coding:
1. summarize current architecture and completed phases
2. summarize the confirmed media auth decision
3. state the exact next-phase plan
4. list assumptions
5. list touched files/modules
6. then implement only the approved next scope
