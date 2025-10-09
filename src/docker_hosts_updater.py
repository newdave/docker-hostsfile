#!/usr/bin/env python3
"""
Docker Hosts File Updater
Automatically updates /etc/hosts with Docker container hostnames and IPs
"""
import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from signal import SIGINT, SIGTERM
from typing import Dict, List, Set

# Configuration
HOSTS_FILE = "/etc/hosts"
BEGIN_BLOCK = "# BEGIN DOCKER CONTAINERS"
END_BLOCK = "# END DOCKER CONTAINERS"
UPDATE_LOCK = asyncio.Lock()

# Global variable for domain base (set during initialization)
DOMAIN_BASE = "base.domain"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def parse_time_interval(interval_str: str) -> int:
    """Parse time interval string (e.g., '30s', '5m', '1h') to seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    if not interval_str or len(interval_str) < 2:
        raise ValueError("Invalid time interval format. Use format like '30s', '5m', '1h'")

    unit = interval_str[-1].lower()
    if unit not in units:
        raise ValueError(f"Unsupported time unit '{unit}'. Use: s, m, h, d")

    try:
        value = int(interval_str[:-1])
        if value <= 0:
            raise ValueError("Time interval must be positive")
        return value * units[unit]
    except ValueError as e:
        raise ValueError(f"Invalid time interval format: {e}")


def check_docker_available() -> bool:
    """Check if Docker daemon is accessible."""
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Docker not available: {e}")
        return False


def fix_non_breaking_spaces() -> bool:
    """Remove non-breaking spaces from hosts file."""
    try:
        # Use subprocess.run with list instead of shell=True for security
        subprocess.run(["sed", "-i", "s/\\xA0/ /g", HOSTS_FILE], check=True, timeout=10)
        logger.info("Fixed non-breaking spaces in hosts file")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error fixing non-breaking spaces: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error fixing non-breaking spaces: {e}")
        return False


def ensure_managed_section_exists() -> bool:
    """Ensure the managed section markers exist in hosts file."""
    try:
        hosts_path = Path(HOSTS_FILE)
        if not hosts_path.exists():
            logger.error(f"Hosts file {HOSTS_FILE} does not exist")
            return False

        contents = hosts_path.read_text()

        if BEGIN_BLOCK not in contents or END_BLOCK not in contents:
            logger.info(f"Adding managed section markers to {HOSTS_FILE}")
            with hosts_path.open("a") as f:
                f.write(f"\n{BEGIN_BLOCK}\n{END_BLOCK}\n")

        return True
    except PermissionError:
        logger.error(f"Permission denied accessing {HOSTS_FILE}. Run as root?")
        return False
    except Exception as e:
        logger.error(f"Error ensuring managed section exists: {e}")
        return False


def get_docker_container_hosts() -> List[str]:
    """
    Get list of Docker container host entries.
    Returns entries in format: IP hostname hostname.DOMAIN
    """
    try:
        # Get all running containers
        result = subprocess.run(["docker", "container", "ls", "-q"], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            logger.error(f"Failed to list containers: {result.stderr}")
            return []

        container_ids = result.stdout.strip().split()
        if not container_ids:
            logger.info("No running containers found")
            return []

        # Inspect all containers
        result = subprocess.run(
            ["docker", "container", "inspect"] + container_ids, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            logger.error(f"Failed to inspect containers: {result.stderr}")
            return []

        containers = json.loads(result.stdout)
        host_entries = []
        seen_ips: Set[str] = set()

        for container in containers:
            container_name = container.get("Name", "").lstrip("/")
            hostname = container.get("Config", {}).get("Hostname", "")
            networks = container.get("NetworkSettings", {}).get("Networks", {})

            if not networks:
                continue

            # Process each network the container is connected to
            for network_name, network_info in networks.items():
                ip_address = network_info.get("IPAddress", "")
                aliases = network_info.get("Aliases", [])

                if not ip_address or ip_address in seen_ips:
                    continue

                # Collect all hostnames for this IP
                hostnames: List[str] = []

                # Add container name
                if container_name:
                    hostnames.append(container_name)

                # Add hostname if different from container name
                if hostname and hostname != container_name:
                    hostnames.append(hostname)

                # Add network aliases
                if aliases:
                    for alias in aliases:
                        if alias and alias not in hostnames:
                            hostnames.append(alias)

                if hostnames:
                    # Create entry with short names and FQDNs
                    all_names = []
                    for name in hostnames:
                        # Clean the hostname (remove any existing domain)
                        clean_name = name.split(".")[0]
                        all_names.append(clean_name)
                        all_names.append(f"{clean_name}.{DOMAIN_BASE}")

                    # Remove duplicates while preserving order
                    unique_names = []
                    for name in all_names:
                        if name not in unique_names:
                            unique_names.append(name)

                    entry = f"{ip_address} {' '.join(unique_names)}"
                    host_entries.append(entry)
                    seen_ips.add(ip_address)
                    logger.debug(f"Added entry: {entry}")

        return host_entries

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Docker inspect output: {e}")
        return []
    except subprocess.TimeoutExpired:
        logger.error("Docker command timed out")
        return []
    except Exception as e:
        logger.error(f"Error getting container hosts: {e}")
        return []


def update_hosts_file() -> bool:
    """Update the hosts file with current Docker container information."""
    try:
        hosts_path = Path(HOSTS_FILE)

        # Read current hosts file
        lines = hosts_path.read_text().splitlines(keepends=True)

        # Find managed section
        try:
            start_idx = next(i for i, line in enumerate(lines) if line.strip() == BEGIN_BLOCK)
            end_idx = next(i for i, line in enumerate(lines) if line.strip() == END_BLOCK)
        except StopIteration:
            logger.error("Managed section markers not found in hosts file")
            return False

        # Get Docker container entries
        docker_entries = get_docker_container_hosts()

        # Build new hosts file content
        new_lines = (
            lines[: start_idx + 1]
            + [f"{entry}\n" for entry in docker_entries]  # Everything before managed section
            + lines[end_idx:]  # Docker entries  # Everything from end marker onwards
        )

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir="/tmp") as temp_file:
            temp_file.writelines(new_lines)
            temp_path = temp_file.name

        # Set proper permissions and atomically replace
        subprocess.run(["chmod", "644", temp_path], check=True, timeout=5)
        subprocess.run(["mv", temp_path, HOSTS_FILE], check=True, timeout=5)

        logger.info(f"Successfully updated {HOSTS_FILE} with {len(docker_entries)} entries")
        return True

    except PermissionError:
        logger.error(f"Permission denied writing to {HOSTS_FILE}")
        return False
    except Exception as e:
        logger.error(f"Error updating hosts file: {e}")
        # Clean up temp file if it exists
        try:
            if "temp_path" in locals():
                Path(temp_path).unlink(missing_ok=True)
        except:
            pass
        return False


async def update_hosts_file_async() -> bool:
    """Thread-safe async wrapper for updating hosts file."""
    async with UPDATE_LOCK:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, update_hosts_file)
            return result
        except Exception as e:
            logger.error(f"Error in async update: {e}")
            return False


async def periodic_update(interval_seconds: int):
    """Periodically update hosts file at specified interval."""
    logger.info(f"Starting periodic updates every {interval_seconds} seconds")

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            logger.debug("Periodic update triggered")
            await update_hosts_file_async()
        except asyncio.CancelledError:
            logger.info("Periodic update task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic update: {e}")


async def monitor_docker_events():
    """Monitor Docker events and trigger hosts file updates."""
    events_to_monitor = ["start", "stop", "die", "kill", "pause", "unpause", "connect", "disconnect"]

    cmd = ["docker", "events", "--format", "{{json .}}"]
    for event in events_to_monitor:
        cmd.extend(["--filter", f"event={event}"])

    logger.info(f"Starting Docker event monitoring for: {', '.join(events_to_monitor)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        async for line in process.stdout:
            try:
                event_data = json.loads(line.decode("utf-8").strip())
                event_type = event_data.get("status", "unknown")
                container_name = event_data.get("Actor", {}).get("Attributes", {}).get("name", "unknown")

                logger.info(f"Docker event: {event_type} - container: {container_name}")
                await update_hosts_file_async()

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse event: {line.decode('utf-8').strip()}")
            except Exception as e:
                logger.error(f"Error processing event: {e}")

        await process.wait()

    except asyncio.CancelledError:
        logger.info("Docker event monitoring cancelled")
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
    except Exception as e:
        logger.error(f"Error in event monitoring: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Docker Hosts File Updater - Automatically updates /etc/hosts with Docker container information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 30s                           # Update every 30 seconds (default domain: base.domain)
  %(prog)s 5m -d example.com             # Update every 5 minutes with custom domain
  %(prog)s 1h --domain local.dev         # Update every hour with custom domain

Environment Variables:
  DOCKER_HOSTS_DOMAIN    Base domain for FQDNs (e.g., 'example.com')
        """,
    )

    parser.add_argument("interval", help="Update interval (e.g., 30s, 5m, 1h, 1d)")

    parser.add_argument(
        "-d",
        "--domain",
        help='Base domain for FQDNs (default: value from DOCKER_HOSTS_DOMAIN env var or "base.domain")',
        default=None,
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    global DOMAIN_BASE

    # Parse command line arguments
    args = parse_arguments()

    # Determine domain base (priority: CLI arg > env var > default)
    if args.domain:
        DOMAIN_BASE = args.domain.strip()
    elif os.getenv("DOCKER_HOSTS_DOMAIN"):
        DOMAIN_BASE = os.getenv("DOCKER_HOSTS_DOMAIN").strip()
    else:
        DOMAIN_BASE = "base.domain"

    logger.info(f"Using domain base: {DOMAIN_BASE}")

    # Parse interval
    try:
        interval_seconds = parse_time_interval(args.interval)
        logger.info(f"Update interval: {interval_seconds} seconds")
    except ValueError as e:
        logger.error(f"Invalid interval: {e}")
        sys.exit(1)

    # Check Docker availability
    if not check_docker_available():
        logger.error("Docker is not available or not running")
        sys.exit(1)

    # Initialize hosts file
    logger.info("Initializing hosts file management")
    fix_non_breaking_spaces()

    if not ensure_managed_section_exists():
        logger.error("Failed to initialize managed section")
        sys.exit(1)

    # Perform initial update
    logger.info("Performing initial hosts file update")
    await update_hosts_file_async()

    # Setup tasks
    events_task = asyncio.create_task(monitor_docker_events())
    update_task = asyncio.create_task(periodic_update(interval_seconds))

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler(signame):
        logger.info(f"Received {signame}, shutting down gracefully...")
        events_task.cancel()
        update_task.cancel()

    loop.add_signal_handler(SIGTERM, lambda: signal_handler("SIGTERM"))
    loop.add_signal_handler(SIGINT, lambda: signal_handler("SIGINT"))

    # Run both tasks
    try:
        await asyncio.gather(events_task, update_task)
    except asyncio.CancelledError:
        logger.info("Tasks cancelled, cleaning up...")

    logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
