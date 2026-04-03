"""
CTFd LOKI — API Routes
========================

Flask-RESTX namespaces for player and admin container operations.
Follows CTFd's existing API pattern for consistency.
"""

import logging
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource, abort

from CTFd.models import db
from CTFd.utils import get_config
from CTFd.utils import user as current_user
from CTFd.utils.decorators import admins_only, authed_only

from .config import get_loki_config
from .decorators import challenge_visible, frequency_limited
from .models import LokiChallenge, LokiContainer
from .backends import get_backend

log = logging.getLogger("ctfd-loki.api")

admin_namespace = Namespace("ctfd-loki-admin")
user_namespace = Namespace("ctfd-loki-user")


# ── Error handlers ───────────────────────────────────────────────

@admin_namespace.errorhandler
@user_namespace.errorhandler
def handle_default(err):
    return {"success": False, "message": "An unexpected error occurred"}, 500


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _get_owner_id():
    """Return (user_id, team_id) based on the configured container scope."""
    user = current_user.get_current_user()
    scope = get_loki_config("container_scope", "user")
    if scope == "team" and hasattr(user, "team_id") and user.team_id:
        return user.id, user.team_id
    return user.id, None


def _get_existing_container(user_id, team_id=None):
    """
    Find an existing running container for this user/team.
    In team mode, any team member's container counts.
    """
    scope = get_loki_config("container_scope", "user")
    if scope == "team" and team_id:
        return LokiContainer.query.filter_by(team_id=team_id).first()
    return LokiContainer.query.filter_by(user_id=user_id).first()


def _resolve_admin_container():
    """
    Resolve a container for admin actions.
    Preferred key is container_id (DB id), with user_id fallback.
    """
    container_id = request.args.get("container_id", type=int)
    if container_id:
        return LokiContainer.query.filter_by(id=container_id).first()

    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return None

    challenge_id = request.args.get("challenge_id", type=int)
    team_id = request.args.get("team_id", type=int)

    q = LokiContainer.query.filter_by(user_id=user_id)
    if challenge_id:
        q = q.filter_by(challenge_id=challenge_id)
    if team_id:
        q = q.filter_by(team_id=team_id)
    return q.order_by(LokiContainer.id.desc()).first()


