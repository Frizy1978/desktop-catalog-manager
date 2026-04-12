# AGENTS.md

## Project
Fish Olha Desktop Catalog Manager v1

## Source of truth
Always follow:
- `fisholha_desktop_catalog_manager_tz_for_codex.md`
- `desktop_catalog_manager_phase1_foundation_for_codex.md`
- later phase briefs if present

## Current priority
Build the project correctly from scratch in phases.

Current default focus:
**Phase 1 / foundation**, unless explicitly told to move to the next phase.

---

## Product mission
This project is a **desktop Windows catalog and media management application** for fisholha.ru.

It is:
- a local desktop application
- not a WordPress plugin
- not a web admin panel
- not a Telegram project
- not a buyer app
- not an order management system in this MVP

The app must become the internal working cabinet for:
- categories
- products
- prices
- descriptions
- images
- bulk edits
- draft → publish workflow
- sync with WooCommerce

---

## Core architecture rules

### 1. Product type
This must remain a **desktop application** built with Python + PySide6.
Do not drift into web-first architecture.

### 2. WooCommerce role
WooCommerce is:
- the current storefront
- the initial import source
- the publication target

Catalog editing should happen inside this desktop app, not primarily in WooCommerce admin.

### 3. Local database
The application must have its own local database.
For MVP this should be:
- SQLite

### 4. Draft → publish
This workflow is required.
Do not design the app as immediate live-edit only.

### 5. Scope discipline
Do not add in this MVP:
- Telegram
- buyer flows
- orders
- Google Sheets
- Yandex Maps full integration
- online payments
- CRM
- warehouse logic
- cloud multi-user collaboration

### 6. Auth
Use local application authentication.
Do not implement WooCommerce SSO for MVP.

### 7. AI image enhancement
Architecture should be ready for AI image processing later, with provider abstraction.
Do not hardcode the whole app around one provider.

---

## UI rules
The app is internal and admin-focused.

UI should be:
- modern
- minimal
- practical
- desktop-friendly
- easy for a non-technical owner

Use:
- clean layout
- readable typography
- light neutral palette
- one accent color
- soft shadows
- strong table usability
- clear loading / empty / error states

Avoid:
- flashy experimental design
- excessive motion
- neon palettes
- decorative clutter
- overcomplicated workflows

---

## Main window rules
This is a **single main window** app.

The main layout should contain:
1. left categories panel
2. top-right toolbar
3. bottom-right products table

Dialogs / side panels / popup editors are allowed for:
- category editing
- product editing
- photo management
- settings
- logs

---

## Engineering rules
- Use Python 3.12+
- Use PySide6
- Use SQLite for MVP
- Use clean modular architecture
- Prefer incremental safe progress
- Avoid giant one-shot implementation
- Keep docs updated
- Keep assumptions explicit

---

## Before coding
Always start by:
1. summarizing the current phase
2. listing assumptions
3. identifying touched files/modules
4. only then implementing

## After coding
Always provide:
1. changed files
2. what was implemented
3. open issues / assumptions
4. what the next logical phase is
