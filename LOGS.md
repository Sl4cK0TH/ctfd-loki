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
