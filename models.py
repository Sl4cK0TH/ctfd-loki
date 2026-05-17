"""
CTFd LOKI — Database Models
============================

Defines the challenge type table and instance tracking table.
Uses SQLAlchemy polymorphic inheritance to extend CTFd's Challenges model.
"""

import random
import uuid as _uuid
from datetime import datetime

from jinja2 import Template

from CTFd.models import db, Challenges
from CTFd.utils import get_config


class LokiChallenge(Challenges):
    """
    A challenge that provisions a Docker container per player/team.
    Inherits from CTFd's Challenges via polymorphic identity.
    """

    __mapper_args__ = {"polymorphic_identity": "loki"}

    id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # ── Container settings ───────────────────────────────────────
    docker_image = db.Column(db.String(512), default="")
    redirect_port = db.Column(db.Integer, default=22)
    redirect_type = db.Column(db.String(32), default="ssh")
    ssh_user = db.Column(db.String(64), default="ctf")
    tcp_display_template = db.Column(db.String(32), default="")

    # ── Resource limits ──────────────────────────────────────────
    memory_limit = db.Column(db.String(32), default="256m")
    cpu_limit = db.Column(db.Float, default=0.5)

    # ── Flag settings ────────────────────────────────────────────
    flag_mode = db.Column(db.String(16), default="static")
    flag_template = db.Column(
        db.Text,
        default='flag{{{ uuid.uuid4()|string }}}',
    )

    # ── Scoring ──────────────────────────────────────────────────
    dynamic_score = db.Column(db.Integer, default=0)

    def __init__(self, *args, **kwargs):
        super(LokiChallenge, self).__init__(**kwargs)

    def __repr__(self):
        return f"<LokiChallenge {self.name!r}>"


class LokiContainer(db.Model):
    """
    Tracks a running container provisioned for a specific user/team.
    """

    __tablename__ = "loki_containers"
    __table_args__ = (
        db.Index("ix_loki_containers_user_id", "user_id"),
        db.Index("ix_loki_containers_team_id", "team_id"),
        db.Index("ix_loki_containers_challenge_id", "challenge_id"),
        db.Index("ix_loki_containers_start_time", "start_time"),
        db.Index("ix_loki_containers_user_challenge", "user_id", "challenge_id"),
        db.Index("ix_loki_containers_team_challenge", "team_id", "challenge_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    container_id = db.Column(db.String(128), default="")
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    renew_count = db.Column(db.Integer, nullable=False, default=0)
    uuid = db.Column(db.String(64), nullable=False)
    port = db.Column(db.Integer, nullable=True, default=0)
    flag = db.Column(db.String(256), nullable=False, default="")

    # ── Relationships ────────────────────────────────────────────
    user = db.relationship(
        "Users", foreign_keys="LokiContainer.user_id", lazy="select"
    )
    challenge = db.relationship(
        "LokiChallenge",
        foreign_keys="LokiContainer.challenge_id",
        lazy="select",
    )

    def __init__(self, user_id, challenge_id, team_id=None):
        self.user_id = user_id
        self.challenge_id = challenge_id
        self.team_id = team_id
        self.start_time = datetime.utcnow()
        self.renew_count = 0
        self.uuid = str(_uuid.uuid4())

        # Generate flag based on challenge's flag_mode
        challenge = LokiChallenge.query.filter_by(id=challenge_id).first()
        if challenge and challenge.flag_mode == "dynamic":
            template_str = challenge.flag_template or get_config(
                "loki:flag_template",
                'flag{{{ uuid.uuid4()|string }}}',
            )
            self.flag = Template(template_str).render(
                container=self,
                uuid=_uuid,
                random=random,
                get_config=get_config,
            )
        else:
            self.flag = ""

    @property
    def remaining_seconds(self):
        """Seconds remaining before this container expires."""
        timeout = int(get_config("loki:docker_timeout", "3600"))
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        return max(0, timeout - int(elapsed))

    @property
    def is_expired(self):
        return self.remaining_seconds <= 0

    def __repr__(self):
        return (
            f"<LokiContainer user={self.user_id} "
            f"challenge={self.challenge_id} uuid={self.uuid}>"
        )
