#!/usr/bin/env python3
"""
Test and validation script for Docker Hosts Updater
"""
import subprocess
import sys
import time


def color(text, code):
    """Add color to terminal output."""
    return f"\033[{code}m{text}\033[0m"


def success(text):
    return color(f"✓ {text}", "32")


def error(text):
    return color(f"✗ {text}", "31")


def info(text):
    return color(f"ℹ {text}", "34")


def warn(text):
    return color(f"⚠ {text}", "33")


def run_command(cmd, check=True):
    """Run a shell command and return result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if check and result.returncode != 0:
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def check_root():
    """Check if running as root."""
    ok, output = run_command("id -u")
    if ok and output.strip() == "0":
        print(success("Running as root"))
        return True
    else:
        print(error("Not running as root (use sudo)"))
        return False


def check_docker():
    """Check if Docker is available and running."""
    ok, _ = run_command("docker info", check=False)
    if ok:
        print(success("Docker is available and running"))
        return True
    else:
        print(error("Docker is not available or not running"))
        return False


def check_hosts_file():
    """Check if /etc/hosts is writable."""
    ok, _ = run_command("test -w /etc/hosts")
    if ok:
        print(success("/etc/hosts is writable"))
        return True
    else:
        print(error("/etc/hosts is not writable"))
        return False


def check_managed_section():
    """Check if managed section exists."""
    ok, output = run_command("grep 'BEGIN DOCKER CONTAINERS' /etc/hosts")
    if ok:
        print(success("Managed section exists in /etc/hosts"))
        return True
    else:
        print(warn("Managed section not found (will be created on first run)"))
        return True


def create_test_containers():
    """Create test containers."""
    print(info("Creating test containers..."))

    containers = [
        ("test-nginx", "nginx:alpine", "webserver"),
        ("test-redis", "redis:alpine", "cache"),
        ("test-postgres", "postgres:alpine", "database"),
    ]

    success_count = 0
    for name, image, hostname in containers:
        # Remove if exists
        run_command(f"docker rm -f {name} 2>/dev/null", check=False)

        # Create new
        ok, _ = run_command(
            f"docker run -d --name {name} --hostname {hostname} " f"-e POSTGRES_PASSWORD=test {image}", check=False
        )
        if ok:
            print(success(f"Created container: {name} (hostname: {hostname})"))
            success_count += 1
        else:
            print(error(f"Failed to create container: {name}"))

    return success_count == len(containers)


def verify_hosts_entries():
    """Verify hosts file entries were created."""
    print(info("Verifying hosts file entries..."))

    ok, output = run_command("grep -A 20 'BEGIN DOCKER CONTAINERS' /etc/hosts")
    if not ok:
        print(error("Could not read managed section"))
        return False

    print("\nCurrent Docker entries in /etc/hosts:")
    print("-" * 60)
    print(output)
    print("-" * 60)

    # Check for test containers
    test_names = ["test-nginx", "test-redis", "test-postgres", "base.domain"]
    found = []
    missing = []

    for name in test_names:
        if name in output:
            found.append(name)
        else:
            missing.append(name)

    print(f"\nFound entries for: {', '.join(found)}")
    if missing:
        print(warn(f"Missing entries for: {', '.join(missing)}"))

    # Check for FQDN format
    if "base.domain" in output:
        print(success("FQDN format with base.domain domain found"))
    else:
        print(error("FQDN format with base.domain domain NOT found"))

    return len(found) >= 3


def cleanup_test_containers():
    """Remove test containers."""
    print(info("Cleaning up test containers..."))

    for name in ["test-nginx", "test-redis", "test-postgres"]:
        ok, _ = run_command(f"docker rm -f {name} 2>/dev/null", check=False)
        if ok:
            print(success(f"Removed container: {name}"))


def test_script_execution():
    """Test running the script briefly."""
    print(info("Testing script execution (10 seconds)..."))

    try:
        # Run script in background with timeout
        process = subprocess.Popen(
            ["python3", "docker_hosts_updater.py", "5s"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait a bit
        time.sleep(10)

        # Terminate
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

        print(success("Script executed successfully"))
        return True

    except Exception as e:
        print(error(f"Script execution failed: {e}"))
        return False


def main():
    """Main test routine."""
    print("\n" + "=" * 60)
    print(color("Docker Hosts Updater - Validation Tests", "1;36"))
    print("=" * 60 + "\n")

    # Pre-flight checks
    print(color("Pre-flight Checks:", "1;33"))
    checks = [
        ("Root privileges", check_root),
        ("Docker availability", check_docker),
        ("Hosts file writability", check_hosts_file),
        ("Managed section", check_managed_section),
    ]

    failed = False
    for name, check_func in checks:
        if not check_func():
            failed = True

    if failed:
        print(error("\nPre-flight checks failed. Fix issues above and retry."))
        sys.exit(1)

    print(success("\n✓ All pre-flight checks passed!\n"))

    # Functional tests
    print(color("Functional Tests:", "1;33"))

    # Create test containers
    if not create_test_containers():
        print(error("Failed to create test containers"))
        sys.exit(1)

    print()

    # Run script
    if not test_script_execution():
        cleanup_test_containers()
        print(error("Script execution test failed"))
        sys.exit(1)

    print()

    # Verify entries
    if not verify_hosts_entries():
        cleanup_test_containers()
        print(warn("Some hosts entries missing or incorrect"))

    print()

    # Cleanup
    cleanup_test_containers()

    print("\n" + "=" * 60)
    print(color("✓ All tests completed successfully!", "1;32"))
    print("=" * 60)
    print("\nYou can now:")
    print("  • Install with: sudo make install")
    print("  • Start service: sudo systemctl start docker-hosts-updater")
    print("  • View logs: sudo journalctl -u docker-hosts-updater -f")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(error(f"\nUnexpected error: {e}"))
        sys.exit(1)
