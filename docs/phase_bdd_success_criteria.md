# Phase BDD Success Criteria

## Purpose

This document defines the approved Behavior-Driven Development success criteria for the phased delivery of Fish Olha Desktop Catalog Manager.

These criteria are the acceptance baseline for deciding whether a phase is complete, still in progress, or blocked by missing behavior.

## Source alignment

This document is based on:
- `fisholha_desktop_catalog_manager_tz_for_codex.md`
- `desktop_catalog_manager_phase1_foundation_for_codex.md`
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `docs/phase_scope_review_2026-04-14.md`

## Global rules

- The product must remain a desktop Windows application built with Python, PySide6, and SQLite for MVP.
- The app must preserve the layered architecture `UI -> service -> repository -> DB/integration`.
- UI must not call SQL directly.
- UI must not call WooCommerce or WordPress APIs directly.
- WooCommerce categories/products must use `/wc/v3` with Consumer Key / Consumer Secret.
- WordPress media uploads must use `/wp/v2/media` with WordPress username + Application Password.
- These two authentication flows must never be merged.
- External entity mapping must rely on `external_wc_id`, not on name matching.
- Deferred scope must stay outside phase success criteria until explicitly approved.

## Phase 1 - Foundation

- `Given` the project is opened on the target local machine, `When` the application is launched, `Then` the desktop app starts, prepares local folders/config, initializes SQLite foundation, and shows the login screen.
- `Given` the user enters valid local credentials, `When` authentication succeeds, `Then` the main window opens in a single-window layout.
- `Given` the main window is open, `When` the user views the workspace, `Then` the app shows three core regions: categories panel on the left, toolbar on the top-right, and products table area on the bottom-right.
- `Given` Phase 1 is evaluated for completion, `When` acceptance is checked, `Then` project scaffold, app shell, login screen, main window skeleton, SQLite foundation, settings foundation, and core docs must exist.

## Phase 2 - Data layer and import

- `Given` WooCommerce connection settings are configured, `When` the user starts import, `Then` categories, products, category links, and image source URLs are imported into the local database.
- `Given` an imported category or product already exists locally with the same external WooCommerce identifier, `When` import runs again, `Then` the local record is updated instead of duplicated.
- `Given` import finishes, `When` the result is reviewed, `Then` the application records the sync run outcome, counters, and errors in a predictable way.
- `Given` imported data exists locally, `When` the catalog screen is refreshed, `Then` the user can see imported categories and products in the desktop UI.

## Phase 3 - CRUD

- `Given` the user wants to create or edit a category, `When` the category form is saved with valid data, `Then` the category is stored locally and becomes available in the category panel.
- `Given` the user wants to create or edit a product, `When` the product form is saved with valid data, `Then` the product is stored locally and becomes available in the products table.
- `Given` an existing synced category or product is changed locally, `When` the save operation succeeds, `Then` the entity reflects a local modified state rather than silently pretending it is already synced.
- `Given` invalid local input is entered, `When` the user tries to save, `Then` the UI shows a meaningful validation error without crashing.

## Phase 4 - Photos

- `Given` a product has one or more local images, `When` the user opens product image management, `Then` the app shows the linked images and their order.
- `Given` the user adds a local image to a product, `When` the operation succeeds, `Then` the image is stored locally and linked to that product without losing existing images.
- `Given` the user marks one image as primary, `When` the change is saved, `Then` the product has one clear primary image state.
- `Given` local image work is performed, `When` the product is returned to later, `Then` the image selection and primary state persist locally.

## Phase 4.5 - WordPress media upload

- `Given` the product or category has a local image selected for publication, `When` media upload is triggered, `Then` the file is uploaded through `/wp-json/wp/v2/media`.
- `Given` media upload to WordPress is executed, `When` authentication is used, `Then` it uses WordPress username and Application Password rather than WooCommerce Consumer Key / Secret.
- `Given` WooCommerce product/category publish also exists in the app, `When` both flows are used in the same system, `Then` WordPress media auth and WooCommerce catalog auth remain separated.

## Phase 5 - Draft / publish

- `Given` local changes exist for categories or products, `When` the user opens the pending changes view, `Then` the app shows what is ready for publication and allows explicit selection.
- `Given` the user selects categories and products for publish, `When` publication starts, `Then` the process runs through the publish job and sync-run architecture rather than direct uncontrolled writes from UI.
- `Given` a selected product depends on unpublished categories, `When` scoped publish is executed, `Then` the required category dependencies are safely included.
- `Given` a selected category depends on unpublished parent categories, `When` scoped publish is executed, `Then` the missing parent categories are safely included first.
- `Given` publication succeeds or fails, `When` the run completes, `Then` sync status and operation result are visible and understandable to the user.

## Phase 6 - Bulk editing

- `Given` the products table is filled, `When` the user selects multiple products with checkboxes, `Then` the app supports safe multi-selection for bulk operations.
- `Given` several products are selected, `When` the user opens bulk actions, `Then` mass actions are applied only to the selected products.
- `Given` the user runs supported bulk operations, `When` the action is confirmed, `Then` the app can safely mass-update price, `price_unit`, category, `published_state`, `visibility`, `is_featured`, `stock_status`, and archive state for selected products.
- `Given` the user opens single-product editing, `When` the form is saved, `Then` WooCommerce-facing product state fields such as `published_state`, `visibility`, `is_featured`, and `stock_status` are stored locally and later available for publish.
- `Given` a bulk edit changes a synced product locally, `When` the action succeeds, `Then` sync status becomes `modified_local` unless the product is already `new_local`.
- `Given` non-selected products exist in the same table, `When` a bulk action is executed, `Then` those non-selected products remain unchanged.
- `Given` Phase 6 is evaluated for completion, `When` acceptance is checked, `Then` bulk actions, batch-safe edit behavior, practical filtering support, and local editing of WooCommerce-facing product state fields must exist, but deferred table redesign and SEO work must not be required for acceptance.
- Current assessment on `2026-04-15`: Phase 6 criteria are satisfied on the current branch.

## Phase 7 - AI image foundation

- `Given` AI image processing is planned for a later step, `When` the architecture is evaluated, `Then` provider abstraction must exist instead of a hard dependency on one vendor.
- `Given` image processing tasks and results will be added later, `When` the phase is implemented, `Then` the system must have a task-oriented model for processing state and result storage.
- `Given` MVP scope is checked, `When` Phase 7 acceptance is reviewed, `Then` architectural readiness is required, but full production AI integration is not required unless explicitly approved.

## Deferred scope notes

- SEO implementation is deferred to later phases.
- Real Yandex integration is deferred; only architectural placeholders are allowed in MVP phases where already approved.
- Buyer flows, orders, Telegram, CRM, Google Sheets, and warehouse logic remain out of MVP scope.
- Advanced spreadsheet-like table redesign is not part of current approved Phase 6 acceptance unless separately approved.

## Usage rules

- Before coding, compare the requested task with the current phase criteria in this document.
- If the requested behavior is outside the current phase acceptance boundary, do not silently include it.
- If a criterion is only partially satisfied, treat the phase as still in progress.
- When phase status changes, update both this document and the current phase review file if the acceptance baseline changed.
