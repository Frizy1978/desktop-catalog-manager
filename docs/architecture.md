# Architecture (Phase 1 Foundation)

## Goals
Phase 1 establishes a clean desktop-first foundation for later phases:
- local-first data model (SQLite)
- local authentication
- single-window admin layout
- modular feature boundaries for sync/publish/media extensions

## Layered Structure
- `app/core`: shared core primitives (settings, paths, database, security)
- `app/models`: typed entities and enums
- `app/repositories`: persistence access layer
- `app/services`: application use-cases orchestration
- `app/ui`: PySide6 windows/widgets/dialogs
- `app/modules`: feature package placeholders for future implementation

## Runtime Flow
1. `main.py` calls `app.bootstrap.run()`.
2. Settings and local folders are prepared.
3. SQLite schema initialization runs.
4. Default local admin account is ensured.
5. Login dialog is shown.
6. On successful login, main window opens.

## Main Window Composition
- Left panel: categories scaffold
- Right top panel: command-bar style toolbar (primary actions + overflow menu "Ещё")
- Right bottom panel: products table scaffold

This enforces the single main window requirement while keeping dialogs for editing/settings/logs.

## Iconography
- UI actions use a third-party icon library (`qtawesome`) for a modern and consistent look.
- Application window icon is loaded from `Icons/logo_mn.png`.

## Database Foundation
Phase 1 initializes these tables:
- `roles`
- `users`
- `categories`
- `products`
- `product_categories`
- `product_images`
- `product_image_versions`
- `sync_runs`
- `publish_jobs`

## Phase 2 Data Layer
- SQLAlchemy 2.0 model layer added for:
  - `Category`
  - `Product`
  - `ProductImage`
  - `ProductCategoryLink`
  - `SyncRun`
- Repository layer handles upsert and read-model queries.
- WooCommerce import flow:
  1. import categories
  2. bind category parent links
  3. import products
  4. bind product-category links
  5. store image URLs as metadata (`product_images.original_path`)
  6. write sync run result in `sync_runs`

## Product Image Rules
- One product can have multiple image records.
- Exactly one image per product is marked as primary (`is_primary = true`).
- `original_path` stores source URL from WooCommerce.
- `local_path` is reserved for future local media files and is currently nullable.

## Scope Boundary
Phase 1 does not implement:
- full WooCommerce import/publish logic
- final draft/publish behavior
- AI image providers
- Yandex channel integration
- complete bulk editing workflows

## Windows Compatibility Note
- Current stack in repository (`Python 3.12+` + `PySide6/Qt6`) is suitable for modern Windows targets.
- For future runtime support on `Windows 7`, a dedicated compatibility profile will be required (older Python/Qt branch and separate build pipeline).
- Until that profile is introduced, avoid introducing platform-specific APIs that hard-lock behavior to Windows 10/11-only features.
