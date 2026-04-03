# CTFd LOKI — Development Log

All timestamps are in UTC+8 (Asia/Manila).

---

## 2026-03-14

### 00:41 — Phase 1 Execution Started
- Implementation plan approved by user
- Beginning scaffold: `LOGS.md`, `LICENSE`, `requirements.txt`
- Foundation files: `models.py`, `config.py`
- Backend abstraction: `backends/`

### 00:45 — Core Python Files Created
- `models.py` — `LokiChallenge` (extends Challenges, polymorphic identity `"loki"`), `LokiContainer` (instance tracking with UUID, dynamic flag generation, expiry)
- `config.py` — Default config values with `loki:` prefix, `setup_default_configs()`, `get_loki_config()` helper
- `backends/__init__.py` — Backend factory (`get_backend()`)
- `backends/base.py` — Abstract `BackendBase` class
- `backends/docker_backend.py` — Plain Docker implementation (lazy client init, resource limits, port mapping, DNS, network attach)
- `decorators.py` — `@challenge_visible`, `@frequency_limited` (session-based, no Redis)

### 00:50 — Challenge Type + API Created
- `challenge_type.py` — `LokiChallengeType(BaseChallenge)` with full CRUD, static + dynamic flag checking, thorough `delete()` cleanup
- `api.py` — Flask-RESTX namespaces: user (GET/POST/PATCH/DELETE for container lifecycle), admin (list/renew/destroy). Supports user/team scoping, global container limits, renewal limits
- `__init__.py` — Plugin entry point: DB init, config setup, asset + menu registration, API namespace mounting, APScheduler auto-cleanup with file lock

### 00:55 — Frontend Assets Created
- `assets/create.html` + `create.js` — Admin challenge creation form
- `assets/update.html` + `update.js` — Admin challenge update form
- `assets/view.html` + `view.js` — Player view: Start/Stop/Renew, countdown timer, connection info, copy-to-clipboard
- `templates/loki_base.html` — Admin base with tab navigation
- `templates/loki_settings.html` — Admin settings page (Docker, scoping, flags, backend)
- `templates/loki_containers.html` — Admin container management dashboard

### 01:00 — Documentation Created
- `README.md` — Comprehensive docs: features, architecture, installation, config, usage, API reference, DB schema, image prep, roadmap, security
- `LICENSE` — MIT
- `requirements.txt` — `docker>=6.0.0`, `Flask-APScheduler>=1.13.0`

### 01:00 — Phase 1 Verification
- Checking all files created and importable
- Verifying CTFd compatibility

---

## 2026-04-03

### 22:10 — Workspace Analysis + Architecture Decisions
- Reviewed `ctfd-loki` and compared with `ctfd-whale` to identify parity gaps and regressions
- Confirmed plugin structure and runtime flow are present (spawn, status, renew, stop, auto-clean)
- Captured user decisions for next iteration:
	- Team mode: teammates share one instance and one dynamic flag
	- Start behavior: block when an instance exists; require explicit stop before spawn
	- Priority: fix correctness bugs first, then hardening

### 22:20 — Correctness Fixes (API + Challenge Type)
- Updated `api.py`:
	- Added `_resolve_admin_container()` for stable admin action targeting
	- Admin `PATCH/DELETE /admin/container` now accepts `container_id` (preferred), with `user_id` fallback
	- Changed user `POST /container` behavior to block when an instance already exists instead of auto-destroying
- Updated `challenge_type.py`:
	- Fixed team-scope dynamic flag validation to resolve container by `team_id` when `container_scope=team`
	- Added robust boolean normalization for `dynamic_score` (`_to_int_bool`) to avoid checkbox casting issues

### 22:30 — Runtime Security Hardening
- Updated `config.py` defaults with runtime hardening settings:
	- `docker_security_read_only_rootfs`
	- `docker_security_drop_all_caps`
	- `docker_security_no_new_privileges`
	- `docker_security_pids_limit`
	- `docker_security_tmpfs_size`
