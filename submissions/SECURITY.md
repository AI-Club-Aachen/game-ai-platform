# Docker Security

This document lists the security measures implemented to safely run untrusted agent code.

## Container Isolation

**User privileges:**
- Runs as non-root user `runner`
- `no-new-privileges` prevents privilege escalation
- All Linux capabilities dropped

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

- Automated vulnerability scanning with Trivy on base image builds
- Scans fail CI/CD if critical or high-severity vulnerabilities are found

## Configuration

Runtime settings are defined in `secure_default_settings.yaml`.
