"""
CTFd LOKI — Plugin Entry Point
================================

Registers all components when CTFd loads the plugin.
Named after Loki from the MCU — the one who holds the timelines together.
"""

import logging
import warnings

from flask import Blueprint, render_template, request, session

from CTFd.api import CTFd_API_v1
from CTFd.plugins import (
    register_plugin_assets_directory,
    register_admin_plugin_menu_bar,
)
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only

from .api import admin_namespace, user_namespace, AdminContainers
from .challenge_type import LokiChallengeType
from .config import setup_default_configs, get_loki_config
from .models import LokiContainer

log = logging.getLogger("ctfd-loki")


def load(app):
    # Suppress 404 help text in API responses
    app.config["RESTX_ERROR_404_HELP"] = False

    plugin_name = __name__.split(".")[-1]
    set_config("loki:plugin_name", plugin_name)

    # ── 1. Database ──────────────────────────────────────────────
    app.db.create_all()

    if not get_config("loki:setup"):
        setup_default_configs()
        log.info("Loki: first-run config written")

    # ── 2. Assets ────────────────────────────────────────────────
    register_plugin_assets_directory(
        app,
        base_path=f"/plugins/{plugin_name}/assets",
        endpoint="plugins.ctfd-loki.assets",
    )

    # ── 3. Admin menu entry ──────────────────────────────────────
    register_admin_plugin_menu_bar(
        title="Loki", route="/plugins/ctfd-loki/admin/settings"
    )

    # ── 4. Challenge type ────────────────────────────────────────
    LokiChallengeType.templates = {
        "create": f"/plugins/{plugin_name}/assets/create.html",
        "update": f"/plugins/{plugin_name}/assets/update.html",
        "view": f"/plugins/{plugin_name}/assets/view.html",
    }
    LokiChallengeType.scripts = {
        "create": f"/plugins/{plugin_name}/assets/create.js",
        "update": f"/plugins/{plugin_name}/assets/update.js",
        "view": f"/plugins/{plugin_name}/assets/view.js",
    }
    CHALLENGE_CLASSES["loki"] = LokiChallengeType

    # ── 5. API namespaces ────────────────────────────────────────
    CTFd_API_v1.add_namespace(admin_namespace, path="/plugins/ctfd-loki/admin")
    CTFd_API_v1.add_namespace(user_namespace, path="/plugins/ctfd-loki")

    # ── 6. Admin page blueprint ──────────────────────────────────
    page_blueprint = Blueprint(
        "ctfd-loki",
        __name__,
        template_folder="templates",
        static_folder="assets",
        url_prefix="/plugins/ctfd-loki",
    )

    @page_blueprint.route("/admin/settings")
    @admins_only
    def admin_settings():
        return render_template("loki_settings.html")

    @page_blueprint.route("/admin/containers")
    @admins_only
    def admin_containers():
        result = AdminContainers.get()
        return render_template(
            "loki_containers.html",
            plugin_name=plugin_name,
            containers=result["data"]["containers"],
            pages=result["data"]["pages"],
            curr_page=abs(request.args.get("page", 1, type=int)),
            curr_page_start=result["data"]["page_start"],
        )

    app.register_blueprint(page_blueprint)

    # ── 7. Auto-cleanup scheduler ────────────────────────────────
    _start_scheduler(app)

    log.info("CTFd LOKI loaded successfully")


def _start_scheduler(app):
    """
    Start a background job that reaps expired containers every 30 seconds.
    Uses a file lock to prevent duplicate schedulers in multi-worker setups.
    """
    import os
    import sys

    try:
        from flask_apscheduler import APScheduler
    except ImportError:
        log.warning("Flask-APScheduler not installed — auto-cleanup disabled")
        return

    # File lock to prevent duplicate schedulers (Linux/Mac only)
    lock_path = "/tmp/ctfd_loki.lock"
    if sys.platform != "win32":
        try:
            import fcntl

            lock_file = open(lock_path, "w")
            fcntl.lockf(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            return  # Another worker already holds the lock

    def auto_clean():
        with app.app_context():
            from .backends import get_backend

            try:
                containers = LokiContainer.query.all()
                backend = get_backend()
                for c in containers:
                    if c.is_expired:
                        try:
                            backend.remove_container(c)
                        except Exception:
                            pass
                        app.db.session.delete(c)
                app.db.session.commit()
            except Exception as exc:
                log.error("Auto-clean error: %s", exc)

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(
        id="loki-auto-clean",
        func=auto_clean,
        trigger="interval",
        seconds=30,
    )
    log.info("Loki auto-cleanup scheduler started (30s interval)")
