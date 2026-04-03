"""
CTFd LOKI — Abstract Backend Interface
========================================

All container backends must implement this interface.
"""

from abc import ABC, abstractmethod


class BackendBase(ABC):
    """
    Abstract base class for container orchestration backends.

    Each backend handles the lifecycle of challenge containers:
    creation, removal, and status checking.
    """

    @abstractmethod
    def create_container(self, challenge, container_record):
        """
        Create and start a container for the given challenge.

        Parameters
        ----------
        challenge : LokiChallenge
            The challenge model instance.
        container_record : LokiContainer
            The container tracking record (already has uuid, flag, etc.).

        Returns
        -------
        tuple[str, int]
            (container_id, assigned_host_port)
        """

    @abstractmethod
    def remove_container(self, container_record):
        """
        Stop and remove a running container.

        Parameters
        ----------
        container_record : LokiContainer
            The container tracking record.

        Returns
        -------
        bool
            True if successfully removed, False otherwise.
        """

    @abstractmethod
    def is_running(self, container_record):
        """
        Check whether a container is still running.

        Parameters
        ----------
        container_record : LokiContainer
            The container tracking record.

        Returns
        -------
        bool
        """

    def get_connection_info(self, challenge, container_record):
        """
        Build a human-readable connection string for the player.

        Parameters
        ----------
        challenge : LokiChallenge
        container_record : LokiContainer

        Returns
        -------
        str
        """
        port = container_record.port
        redirect_type = challenge.redirect_type or "tcp"

        if redirect_type == "ssh":
            user = challenge.ssh_user or "ctf"
            return f"ssh -p {port} {user}@{{SERVER_IP}}"
        elif redirect_type == "http":
            return f"http://{{SERVER_IP}}:{port}"
        else:
            return f"nc {{SERVER_IP}} {port}"