- Updated `backends/docker_backend.py`:
	- Added boolean parser helper for config values
	- Applied security options in `containers.run(...)`:
		- optional read-only rootfs
		- cap drop all
		- no-new-privileges
		- PID limit
		- hardened writable tmpfs for `/tmp`

### 22:38 — Admin UI Updates
- Updated `templates/loki_containers.html`:
	- Switched row/action identity from `user_id` to container DB `id`
	- Admin renew/destroy actions now call API with `container_id`
- Updated `templates/loki_settings.html`:
	- Added Runtime Security section exposing the new hardening configs

### 22:42 — Verification Plan
- Planned validation after edits:
	- compile plugin modules (`python -m compileall plugins/ctfd-loki`)
	- check diagnostics for modified files
	- re-run quick endpoint sanity review for start/stop/admin paths

### 23:05 — Latest CTFd Compatibility Audit
- Performed source-level compatibility check against this workspace's CTFd core implementation.
- Verified plugin registration/API hooks are conceptually compatible:
	- `CTFd_API_v1` import path (`CTFd.api`) is valid for this codebase
	- challenge type registration via `CHALLENGE_CLASSES` is valid
	- plugin asset/menu registration APIs are valid
- Identified critical frontend contract gaps preventing "works perfectly" status on latest CTFd UI flow:
	- `assets/view.html` does not extend `challenge.html` and bypasses the expected challenge modal contract.
	- `assets/view.js` does not use `CTFd._internal.challenge.preRender/postRender/submit` hooks.
	- `assets/view.js` uses `init.csrfNonce`; current core uses `CTFd.config.csrfNonce` (or `CTFd.fetch` wrapper).
	- `assets/view.html` defines custom submission form/input (`name=answer`) instead of using expected submission flow (`name=submission` + core submit pipeline).
- Identified medium-risk admin UX contract gaps:
	- `assets/create.js` and `assets/update.js` rely on `DOMContentLoaded`; admin challenge scripts are loaded dynamically after page load, so these handlers may not fire.
- Conclusion: backend/API/model layer is close; frontend challenge/admin scripts need contract-aligned refactor for full compatibility with latest CTFd.

### 23:30 — Frontend Contract Refactor Implemented
- Updated `assets/view.html` to extend `challenge.html` and inject Loki instance controls in the description block.
- Removed custom/standalone flag submission form from Loki view template to rely on core challenge submission UI.
- Rewrote `assets/view.js` to use CTFd challenge lifecycle contract:
	- `CTFd._internal.challenge.preRender`
	- `CTFd._internal.challenge.postRender`
	- `CTFd._internal.challenge.submit`
	- `CTFd._internal.challenge.boot/destroy/renew`
- Switched away from legacy `init.csrfNonce` usage and used `CTFd.fetch`/CTFd API wrappers used by core frontend.
- Updated `assets/create.js` and `assets/update.js` to avoid `DOMContentLoaded` dependency and bind immediately when scripts are loaded dynamically in admin challenge pages.

### 23:36 — Validation
- Ran `python -m compileall plugins/ctfd-loki` after refactor.
- Checked diagnostics for modified frontend assets; no tool-reported errors.
- Verified expected compatibility markers exist in source:
	- view template extends `challenge.html`
	- view script defines `postRender` and `submit` lifecycle hooks

### 23:50 — Repo Hygiene + Documentation Stabilization
- Added plugin-level `.gitignore` to ignore Python bytecode and common local artifacts.
- Updated `README.md` to reflect current behavior and interfaces:
	- explicit block-on-existing instance behavior for start endpoint
	- runtime hardening settings now exposed in configuration table
	- admin container actions documented with `container_id` as preferred lookup
	- compatibility notes for latest CTFd challenge frontend contract
- Prepared cleanup of tracked bytecode artifacts from git index.