def _resolve_public_host():
    """
    Resolve host used in player connection info.

    Priority:
      1) loki:public_host override
      2) X-Forwarded-Host (reverse proxy)
      3) request.host
    """
    configured = (get_loki_config("public_host", "") or "").strip()
    if configured:
        return configured

    forwarded = (request.headers.get("X-Forwarded-Host", "") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip().split(":")[0]

    host = (request.host or "").strip()
    if host:
        return host.split(":")[0]

    return "127.0.0.1"


def _is_container_running(container):
    """Best-effort running-state check against the backend runtime."""
    try:
        backend = get_backend()
        return backend.is_running(container)
    except Exception as exc:
        log.warning("Container state check failed for %s: %s", container.id, exc)
        return False


# ═══════════════════════════════════════════════════════════════════
#  ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@admin_namespace.route("/container")
class AdminContainers(Resource):
    @staticmethod
    @admins_only
    def get():
        """List all running containers (paginated)."""
        page = abs(request.args.get("page", 1, type=int))
        per_page = abs(request.args.get("per_page", 20, type=int))
        offset = per_page * (page - 1)

        total = LokiContainer.query.count()
        containers = LokiContainer.query.offset(offset).limit(per_page).all()

        timeout = int(get_loki_config("docker_timeout", "3600"))
        data = []
        for c in containers:
            elapsed = (datetime.utcnow() - c.start_time).total_seconds()
            data.append(
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "team_id": c.team_id,
                    "challenge_id": c.challenge_id,
                    "challenge_name": c.challenge.name if c.challenge else "?",
                    "user_name": c.user.name if c.user else "?",
                    "container_id": c.container_id[:12] if c.container_id else "",
                    "port": c.port,
                    "start_time": c.start_time.isoformat(),
                    "remaining": max(0, timeout - int(elapsed)),
                    "renew_count": c.renew_count,
                }
            )

        return {
            "success": True,
            "data": {
                "containers": data,
                "total": total,
                "pages": (total // per_page) + (1 if total % per_page else 0),
                "page_start": offset,
            },
        }

    @staticmethod
    @admins_only
    def patch():
        """Renew a container (admin override — no renew limit)."""
        if not request.args.get("container_id", type=int) and not request.args.get(
            "user_id", type=int
        ):
            abort(400, "Missing container_id or user_id", success=False)

        container = _resolve_admin_container()
        if not container:
            abort(404, "No container found", success=False)

        container.start_time = datetime.utcnow()
        container.renew_count += 1
        db.session.commit()
        return {"success": True, "message": "Container renewed"}

    @staticmethod
    @admins_only
    def delete():
        """Destroy a user's container (admin override)."""
        if not request.args.get("container_id", type=int) and not request.args.get(
            "user_id", type=int
        ):
            abort(400, "Missing container_id or user_id", success=False)

        container = _resolve_admin_container()
        if not container:
            abort(404, "No container found", success=False)

        try:
            backend = get_backend()
            backend.remove_container(container)
        except Exception as exc:
            log.error("Failed to remove container: %s", exc)

        db.session.delete(container)
        db.session.commit()
        return {"success": True, "message": "Container destroyed"}


# ═══════════════════════════════════════════════════════════════════
#  USER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@user_namespace.route("/container")
class UserContainers(Resource):

    # ── GET: status ──────────────────────────────────────────────

    @staticmethod
    @authed_only
    @challenge_visible
    def get():
        """Return current container info for the authenticated user."""
        user_id, team_id = _get_owner_id()
        challenge_id = request.args.get("challenge_id", type=int)
        container = _get_existing_container(user_id, team_id)

        if not container:
            return {"success": True, "data": {}}

        # Cleanup stale DB records if container no longer exists/runs.
        if not _is_container_running(container):
            db.session.delete(container)
            db.session.commit()
            return {"success": True, "data": {}}

        # Verify the container belongs to the requested challenge
        if int(container.challenge_id) != int(challenge_id):
            chal_name = container.challenge.name if container.challenge else "another"
            abort(
                403,
                f"You already have a running instance for '{chal_name}'. "
                "Please stop it before starting a new one.",
                success=False,
            )

        timeout = int(get_loki_config("docker_timeout", "3600"))
        elapsed = (datetime.utcnow() - container.start_time).total_seconds()

        backend = get_backend()
        connection_info = backend.get_connection_info(container.challenge, container)
        connection_info = connection_info.replace("{SERVER_IP}", _resolve_public_host())

        return {
            "success": True,
            "data": {
                "user_access": connection_info,
                "port": container.port,
                "remaining_time": max(0, timeout - int(elapsed)),
                "renew_count": container.renew_count,
            },
        }

    # ── POST: start ──────────────────────────────────────────────

    @staticmethod
    @authed_only
    @challenge_visible
    @frequency_limited
    def post():
        """Start a new container instance."""
        user_id, team_id = _get_owner_id()
        challenge_id = request.args.get("challenge_id", type=int)

        # Block if an instance is already running. User must stop it first.
        existing = _get_existing_container(user_id, team_id)
        if existing:
            # Recover from stale records that can block restart.
            if not _is_container_running(existing):
                db.session.delete(existing)
                db.session.commit()
                existing = None

        if existing:
            if int(existing.challenge_id) == int(challenge_id):
                abort(
                    403,
                    "You already have a running instance for this challenge. "
                    "Please stop it before starting a new one.",
                    success=False,
                )
            chal_name = existing.challenge.name if existing.challenge else "another"
            abort(
                403,
                f"You already have a running instance for '{chal_name}'. "
                "Please stop it before starting a new one.",
                success=False,
            )

        # Enforce global container limit
        max_containers = int(get_loki_config("docker_max_containers", "100"))
        current_count = LokiContainer.query.count()
        if current_count >= max_containers:
            abort(
                403,
                "Maximum container limit reached. Please try again later.",
                success=False,
            )

        # Create the container record
        container = LokiContainer(
            user_id=user_id,
            challenge_id=challenge_id,
            team_id=team_id,
        )
        db.session.add(container)
        db.session.flush()  # Get the ID without committing

        # Spin up the Docker container
        challenge = LokiChallenge.query.filter_by(id=challenge_id).first()
        if not challenge:
            db.session.rollback()
            abort(404, "Challenge not found", success=False)

        try:
            backend = get_backend()
            container_id, port = backend.create_container(challenge, container)
            container.container_id = container_id
            container.port = port
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            log.error("Container creation failed: %s", exc)
            abort(500, f"Failed to start instance: {exc}", success=False)

        start_delay = int(get_loki_config("ui_start_delay_seconds", "3"))
        if start_delay < 0:
            start_delay = 0

        return {
            "success": True,
            "message": "Instance started",
            "data": {"start_delay_seconds": start_delay},
        }

    # ── PATCH: renew ─────────────────────────────────────────────

    @staticmethod
    @authed_only
    @challenge_visible
    @frequency_limited
    def patch():
        """Renew (extend) the container's lifetime."""
        user_id, team_id = _get_owner_id()
        challenge_id = request.args.get("challenge_id", type=int)

        container = _get_existing_container(user_id, team_id)
        if not container:
            abort(404, "No running instance found", success=False)

        if int(container.challenge_id) != int(challenge_id):
            abort(403, "Instance belongs to a different challenge", success=False)

        max_renew = int(get_loki_config("docker_max_renew_count", "5"))
        if container.renew_count >= max_renew:
            abort(403, "Maximum renewal count reached", success=False)

        container.start_time = datetime.utcnow()
        container.renew_count += 1
        db.session.commit()

        return {"success": True, "message": "Instance renewed"}

    # ── DELETE: stop ─────────────────────────────────────────────

    @staticmethod
    @authed_only
    @frequency_limited
    def delete():
        """Stop and destroy the user's running container."""
        user_id, team_id = _get_owner_id()
        container = _get_existing_container(user_id, team_id)

        if not container:
            abort(404, "No running instance found", success=False)

        try:
            backend = get_backend()
            backend.remove_container(container)
        except Exception as exc:
            log.error("Container removal failed: %s", exc)
            abort(500, f"Failed to stop instance: {exc}", success=False)

        db.session.delete(container)
        db.session.commit()
        stop_delay = int(get_loki_config("ui_stop_delay_seconds", "2"))
        if stop_delay < 0:
            stop_delay = 0

        return {
            "success": True,
            "message": "Instance destroyed",
            "data": {"stop_delay_seconds": stop_delay},
        }
