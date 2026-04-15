# Phase Scope Review - 2026-04-14

## Current confirmed state

Approved acceptance baseline:
- cross-phase success criteria are defined in `docs/phase_bdd_success_criteria.md`
- this file remains the source for current phase boundary, safe continuation, and manual verification

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

`Phase 6 - Bulk editing` is complete on the current branch.

Next active phase for planning and implementation is `Phase 7`.

Phase 5 work completed in the current branch:
- pending changes preview dialog
- explicit checkbox-based publish selection for categories and products
- select-all behavior for both entity groups
- future publish-target placeholder with only WooCommerce active
- publish selection passed through existing publish job / sync-run architecture
- product image changes now mark the product as `modified_local`
- left/right workspace resize affordance improved with a visible splitter handle
- publish selection counter now updates correctly when row checkboxes are toggled

Phase 5 stabilization completed:
- selected product publish now auto-includes required unpublished categories
- selected category publish now auto-includes required unpublished parent categories
- publish dependency handling is covered by automated tests

Allowed continuation from this point:
- Phase 7 planning and implementation
- documentation updates

Phase 6 first implemented scope:
- checkbox-based selection in the products table
- full selection of the current filtered product set for bulk actions
- compact two-row toolbar layout for desktop screens
- toolbar entry point for mass actions
- mass update of `price_unit` for selected products
- mass update of price for selected products
- mass replacement of category for selected products
- mass update of `published_state` for selected products
- mass update of `visibility` for selected products
- mass update of `is_featured` for selected products
- mass update of `stock_status` for selected products
- mass archive of selected products
- product editor fields for WooCommerce-facing product state:
  - `published_state`
  - `visibility`
  - `is_featured`
  - `stock_status`
- table filters for bulk workflow:
  - text search
  - category filter from the left panel
  - `sync_status` filter in toolbar
  - `published_state` filter in toolbar
  - `visibility` filter in toolbar
  - `is_featured` filter in toolbar
  - `stock_status` filter in toolbar
- compact product-table state columns for fast bulk verification:
  - `visibility`
  - `is_featured`
  - `stock_status`
- automated tests for repository/service bulk operations

How to verify the completed Phase 6 manually:
1. Open the app and load the catalog so the products table is filled.
2. Mark several products in the checkbox column.
3. Click `Массово`.
4. Choose `Изменить цену`, enter a new value, confirm, and verify the selected rows show the new price and local-change sync status.
5. Choose `Заменить категорию`, select a category, confirm, and verify the selected rows moved to the chosen category.
6. Choose `Изменить единицу измерения цены`, enter a value, confirm, and verify the selected rows show the updated unit.
7. Choose `Архивировать выбранные товары`, confirm, and verify the selected rows disappear from the active table.

8. Choose `Изменить статус публикации`, apply a new value, and verify the selected rows switch to the chosen local publish state.
9. Choose `Изменить видимость в каталоге`, apply a new value, and verify the selected rows keep the new visibility for future WooCommerce publish.
10. Choose `Изменить признак рекомендуемого товара`, apply the new value, and verify the selected rows were updated together.

11. Use the toolbar filters for `sync_status` and `published_state`, and verify the products table narrows down to the expected subset before mass actions.
12. Click `Отметить по фильтру` and verify the bulk-selection counter includes the full current filtered result set, not only the visible page.
13. Apply the filters `Видимость в каталоге` and `Рекомендуемый товар`, and verify the products table narrows down to the expected subset.
14. Open the product create/edit dialog and verify the fields `Статус публикации`, `Видимость в каталоге`, `Рекомендуемый товар`, and `Наличие` can be changed and saved locally.
15. Publish a product with changed `Статус публикации`, `Видимость в каталоге`, `Рекомендуемый товар`, or `Наличие`, and verify these values are sent to WooCommerce.
16. Apply the `Наличие` filter and verify the products table narrows down to the expected subset.
17. Verify the toolbar is split into two rows, fits within the app window width, and keeps secondary commands inside `Ещё`.

Additional manual check for the latest Phase 6 slice:
- open `Массово`, choose `Изменить наличие`, apply a value, and verify only the selected products receive the new local `stock_status`
- after bulk-editing state fields, verify the products table immediately reflects `Видимость`, `Рек.`, and `Наличие` without opening the product dialog

Additional manual check with current UI labels:
- after bulk-editing state fields, verify the products table immediately reflects `Видимость`, `Рекомендуемый`, and `Наличие` without opening the product dialog

Phase 6 closure decision:
- approved BDD criteria for Phase 6 are satisfied
- deferred inline editing, column management, and spreadsheet-like workflow are not required for Phase 6 acceptance
- the branch is ready to move to `Phase 7`

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
  - `.\.venv\Scripts\python.exe -m pytest -q` -> `11 passed`

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
