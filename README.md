# Docker Hosts File Updater

Automatically updates your Docker host's `/etc/hosts` file with running container hostnames and IPs, including FQDNs
using `base.domain` as the domain base.

## Features

- ✅ **Real-time monitoring**: Watches Docker events (start, stop, connect, disconnect, etc.)
- ✅ **Periodic updates**: Fallback periodic sync to catch any missed events
- ✅ **FQDN support**: Creates entries like `container.base.domain`
- ✅ **Multi-network support**: Handles containers connected to multiple networks
- ✅ **Thread-safe**: Uses asyncio locks to prevent race conditions
- ✅ **Graceful shutdown**: Handles SIGTERM and SIGINT properly
- ✅ **Comprehensive logging**: Detailed logging with proper log levels
- ✅ **Error handling**: Robust error handling throughout

## Requirements

- Python 3.12+
- Docker installed and running
- Root/sudo access (to modify `/etc/hosts`)

## Installation

```bash
# Make the script executable
chmod +x docker_hosts_updater.py

# Install as a system service (recommended)
sudo cp docker_hosts_updater.py /usr/local/bin/
sudo cp docker-hosts-updater.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable docker-hosts-updater
sudo systemctl start docker-hosts-updater
```

## Usage

### Command Line

```bash
# Update every 30 seconds (default domain: base.domain)
sudo python docker_hosts_updater.py 30s

# Update every 5 minutes with custom domain
sudo python docker_hosts_updater.py 5m --domain example.com

# Update every 1 hour with custom domain (short form)
sudo python docker_hosts_updater.py 1h -d local.dev

# Show help
python docker_hosts_updater.py --help
```

### Time Interval Format

- `s` - seconds (e.g., `30s`)
- `m` - minutes (e.g., `5m`)
- `h` - hours (e.g., `1h`)
- `d` - days (e.g., `1d`)

### Domain Configuration

You can configure the base domain for FQDNs in three ways (in order of priority):

1. **Command line argument**: `--domain` or `-d`

   ```bash
   sudo python docker_hosts_updater.py 30s --domain example.com
   ```

2. **Environment variable**: `DOCKER_HOSTS_DOMAIN`

   ```bash
   export DOCKER_HOSTS_DOMAIN=example.com
   sudo -E python docker_hosts_updater.py 30s
   ```

3. **Default**: `base.domain` (if neither above is specified)

## How It Works

### Hosts File Format

The script manages a dedicated section in `/etc/hosts`:

```text
# BEGIN DOCKER CONTAINERS
172.18.0.2 nginx nginx.base.domain web web.base.domain
172.18.0.3 postgres postgres.base.domain db db.base.domain
172.18.0.4 redis redis.base.domain cache cache.base.domain
# END DOCKER CONTAINERS
```

### Container Name Resolution

For each running container, the script adds entries for:

1. **Container name**: The Docker container name
2. **Hostname**: The container's configured hostname (if different)
3. **Network aliases**: Any aliases defined in the network configuration
4. **FQDNs**: All of the above with `.base.domain` appended

### Example

Container configuration:

```yaml
services:
  web:
    image: nginx
    hostname: webserver
    networks:
      frontend:
        aliases:
          - nginx
          - www
```

Resulting `/etc/hosts` entries:

```text
172.18.0.2 web web.base.domain webserver webserver.base.domain nginx nginx.base.domain www www.base.domain
```

## Systemd Service

Create `/etc/systemd/system/docker-hosts-updater.service`:

```ini
[Unit]
Description=Docker Hosts File Updater
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/docker_hosts_updater.py 30s
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Service management:

```bash
# Start the service
sudo systemctl start docker-hosts-updater

# Check status
sudo systemctl status docker-hosts-updater

# View logs
sudo journalctl -u docker-hosts-updater -f

# Stop the service
sudo systemctl stop docker-hosts-updater
```

## Docker Container Usage

Pre-built container images are available at `ghcr.io/newdave/docker-hostsfile`.

### Quick Start with Docker Run

```bash
# Using default settings (30s interval, base.domain)
docker run -d \
  --name docker-hosts-updater \
  --network host \
  --cap-add NET_ADMIN \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/hosts:/etc/hosts \
  ghcr.io/newdave/docker-hostsfile:latest

# With custom interval and domain
docker run -d \
  --name docker-hosts-updater \
  --network host \
  --cap-add NET_ADMIN \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/hosts:/etc/hosts \
  ghcr.io/newdave/docker-hostsfile:latest 5m --domain example.com

