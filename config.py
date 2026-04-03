"""
CTFd LOKI — Default Configuration
===================================

Stores default config values and handles first-run setup.
All keys are prefixed with ``loki:`` in CTFd's config table.
"""

from CTFd.utils import set_config, get_config

# Default configuration values
DEFAULTS = {
    "setup": "true",
    # ── Docker ───────────────────────────────────────────────
    "docker_api_url": "unix:///var/run/docker.sock",
    "docker_dns": "",
    "docker_auto_connect_network": "",
    "docker_timeout": "3600",
    "docker_max_containers": "100",
    "docker_max_renew_count": "5",
    # ── Docker runtime security ─────────────────────────────
    "docker_security_read_only_rootfs": "0",
    "docker_security_drop_all_caps": "1",
    "docker_security_no_new_privileges": "1",
    "docker_security_pids_limit": "256",
    "docker_security_tmpfs_size": "64m",
    # ── Container scope ──────────────────────────────────────
    "container_scope": "user",  # "user" or "team"
    # ── Flags ────────────────────────────────────────────────
    "flag_mode_default": "static",
    "flag_template": 'flag{{{ uuid.uuid4()|string }}}',
    # ── Backend & Router ─────────────────────────────────────
    "backend": "docker",  # Phase 2: "swarm"
    "router": "direct",   # Phase 2: "traefik", "frp"
    # ── Rate limiting ────────────────────────────────────────
    "rate_limit_seconds": "60",
}


def setup_default_configs():
    """Write default values into CTFd's config table on first load."""
    for key, val in DEFAULTS.items():
        set_config(f"loki:{key}", val)


def get_loki_config(key, fallback=None):
    """
    Convenience wrapper to read a ``loki:``-prefixed config value.

    Falls back to the default defined in ``DEFAULTS`` if not found.
    """
    value = get_config(f"loki:{key}")
    if value is None:
        return DEFAULTS.get(key, fallback)
    return value
