"""
CTFd LOKI — Challenge Type
============================

Registers the ``loki`` challenge type with CTFd and defines CRUD + solve logic.
"""

from flask import Blueprint

from CTFd.models import db, Flags, Solves, Fails, Tags, Hints, ChallengeFiles
from CTFd.plugins.challenges import BaseChallenge
from CTFd.plugins.flags import get_flag_class
from CTFd.utils import user as current_user
from CTFd.utils.uploads import delete_file

from .config import get_loki_config
from .models import LokiChallenge, LokiContainer
from .backends import get_backend


def _to_int_bool(value):
    """Normalise checkbox/select style values to 0 or 1."""
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return 1
    return 0


class LokiChallengeType(BaseChallenge):
    """
    Custom challenge type that provisions a Docker container per player.
    """

    id = "loki"
    name = "loki"

    blueprint = Blueprint(
        "ctfd-loki-challenge",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = LokiChallenge

    # Templates and scripts are set dynamically in __init__.py
    templates = {}
    scripts = {}

    # ── Create ───────────────────────────────────────────────────

    @classmethod
    def create(cls, request):
        data = request.form or request.get_json()
        docker_image = str(data.get("docker_image", "")).strip()
        challenge = LokiChallenge(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            value=int(data.get("value", 0)),
            state=data.get("state", "visible"),
            type="loki",
            # Container fields
            docker_image=docker_image,
            redirect_port=int(data.get("redirect_port", 22)),
            redirect_type=data.get("redirect_type", "ssh"),
            ssh_user=data.get("ssh_user", "ctf"),
            tcp_display_template=data.get("tcp_display_template", ""),
            memory_limit=data.get("memory_limit", "256m"),
            cpu_limit=float(data.get("cpu_limit", 0.5)),
            # Flag settings
            flag_mode=data.get("flag_mode", "static"),
            flag_template=data.get("flag_template", ""),
            # Scoring
            dynamic_score=_to_int_bool(data.get("dynamic_score", 0)),
        )
        db.session.add(challenge)
        db.session.commit()
        return challenge

    # ── Read ─────────────────────────────────────────────────────

    @classmethod
    def read(cls, challenge):
        challenge = LokiChallenge.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "description": challenge.description,
            "attribution": challenge.attribution,
            "connection_info": challenge.connection_info,
            "next_id": challenge.next_id,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
            # Loki-specific
            "docker_image": challenge.docker_image,
            "redirect_port": challenge.redirect_port,
            "redirect_type": challenge.redirect_type,
            "ssh_user": challenge.ssh_user,
            "tcp_display_template": challenge.tcp_display_template,
            "memory_limit": challenge.memory_limit,
            "cpu_limit": challenge.cpu_limit,
            "flag_mode": challenge.flag_mode,
            "flag_template": challenge.flag_template,
            "dynamic_score": challenge.dynamic_score,
        }
        return data

    # ── Update ───────────────────────────────────────────────────

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json()
        for attr, value in data.items():
            if attr in ("initial", "minimum", "decay"):
                value = float(value)
            elif attr in ("value", "redirect_port"):
                value = int(value)
            elif attr == "dynamic_score":
                value = _to_int_bool(value)
            elif attr == "cpu_limit":
                value = float(value)
            elif attr == "docker_image":
                value = str(value or "").strip()
            elif attr == "tcp_display_template":
                value = str(value or "").strip()
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    # ── Delete ───────────────────────────────────────────────────

    @classmethod
    def delete(cls, challenge):
        # Destroy all running containers for this challenge
        containers = LokiContainer.query.filter_by(
            challenge_id=challenge.id
        ).all()
        try:
            backend = get_backend()
            for c in containers:
                backend.remove_container(c)
        except Exception:
            pass
        LokiContainer.query.filter_by(challenge_id=challenge.id).delete()

        # Delegate to CTFd's base cleanup to keep behavior aligned with the
        # running CTFd version and ensure parent/child challenge rows are removed.
        super(LokiChallengeType, cls).delete(challenge)

    # ── Attempt (flag checking) ──────────────────────────────────

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()

        # 1. Check static flags defined by the admin
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        if flags:
            for flag in flags:
                if get_flag_class(flag.type).compare(flag, submission):
                    return True, "Correct"
            # If static flags exist and none matched, check dynamic below
            # only if flag_mode is dynamic too
            if challenge.flag_mode != "dynamic":
                return False, "Incorrect"

        # 2. Check per-instance dynamic flag
        if challenge.flag_mode == "dynamic":
            user = current_user.get_current_user()
            scope = get_loki_config("container_scope", "user")

            q = LokiContainer.query.filter_by(challenge_id=challenge.id)
            if scope == "team" and getattr(user, "team_id", None):
                container = q.filter_by(team_id=user.team_id).first()
            else:
                container = q.filter_by(user_id=user.id).first()

            if container is None:
                return False, "Please start an instance first"
            if container.flag and container.flag == submission:
                return True, "Correct"
            return False, "Incorrect"

        # 3. No flags defined and not dynamic — shouldn't happen
        if not flags:
            return False, "No flag configured for this challenge"
        return False, "Incorrect"

    # ── Solve ────────────────────────────────────────────────────

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

    # ── Fail ─────────────────────────────────────────────────────

    @classmethod
    def fail(cls, user, team, challenge, request):
        super().fail(user, team, challenge, request)
