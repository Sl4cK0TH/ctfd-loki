"""
CTFd LOKI — Custom Decorators
================================

Provides route-level protection for challenge visibility and rate limiting.
"""

import functools
import time

from flask import request, session
from flask_restx import abort
from sqlalchemy.sql import and_

from CTFd.models import Challenges
from CTFd.utils.user import is_admin, get_current_user

from .config import get_loki_config


def challenge_visible(func):
    """
    Verify the challenge exists and is not hidden/locked for non-admin users.
    Expects ``challenge_id`` in the request args.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        challenge_id = request.args.get("challenge_id")
        if is_admin():
            if not Challenges.query.filter(Challenges.id == challenge_id).first():
                abort(404, "No such challenge", success=False)
        else:
            if not Challenges.query.filter(
                Challenges.id == challenge_id,
                and_(Challenges.state != "hidden", Challenges.state != "locked"),
            ).first():
                abort(403, "Challenge not visible", success=False)
        return func(*args, **kwargs)

    return _wrapper


def frequency_limited(func):
    """
    Session-based rate limiter — prevents rapid-fire container operations.
    Admins bypass the limit.  No Redis required.
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if is_admin():
            return func(*args, **kwargs)

        cooldown = int(get_loki_config("rate_limit_seconds", "60"))
        now = int(time.time())
        action = (request.method or "action").lower()
        session_key = f"loki_last_action_{action}"
        last = session.get(session_key, 0)

        if now - last < cooldown:
            remaining = cooldown - (now - last)
            abort(
                429,
                f"Too fast! Please wait {remaining} seconds before trying again.",
                success=False,
            )

        session[session_key] = now
        return func(*args, **kwargs)

    return _wrapper