# Using environment variable for domain
docker run -d \
  --name docker-hosts-updater \
  --network host \
  --cap-add NET_ADMIN \
  -e DOCKER_HOSTS_DOMAIN=local.dev \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/hosts:/etc/hosts \
  ghcr.io/newdave/docker-hostsfile:latest 1h
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  hosts-updater:
    image: ghcr.io/newdave/docker-hostsfile:latest
    container_name: docker-hosts-updater
    restart: unless-stopped
    network_mode: host
    command: ["30s", "--domain", "base.domain"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/hosts:/etc/hosts
    cap_add:
      - NET_ADMIN
    environment:
      - PYTHONUNBUFFERED=1
      - DOCKER_HOSTS_DOMAIN=base.domain
    mem_limit: 256m
    cpus: 0.5
```

See `docker-compose.example.yml` for more configuration examples.

### Available Image Tags

- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `v1.0.0` - Specific version (semver)
- `1.0` - Major.minor version
- `1` - Major version
- `main-<sha>` - Specific commit SHA

**Requirements**:

- Access to Docker socket (read-only recommended)
- Mount `/etc/hosts` from host
- `NET_ADMIN` capability or run as privileged
- Host network mode recommended

## Configuration

### Change the Domain Base

Edit the script and modify:

```python
DOMAIN_BASE = 'base.domain'  # Change to your desired domain
```

### Customize Monitored Events

Edit the `monitor_docker_events()` function:

```python
events_to_monitor = [
    'start', 'stop', 'die', 'kill',
    'pause', 'unpause',
    'connect', 'disconnect'
]
```

## Troubleshooting

### Permission Denied

The script needs root privileges to modify `/etc/hosts`:

```bash
sudo python docker_hosts_updater.py 30s
```

### Docker Not Available

Check Docker is running:

```bash
docker info
```

### No Entries Added

Check that containers have:

- Network connections with valid IPs
- At least one of: container name, hostname, or network alias

Debug by checking logs:

```bash
# When running as systemd service
sudo journalctl -u docker-hosts-updater -f

# When running manually (set DEBUG level)
# Edit script and change: level=logging.DEBUG
```

### Duplicate Entries

The script automatically deduplicates entries per IP address. If you see duplicates:

1. Stop the script
2. Manually remove duplicates from `/etc/hosts`
3. Ensure only one instance of the script is running

### Test Container Setup

```bash
# Create test containers
docker run -d --name test-nginx --hostname webserver nginx
docker run -d --name test-redis --hostname cache redis

# Check /etc/hosts
grep -A 10 "BEGIN DOCKER CONTAINERS" /etc/hosts

# Should show:
# 172.17.0.2 test-nginx test-nginx.base.domain webserver webserver.base.domain
# 172.17.0.3 test-redis test-redis.base.domain cache cache.base.domain
```

## Key Improvements Over Original

1. **FQDN Support**: Uses `base.domain` domain base as requested
2. **Better Event Monitoring**: Monitors all relevant Docker events (start, stop, die, kill, pause, unpause, connect, disconnect)
3. **Enhanced Error Handling**: Comprehensive try/except blocks with proper logging
4. **Thread Safety**: Uses asyncio locks to prevent concurrent writes
5. **Initial Update**: Updates hosts file immediately on startup
6. **Signal Handling**: Properly handles both SIGTERM and SIGINT
7. **Docker Validation**: Checks Docker availability before starting
8. **Better Logging**: Uses Python logging module with timestamps and levels
9. **Multi-Network Support**: Correctly handles containers on multiple networks
10. **Container Names**: Uses actual container names and hostnames, not just aliases
11. **JSON Event Parsing**: Properly parses Docker events as JSON
12. **Security**: Avoids `shell=True` where possible
13. **Deduplication**: Ensures no duplicate entries per IP
14. **Type Hints**: Added type hints for better code clarity
15. **Documentation**: Comprehensive docstrings and comments

## Platform/DevOps Integration

### GitHub Actions Example

```yaml
name: Deploy Hosts Updater

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            sudo systemctl stop docker-hosts-updater
            sudo cp docker_hosts_updater.py /usr/local/bin/
            sudo systemctl start docker-hosts-updater
            sudo systemctl status docker-hosts-updater
```

### Monitoring with Prometheus

Export metrics from logs using a sidecar pattern or integrate with:

- Prometheus node_exporter
- Vector.dev for log aggregation
- Grafana Loki for log monitoring

## License

MIT

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Developers

```bash
# Set up development environment
make dev-setup

# Format code
make format

# Run linting
make lint

# Run pre-commit checks
make pre-commit
```

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality:

- **Python**: black, isort, flake8, pylint, mypy, bandit
- **Docker**: hadolint for Dockerfile linting
- **GitHub Actions**: actionlint for workflow validation
- **Markdown**: markdownlint
- **Shell**: shellcheck

Hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

Please ensure:

- Code follows PEP 8 style guidelines (120 char line length)
- All functions have type hints and docstrings
- Error handling is comprehensive
- Changes are tested with multiple Docker network configurations
