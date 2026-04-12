# Fish Olha Desktop Catalog Manager v1

Desktop Windows catalog and media management application for fisholha.ru.

This repository currently contains **Phase 1 (foundation)**:
- project scaffold
- PySide6 shell
- local SQLite bootstrap
- local login screen
- single main window skeleton
- categories panel + toolbar + products table scaffolds
- placeholder dialogs and module packages for next phases
- Phase 2 foundation: SQLAlchemy models/repositories and initial WooCommerce import pipeline

## Tech Stack
- Python 3.12+
- PySide6
- QtAwesome (third-party icon set)
- SQLite (stdlib `sqlite3`)

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies:
```bash
pip install -e .
```
If you updated from an earlier scaffold, reinstall dependencies to get icon library updates:
```bash
pip install -e . --upgrade
```
3. Optional: create a local `.env` from `.env.example`.
4. Run:
```bash
python main.py
```

## Default Local Login
- Username: value of `FISHOLHA_DEFAULT_ADMIN_USERNAME` (default `admin`)
- Password: value of `FISHOLHA_DEFAULT_ADMIN_PASSWORD` (default `admin123`)

The first local user is created automatically on first run if the user table is empty.

## Current Scope
Implemented:
- app shell and foundation architecture
- local auth foundation (password hash + login flow)
- SQLite schema foundation
- UI skeleton required by Phase 1
- SQLAlchemy data layer for catalog entities
- WooCommerce client and initial categories/products import
- sync run operation log foundation (`sync_runs`)
- settings dialog with:
  - WooCommerce credentials editing and saving to `.env`
  - admin login/password update
  - safe catalog clear with automatic DB backup
- login dialog supports:
  - show password
  - remember password on this device

Not implemented yet:
- full WooCommerce sync
- publish workflow
- AI provider integrations
- Yandex integration
- full bulk editing logic
- buyer flows, Telegram, orders

## WooCommerce Import Setup (.env)
Set these values to enable the `Импорт` action:
```ini
FISHOLHA_WC_BASE_URL=https://example.com
FISHOLHA_WC_CONSUMER_KEY=ck_xxx
FISHOLHA_WC_CONSUMER_SECRET=cs_xxx
FISHOLHA_WC_TIMEOUT_SECONDS=20
FISHOLHA_WC_VERIFY_SSL=true
```

## Project Layout
See `docs/architecture.md` for architecture and module boundaries.
