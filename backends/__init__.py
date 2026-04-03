"""
CTFd LOKI — Backend Abstraction
=================================

Provides a factory function to instantiate the configured container backend.
"""

from ..config import get_loki_config


def get_backend():
    """Return the configured backend instance."""
    backend_type = get_loki_config("backend", "docker")

    if backend_type == "docker":
        from .docker_backend import DockerBackend
        return DockerBackend()
    # Phase 2:
    # elif backend_type == "swarm":
    #     from .swarm_backend import SwarmBackend
    #     return SwarmBackend()
    else:
        raise ValueError(f"Unknown Loki backend: {backend_type!r}")
