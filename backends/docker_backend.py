"""
CTFd LOKI — Plain Docker Backend
==================================

Manages challenge containers using the Docker Engine API via docker-py.
Designed for single-host deployments (no Swarm required).
"""

import logging
import random
import string

import docker
import docker.errors

from ..config import get_loki_config
from .base import BackendBase

log = logging.getLogger("ctfd-loki.docker")


class DockerBackend(BackendBase):
    """Plain Docker container backend (default)."""

    _client = None

    # ── Client management ────────────────────────────────────────

    @classmethod
    def _get_client(cls):
        """Lazily initialise the Docker client on first use."""
        if cls._client is None:
            api_url = get_loki_config("docker_api_url", "unix:///var/run/docker.sock")
            try:
                cls._client = docker.DockerClient(base_url=api_url)
                cls._client.ping()
                log.info("Connected to Docker daemon at %s", api_url)
            except Exception as exc:
                cls._client = None
                log.error("Failed to connect to Docker: %s", exc)
                raise RuntimeError(
                    f"Cannot connect to Docker daemon at {api_url}. "
                    "Ensure Docker is running and the socket is accessible."
                ) from exc
        return cls._client

    @classmethod
    def reset_client(cls):
        """Force reconnection on next use (e.g. after config change)."""
        cls._client = None

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_memory_limit(text):
        """Convert human-readable memory string to bytes."""
        if not text:
            return None
        text = str(text).strip().lower()
        if text.endswith("g"):
            return int(text[:-1]) * 1024 * 1024 * 1024
        if text.endswith("m"):
            return int(text[:-1]) * 1024 * 1024
        if text.endswith("k"):
            return int(text[:-1]) * 1024
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _random_password(length=8):
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def _as_bool(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    # ── BackendBase implementation ───────────────────────────────

    def create_container(self, challenge, container_record):
        """
        Create a detached Docker container with resource limits and
        a random port mapping.
        """
        client = self._get_client()
        internal_port = challenge.redirect_port or 22
        memory = self._parse_memory_limit(challenge.memory_limit)
        cpu_nano = int((challenge.cpu_limit or 0.5) * 1e9)
        password = self._random_password()

        env = {"CHALLENGE_PASSWORD": password}
        if container_record.flag:
            env["FLAG"] = container_record.flag

        # DNS config
        dns_str = get_loki_config("docker_dns", "")
        dns_list = [d.strip() for d in dns_str.split(",") if d.strip()] or None

        # Runtime hardening config
        read_only_rootfs = self._as_bool(
            get_loki_config("docker_security_read_only_rootfs", "0")
        )
        drop_all_caps = self._as_bool(
            get_loki_config("docker_security_drop_all_caps", "1")
        )
        no_new_privileges = self._as_bool(
            get_loki_config("docker_security_no_new_privileges", "1")
        )
        tmpfs_size = str(get_loki_config("docker_security_tmpfs_size", "64m")).strip()

        pids_limit = None
        try:
            pids_limit_val = int(get_loki_config("docker_security_pids_limit", "256"))
            if pids_limit_val > 0:
                pids_limit = pids_limit_val
        except (TypeError, ValueError):
            pids_limit = 256

        run_kwargs = {
            "image": challenge.docker_image,
            "name": f"loki-{container_record.user_id}-{container_record.uuid[:12]}",
            "detach": True,
            "ports": {f"{internal_port}/tcp": None},
            "environment": env,
            "mem_limit": memory,
            "nano_cpus": cpu_nano,
            "dns": dns_list,
            "read_only": read_only_rootfs,
            "pids_limit": pids_limit,
            "labels": {
                "loki.user_id": str(container_record.user_id),
                "loki.challenge_id": str(container_record.challenge_id),
                "loki.uuid": container_record.uuid,
            },
        }

        if drop_all_caps:
            run_kwargs["cap_drop"] = ["ALL"]

        if no_new_privileges:
            run_kwargs["security_opt"] = ["no-new-privileges"]

        if tmpfs_size:
            run_kwargs["tmpfs"] = {
                "/tmp": f"size={tmpfs_size},rw,noexec,nosuid,nodev"
            }

        container = client.containers.run(**run_kwargs)

        # Reload to get port mapping
        container.reload()
        port_info = container.attrs["NetworkSettings"]["Ports"].get(
            f"{internal_port}/tcp"
        )
        host_port = int(port_info[0]["HostPort"]) if port_info else 0

        # Optionally connect to a shared network
        network_name = get_loki_config("docker_auto_connect_network", "")
        if network_name:
            try:
                network = client.networks.get(network_name)
                network.connect(container)
            except docker.errors.NotFound:
                log.warning("Network %s not found, skipping", network_name)

        return container.id, host_port

    def remove_container(self, container_record):
        """Stop and remove the container, tolerating 'not found'."""
        client = self._get_client()
        try:
            container = client.containers.get(container_record.container_id)
            container.stop(timeout=5)
            container.remove(force=True)
            log.info("Removed container %s", container_record.container_id[:12])
            return True
        except docker.errors.NotFound:
            log.warning(
                "Container %s not found (already removed?)",
                container_record.container_id[:12],
            )
            return True  # treat as success
        except Exception as exc:
            log.error("Failed to remove container: %s", exc)
            return False

    def is_running(self, container_record):
        """Check if the container exists and is in 'running' state."""
        try:
            client = self._get_client()
            container = client.containers.get(container_record.container_id)
            return container.status == "running"
        except docker.errors.NotFound:
            return False
        except Exception:
            return False
