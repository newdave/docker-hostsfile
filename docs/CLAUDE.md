# Project Overview: Docker Hosts File Updater

## Objective

This project automatically maintains the system `/etc/hosts` file to enable name-based resolution of Docker containers on the host machine. It monitors Docker containers in real-time and creates DNS-like entries so containers can be accessed by name (e.g., `nginx`, `postgres`) and FQDN (e.g., `nginx.base.domain`) instead of IP addresses.

## Core Functionality

**Problem Solved**: Docker containers get dynamic IP addresses that are hard to remember and may change. This tool bridges the gap between Docker's internal DNS and the host system's name resolution.

**How It Works**:

1. Monitors Docker daemon for container lifecycle events (start, stop, connect, disconnect, etc.)
2. Extracts container metadata: container name, hostname, network aliases, and IP addresses
3. Updates a managed section of `/etc/hosts` with entries in format: `IP shortname shortname.base.domain`
4. Runs continuously as a system service or standalone daemon

## Key Features

- **Real-time event monitoring**: Watches Docker events using `docker events` API
- **Periodic fallback sync**: Updates hosts file at configurable intervals (e.g., 30s, 5m) to catch missed events
- **FQDN support**: Appends `.base.domain` to all hostnames for consistent domain-based access
- **Multi-network support**: Handles containers connected to multiple Docker networks
- **Thread-safe**: Uses asyncio locks to prevent race conditions during concurrent updates
- **Managed section**: Only modifies content between `# BEGIN DOCKER CONTAINERS` and `# END DOCKER CONTAINERS` markers
- **Atomic writes**: Uses temporary files and atomic moves to prevent corruption

## Technical Architecture

- **Language**: Python 3.7+ with asyncio for concurrent operations
- **Dependencies**: Docker CLI, Docker daemon, root/sudo access
- **Deployment**: Systemd service, Docker Compose, or standalone script
- **Update strategy**: Event-driven (primary) + periodic polling (fallback)

## Typical Use Cases

1. **Local development**: Access containers by name from host machine without hardcoding IPs
2. **Testing**: Stable hostnames for integration tests across container restarts
3. **Multi-container apps**: Simplify inter-container communication from host perspective
4. **DevOps workflows**: Consistent naming conventions across development environments

## File Structure

- `docker_hosts_updater.py`: Main Python script with all logic
- `docker-hosts-updater.service`: Systemd service unit file
- `docker-compose.yml`: Example Docker Compose deployment
- `test_updater.py`: Unit tests
- `README.md`: User documentation
- `Makefile`: Build and deployment automation

## Security Considerations

- Requires root/sudo access to modify `/etc/hosts`
- Uses read-only Docker socket access when possible
- Avoids `shell=True` in subprocess calls to prevent injection
- Validates and sanitizes all container names and hostnames
- Atomic file updates prevent corrupted hosts file

## Domain Configuration

The default domain base is `base.domain` (configurable in `DOMAIN_BASE` constant). All container names get both:

- Short form: `container-name`
- FQDN form: `container-name.base.domain`

## Example Output

For running containers `nginx` (hostname: `webserver`) and `postgres` (hostname: `db`), the managed section would contain:

```
# BEGIN DOCKER CONTAINERS
172.18.0.2 nginx nginx.base.domain webserver webserver.base.domain
172.18.0.3 postgres postgres.base.domain db db.base.domain
# END DOCKER CONTAINERS
```

## When to Modify This Code

- Changing the domain base (edit `DOMAIN_BASE`)
- Adjusting monitored Docker events (edit `events_to_monitor` list)
- Modifying update intervals (change systemd service or CLI argument)
- Adding custom hostname filtering or transformation logic
- Integrating with external DNS or service discovery systems

## What This Code Does NOT Do

- Does not modify Docker's internal DNS
- Does not provide reverse DNS lookups
- Does not handle non-running containers
- Does not manage DNS servers or external DNS zones
- Does not provide SSL/TLS certificates for FQDNs
