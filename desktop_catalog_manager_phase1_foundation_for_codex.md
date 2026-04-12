# Codex Execution Plan — Phase 1 Foundation for Fish Olha Desktop Catalog Manager

Use:
- `fisholha_desktop_catalog_manager_tz_for_codex.md`
- `PROJECT_CONTEXT.md`
- `AGENTS.md`

as source of truth.

This document defines only **Phase 1 / foundation**.

---

# Goal of this phase

Create the **correct foundation** of the desktop application, not the full product.

Phase 1 should deliver:
- Python project scaffold
- PySide6 application shell
- local config foundation
- SQLite foundation
- login screen
- single main window skeleton
- categories panel scaffold
- toolbar scaffold
- products table scaffold
- docs
- environment/config examples

---

# What needs to be implemented

## 1. Create project structure
Suggested structure:

```text
root/
  app/
    ui/
    widgets/
    dialogs/
    models/
    services/
    repositories/
    core/
    resources/
  docs/
  tests/
  main.py
  requirements.txt or pyproject.toml
  README.md
```

Codex may propose a better structure, but it must remain simple and desktop-oriented.

## 2. Create PySide6 app shell
Need:
- app entrypoint
- QApplication bootstrap
- login window/dialog
- main window
- base styling/theme foundation

## 3. Create single main window skeleton
Main window should already contain placeholder regions for:
- left categories panel
- top-right toolbar
- bottom-right products table

No full business logic yet.

## 4. Create login screen
Need:
- username field
- password field
- login button
- placeholder local auth flow foundation

No need for advanced auth yet.

## 5. Create SQLite foundation
Need:
- DB initialization
- schema/model foundation
- connection bootstrap

At this stage, enough to prepare:
- User
- Role
- Category
- Product
- ProductImage
- ProductImageVersion
- SyncRun
- PublishJob

## 6. Create module skeletons
Suggested modules:
- auth
- categories
- products
- media
- sync
- publish
- settings
- logs

## 7. Create placeholder screens / dialogs
Need placeholders for:
- category editor dialog
- product editor dialog
- settings dialog
- operation log view

## 8. Create docs and config foundation
Need:
- README.md
- AGENTS.md
- PROJECT_CONTEXT.md
- docs/architecture.md
- config example file or settings docs

---

# What should NOT be implemented in this phase

Do not implement yet:
- full WooCommerce client
- import logic
- publish logic
- AI image processing
- Yandex integration
- full bulk editing
- final CRUD behavior
- packaging to exe

---

# What Codex should output before coding

Before implementation, Codex must:
1. summarize intended architecture
2. show project structure
3. show DB entities
4. show window layout plan
5. list assumptions
6. show phased implementation plan

Only then proceed to code.

---

# Acceptance criteria

Phase 1 is successful if:
1. project scaffold exists
2. app launches locally
3. login screen exists
4. main window exists
5. left categories area exists
6. toolbar area exists
7. products table area exists
8. SQLite foundation exists
9. docs exist
10. architecture is ready for Phase 2
