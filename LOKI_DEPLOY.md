# CTFd Loki Deployment and Operations Guide

This document describes how to install, configure, and operate the ctfd-loki plugin with CTFd, including required changes to the CTFd deployment and common fixes.

## Scope
- Plugin: ctfd-loki (dynamic container challenge type)
- CTFd: 3.8.x (as in this workspace)
- Docker: local Docker Engine

## Installation Overview
1) Place ctfd-loki under the CTFd plugins directory.
2) Ensure plugin Python dependencies are installed in the CTFd virtualenv.
3) Ensure CTFd can access the Docker daemon (socket mount and permissions).
4) Restart CTFd and verify plugin load.

## Required CTFd Deployment Changes
These changes are required for Loki to spawn containers.

### 1) Docker socket mount
The CTFd container must access the host Docker daemon.

Add this volume to the CTFd service:

- /var/run/docker.sock:/var/run/docker.sock

### 2) Docker group permissions
The CTFd process runs as uid 1001. It must be in the host Docker group.

Steps:
- Check docker group gid on the host:
  getent group docker
- Add that gid to the CTFd service using group_add.

Example snippet:

services:
  ctfd:
    group_add:
      - "978"  # replace with your docker group gid
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

### 3) Plugin availability inside the container
CTFd must see ctfd-loki inside /opt/CTFd/CTFd/plugins.

Recommended:
- Copy the plugin into CTFd/CTFd/plugins/ctfd-loki (real folder, not symlink).

If you use a symlink:
- The symlink target must be inside the mounted repo path.
- A symlink to a host path outside the repo will be broken inside the container.

## Plugin Dependencies
ctfd-loki depends on the Docker Python SDK and Flask-APScheduler.

The plugin pins:
- Flask 2.1.3
- Flask-Babel 2.0.0
- Flask-APScheduler 1.12.4
- docker >= 6.0.0

Install inside the CTFd container:

/opt/venv/bin/pip install -r /opt/CTFd/CTFd/plugins/ctfd-loki/requirements.txt

If you rebuild CTFd with the plugin in CTFd/CTFd/plugins, the Dockerfile will install plugin requirements during build.

## Initial Plugin Configuration
Open Admin -> Loki -> Settings.

Required:
- Docker API URL: unix:///var/run/docker.sock

Recommended:
- Public Host: your external hostname or IP if behind a reverse proxy
- Container Scope: user or team
- Timeouts and limits
- TCP Display Format: Netcat (nc host port) or HTB (host:port)

## Creating a Loki Challenge
1) Admin -> Challenges -> New
2) Choose type: loki
3) Set container fields:
   - Docker Image: image name that exists on the Docker host
   - Internal Port: service port exposed by the image
   - Connection Type: ssh / tcp / http
   - SSH Username: for ssh challenges
  - TCP Display Format: Use default, Netcat, or HTB (for TCP only)
4) Flag mode:
   - Static: set flags in the Flags tab
   - Dynamic: per-instance flags from the template
5) Save

## Common Operational Flow
- User clicks Spawn Target
- Loki creates a container and returns connection info
- User clicks Stop or Renew
- Auto-cleanup reaps expired containers

## Troubleshooting

### 1) Plugin not visible in Challenge creation
Cause:
- Plugin not present inside /opt/CTFd/CTFd/plugins

Fix:
- Copy ctfd-loki into CTFd/CTFd/plugins/ctfd-loki
- Restart CTFd
- Check logs for plugin import errors

### 2) Spawn Target returns 500 with No module named 'docker'
Cause:
- Docker SDK not installed in CTFd venv

Fix:
- /opt/venv/bin/pip install -r /opt/CTFd/CTFd/plugins/ctfd-loki/requirements.txt
- Restart CTFd

### 3) Cannot connect to Docker daemon
Symptom:
- RuntimeError: Cannot connect to Docker daemon at unix:///var/run/docker.sock

Cause:
- Socket not mounted or permissions blocked

Fix:
- Mount /var/run/docker.sock into the ctfd container
- Add docker group gid via group_add
- Restart CTFd

### 4) Permission denied on docker.sock
Symptom:
- PermissionError(13, 'Permission denied')

Fix:
- Add docker group gid to ctfd service (group_add)
- Restart CTFd

### 5) Image not found
Symptom:
- ImageNotFound: pull access denied for <image>

Fix:
- Build the image on the same Docker host:
  docker build -t <image>:<tag> .
- Or push to a registry and use full image reference
- Update the Loki challenge Docker Image field

### 6) Flask / Flask-Babel mismatch crashes CTFd
Symptom:
- ImportError: locked_cached_property from flask.helpers

Cause:
- Flask upgraded to 3.x while Flask-Babel is 2.0.0

Fix (without changing CTFd repo):
- Ensure ctfd-loki requirements are installed and keep Flask pinned to 2.1.3
- Rebuild the image after updating plugin requirements

### 7) TCP display format does not match expected output
Cause:
- Challenge override set or global template set to the wrong option

Fix:
- Check Admin -> Loki -> Settings -> TCP Display Format
- Check the challenge's TCP Display Format field for overrides

## Validation Checklist
- Admin -> Loki -> Settings saves without errors
- Loki appears in Challenge type list
- Spawn Target succeeds
- Connection info renders correctly
- Admin -> Loki -> Containers shows live instances
- Stop/Renew works
- Auto-cleanup removes expired instances

## Notes
- Loki uses the Docker daemon configured in settings.
- Ensure the Docker image listens on the internal port you configured.
- For per-player instances, the image must be runnable without manual setup.
