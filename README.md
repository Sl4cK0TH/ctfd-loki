# CTFd LOKI

> *"I know what kind of god I need to be — for you. For all of us."*
> — Loki, Season 2

A modern, general-purpose **dynamic container challenge plugin** for [CTFd](https://github.com/CTFd/CTFd).
Inspired by [CTFd-whale](https://github.com/frankli0324/ctfd-whale), rebuilt from scratch for compatibility, clarity, and extensibility.

**LOKI** provisions isolated Docker containers per player (or per team), giving every participant their own environment to hack — with unique credentials, automatic cleanup, and a full admin dashboard.

---

## Features

| Feature | Description |
|---|---|
| **Per-player containers** | Each player gets a dedicated Docker container when they click "Start Instance" |
| **Per-team mode** | Configurable — share one instance across team members |
| **Explicit lifecycle control** | Start is blocked when an instance exists; users must stop first |
| **Static + dynamic flags** | Admin-defined flags or auto-generated unique flags per instance |
| **Countdown timer** | Players see remaining time; containers are auto-cleaned when expired |
| **Renew / Stop** | Players manage their own instance lifecycle |
| **Resource limits** | Configurable memory and CPU caps per challenge |
| **Multi-protocol** | SSH, TCP/Netcat, HTTP — connection info adapts automatically |
| **Admin dashboard** | Settings page + live container management (list, renew, destroy) |
| **Admin menu integration** | "Loki" appears in CTFd's admin sidebar |
| **Auto-cleanup** | Background scheduler reaps expired containers every 30 seconds |
| **Rate limiting** | Session-based cooldown to prevent container spam |
| **Pluggable backends** | Docker (default) — Swarm planned for Phase 2 |
| **No Redis required** | Phase 1 uses session-based rate limiting |

---

## Architecture

```
plugins/ctfd-loki/
├── __init__.py              # Plugin entry point
├── models.py                # LokiChallenge + LokiContainer (SQLAlchemy)
├── challenge_type.py        # LokiChallengeType (BaseChallenge subclass)
├── config.py                # Default settings + first-run setup
├── api.py                   # Flask-RESTX API (user + admin namespaces)
├── decorators.py            # @challenge_visible, @frequency_limited
├── backends/
│   ├── __init__.py          # Backend factory
│   ├── base.py              # Abstract BackendBase
│   └── docker_backend.py    # Plain Docker implementation
├── assets/
│   ├── create.html / .js    # Admin: create challenge
│   ├── update.html / .js    # Admin: update challenge
│   ├── view.html / .js      # Player: challenge view
├── templates/
│   ├── loki_base.html       # Admin base with tab navigation
│   ├── loki_settings.html   # Admin: plugin settings
│   └── loki_containers.html # Admin: running containers
├── README.md
├── LICENSE                  # MIT
├── requirements.txt
└── LOGS.md                  # Development log
```

### Data Flow

```
Player clicks "Start"
    → POST /api/v1/plugins/ctfd-loki/container
        → api.py → UserContainers.post()
            → LokiContainer (DB record created)
            → DockerBackend.create_container()
                → docker.containers.run() → port assigned
            → Response with connection info

Player clicks "Stop"
    → DELETE /api/v1/plugins/ctfd-loki/container
        → DockerBackend.remove_container()
        → DB record deleted

Auto-cleanup (every 30s)
    → Check LokiContainer.is_expired
    → Remove expired containers from Docker + DB
```

---

## Installation

### Prerequisites

| Requirement | Details |
|---|---|
| CTFd | The version in this repository |
| Python | 3.10+ |
| Docker | Installed and accessible to the CTFd process |
| Docker Socket | `/var/run/docker.sock` or TCP endpoint |

### Steps

1. **Install Python dependencies:**
   ```bash
   pip install -r plugins/ctfd-loki/requirements.txt
   ```

2. **Copy the plugin into CTFd's plugins directory:**
   ```bash
   cp -r plugins/ctfd-loki /path/to/CTFd/CTFd/plugins/ctfd-loki
   ```

   Or create a symlink for development:
   ```bash
   ln -s /path/to/plugins/ctfd-loki /path/to/CTFd/CTFd/plugins/ctfd-loki
   ```

3. **Ensure Docker socket access.** If CTFd runs inside Docker:
   ```yaml
   # In CTFd's docker-compose.yml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock
   ```

4. **Start CTFd.** The plugin auto-creates database tables and default settings on first launch.

5. **Verify:**
   - Visit **Admin → Plugins → Loki** in the sidebar
   - Create a new challenge and check for the **"loki"** type

---

## Configuration

All settings are managed through the **Admin → Loki → Settings** page.

| Setting | Default | Description |
|---|---|---|
| Docker API URL | `unix:///var/run/docker.sock` | Docker daemon endpoint |
| Container Timeout | `3600` (1 hour) | Seconds before auto-cleanup |
| Max Containers | `100` | Global container limit |
| Max Renewals | `5` | Per-instance renewal cap |
| Custom DNS | _(empty)_ | Comma-separated DNS servers for containers |
| Auto-connect Network | _(empty)_ | Docker network to attach containers to |
| Read-only RootFS | `0` | Run challenge containers with read-only root filesystem |
| Drop All Capabilities | `1` | Drop all Linux capabilities (`cap_drop=ALL`) |
| No New Privileges | `1` | Prevent privilege escalation (`no-new-privileges`) |
| PIDs Limit | `256` | Max process count per challenge container |
| /tmp tmpfs Size | `64m` | Size of writable hardened `/tmp` tmpfs mount |
| Container Scope | `user` | `user` or `team` |
| Default Flag Mode | `static` | `static` or `dynamic` |
| Flag Template | `flag{<uuid>}` | Jinja2 template for dynamic flags |
| Backend | `docker` | Container backend (Swarm planned) |
| Router | `direct` | Routing method (Traefik/frp planned) |
| Rate Limit | `60` seconds | Cooldown between container operations |

---

## Usage

### For Admins

1. **Go to Admin → Challenges → Create Challenge**
2. **Select type: `loki`**
3. Fill in standard fields (name, category, description, points)
4. Configure container settings:
   - **Docker Image** — must be pre-built and available on the host
   - **Internal Port** — the port your service listens on (e.g. `22` for SSH)
   - **Connection Type** — `ssh`, `tcp`, or `http`
   - **SSH Username** — shown in connection info
   - **Memory / CPU** — resource limits
5. Choose **Flag Mode**:
   - **Static** → add flags manually in the "Flags" tab
   - **Dynamic** → each instance generates a unique flag from the template
6. **Save**

### For Players

1. Open the challenge
2. Click **Start Instance** → container spins up in ~3 seconds
3. Connection info appears with a copy button:
   ```
   ssh -p 49152 ctf@<SERVER_IP>
   ```
4. Solve the challenge in your personal instance
5. Submit the flag
6. Click **Stop Instance** when done (or wait for auto-cleanup)

### Container Management (Admin)

Visit **Admin → Loki → Containers** to:
- View all running containers with user, challenge, port, and remaining time
- **Renew** any container (bypass renewal limits)
- **Destroy** any container immediately

---

## API Reference

All endpoints are under `/api/v1/plugins/ctfd-loki/`.

### User Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/container?challenge_id=N` | Get current instance status |
| `POST` | `/container?challenge_id=N` | Start a new instance (blocked if another is running) |
| `PATCH` | `/container?challenge_id=N` | Renew (extend timeout) |
| `DELETE` | `/container?challenge_id=N` | Stop and destroy |

### Admin Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/container?page=N` | List all containers (paginated) |
| `PATCH` | `/admin/container?container_id=N` | Renew a container (preferred lookup) |
| `DELETE` | `/admin/container?container_id=N` | Destroy a container (preferred lookup) |

Admin compatibility fallback:
- `user_id` is still accepted for renew/destroy operations.
- `challenge_id`/`team_id` can be supplied with `user_id` to disambiguate.

---

## Database Schema

### `LokiChallenge` (extends `challenges`)

| Column | Type | Default |
|---|---|---|
| `docker_image` | String(512) | `""` |
| `redirect_port` | Integer | `22` |
| `redirect_type` | String(32) | `"ssh"` |
| `ssh_user` | String(64) | `"ctf"` |
| `memory_limit` | String(32) | `"256m"` |
| `cpu_limit` | Float | `0.5` |
| `flag_mode` | String(16) | `"static"` |
| `flag_template` | Text | Jinja2 template |
| `dynamic_score` | Integer | `0` |

### `loki_containers`

| Column | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `user_id` | FK → users | Instance owner |
| `team_id` | FK → teams | Owner's team (nullable) |
| `challenge_id` | FK → challenges | Associated challenge |
| `container_id` | String(128) | Docker container ID |
| `start_time` | DateTime | When started |
| `renew_count` | Integer | Times renewed |
| `uuid` | String(64) | Unique instance identifier |
| `port` | Integer | Assigned host port |
| `flag` | String(256) | Generated flag (dynamic mode) |

---

## Preparing Challenge Images

Your Docker image must:

1. **Accept the `CHALLENGE_PASSWORD` env var** and set it as the user's password in the entrypoint
2. **Accept the `FLAG` env var** (for dynamic flag mode) and write it to `/flag.txt` or equivalent
3. **Expose the service port** (e.g. SSH on port 22)
4. **Run in the foreground** (the entrypoint must not exit)

Example entrypoint:
```bash
#!/bin/bash
echo "ctf:${CHALLENGE_PASSWORD:-defaultpass}" | chpasswd
if [ -n "$FLAG" ]; then echo "$FLAG" > /flag.txt; fi
exec /usr/sbin/sshd -D
```

---

## Roadmap

### Phase 2 (Planned)
- **Docker Swarm backend** — multi-node orchestration
- **Traefik router** — auto-discovery via Docker labels
- **frp router** — legacy compatibility
- **Multi-container challenges** — YAML-based multi-service definitions
- **Admin router config UI**

### Phase 3 (Planned)
- **Redis-backed rate limiting**
- **Container health monitoring**
- **Admin bulk actions** (destroy all, renew all)
- **Challenge import/export**
- **Full test suite**

---

## Security Considerations

- **Docker socket** — grants root-equivalent access; restrict permissions
- **Runtime hardening** — enable `cap_drop=ALL` and `no-new-privileges` (defaults in Loki)
- **Resource limits** — always set memory, CPU, and process limits per challenge
- **Filesystem controls** — use read-only rootfs when compatible and writable tmpfs only where needed
- **Network isolation** — use `docker_auto_connect_network` for internal networks
- **Rate limiting** — prevents container spam (configurable cooldown)
- **Cleanup** — auto-cleanup runs every 30 seconds; implement additional monitoring for production

---

## Compatibility Notes

- Loki is aligned with latest CTFd challenge plugin frontend contracts:
   - challenge view template extends `challenge.html`
   - challenge script implements `CTFd._internal.challenge` lifecycle hooks
   - submission path uses CTFd challenge attempt API flow
- Admin create/update scripts are compatible with dynamic script loading in CTFd admin challenge pages.

---

## License

[MIT](LICENSE) — Free for personal and commercial use.

---

## Credits

- Inspired by [CTFd-whale](https://github.com/frankli0324/ctfd-whale)
- Built for [rsuCTF 2026](https://github.com/rsuCTF)
