# Docker Security

This document lists the security measures implemented to safely run untrusted agent code.

## Container Isolation

**Hardening:**
- Uses **Docker Hardened Images (DHI)** as a secure base
- **Shell-free runtime**: `/bin/sh` and other shell binaries are removed to prevent command injection
- Runs as non-root user `runner` (UID 10001)
- `no-new-privileges` prevents privilege escalation
- All Linux capabilities dropped (`CAP_DROP ALL`)

**Filesystem:**
- Root filesystem is read-only
- `/tmp` and `/run` mounted as tmpfs with `noexec,nosuid,nodev`
- Zip extraction checks for path traversal attacks

**Network:**
- Completely disabled (`network_mode: none`)

## Resource Limits

Prevents resource exhaustion attacks:
- Memory: 512MB
- CPU: 1 core
- Processes: 256
- File descriptors: 1024
- **Logs: 5MB** (prevents memory DoS on the runner process)

## Build Security

- **Docker Hardened Images**: Base images provided by `dhi.io` with SLSA Level 3 provenance and built-in SBOMs.
- Automated vulnerability scanning with **Trivy** on custom dependencies.
- Scans fail CI/CD if critical vulnerabilities are found.

## Configuration

Runtime settings are defined in `secure_default_settings.yaml`.
