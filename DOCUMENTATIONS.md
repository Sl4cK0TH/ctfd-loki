# CTFd Loki Documentation

This document describes how to use ctfd-loki as an admin and as a player, including configuration and display options.

## Admin Workflow

### 1) Configure Loki
Go to Admin -> Loki -> Settings.

Key settings:
- Docker API URL: unix:///var/run/docker.sock
- Public Host: external hostname or IP for connection info
- Container Timeout: lifetime before auto-clean
- Max Containers: global cap
- Max Renewals: per-instance renew limit
- Container Scope: user or team
- Default Flag Mode: static or dynamic
- TCP Display Format: Netcat (nc host port) or HTB (host:port)

### 2) Create a Loki Challenge
Admin -> Challenges -> New -> Type: loki

Fields:
- Docker Image
- Internal Port
- Connection Type: ssh / tcp / http
- SSH Username (ssh only)
- Memory / CPU limits
- Flag Mode: static or dynamic
- TCP Display Format: Use default, Netcat, or HTB (TCP only)

### 3) Flags
- Static: add flags in the Flags tab
- Dynamic: flags generated per instance using the template

### 4) Manage Containers
Admin -> Loki -> Containers
- See running instances
- Renew or Destroy instances

## Player Workflow
1) Open the challenge
2) Click Spawn Target
3) Use connection info provided
4) Solve and submit flag
5) Click Stop (or wait for auto-cleanup)

## Connection Display Formats
TCP/Netcat can be displayed in two formats:
- Netcat: nc host port
- HTB: host:port

Priority order:
1) Per-challenge override
2) Global default in Admin -> Loki -> Settings

## Common Operations

### Verify Docker access
- Socket exists: /var/run/docker.sock
- CTFd user has access via docker group

### Verify image availability
- Image must exist on the Docker host
- Example:
  docker build -t my-chal:latest .

## Troubleshooting Quick Hits

- Spawn Target returns 500 and logs show "No module named 'docker'"
  - Install plugin requirements in the CTFd venv

- Cannot connect to Docker daemon
  - Mount /var/run/docker.sock and add docker group gid

- ImageNotFound
  - Build the image locally or push to a registry

- TCP display format unexpected
  - Check global setting and per-challenge override
