# PROJECT_CONTEXT.md

## Project
Fish Olha Desktop Catalog Manager v1

## Current state
This is a fresh project start with a revised concept.

The product is now:
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
- draft → publish workflow
- publication back to WooCommerce
- operation log
- local authentication

## Development environment
Development will be done locally on a Windows laptop.

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
3. Required workflow: draft → publish
4. WooCommerce remains storefront and import/publication target
5. Local login/password instead of WooCommerce SSO
6. Yandex channel is deferred; only architectural placeholder may exist

## Current phase
**Phase 1 — foundation**

## What Phase 1 means
- Python project scaffold
- PySide6 app shell
- login screen
- single main window skeleton
- categories panel scaffold
- products table scaffold
- toolbar scaffold
- SQLite foundation
- config/docs foundation

## What is explicitly out of scope right now
- full WooCommerce sync
- final publish workflow
- AI image integration
- Yandex channel integration
- full bulk editing logic
- buyer-facing UI
- Telegram
- orders

## Immediate goal for Codex
Codex should first:
1. read source-of-truth files
2. propose project structure
3. propose DB entities and modules
4. propose single-window layout
5. state assumptions
6. then implement foundation only
