.PHONY: help install uninstall start stop restart status logs test clean dev-setup

SCRIPT_NAME = docker_hosts_updater.py
SERVICE_NAME = docker-hosts-updater
INSTALL_DIR = /usr/local/bin
SERVICE_DIR = /etc/systemd/system

help:
	@echo "Docker Hosts File Updater - Management Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev-setup        Install development dependencies and pre-commit hooks"
	@echo "  make pre-commit       Run pre-commit on all files"
	@echo "  make lint             Run linting checks (black, isort, flake8, pylint)"
	@echo "  make format           Auto-format code with black and isort"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install script and systemd service"
	@echo "  make uninstall        Remove script and systemd service"
	@echo ""
	@echo "Service Management:"
	@echo "  make start            Start the service"
	@echo "  make stop             Stop the service"
	@echo "  make restart          Restart the service"
	@echo "  make status           Show service status"
	@echo "  make logs             Follow service logs"
	@echo ""
	@echo "Docker Compose:"
	@echo "  make docker-up        Start with Docker Compose"
	@echo "  make docker-down      Stop Docker Compose"
	@echo "  make docker-logs      View Docker Compose logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run the script in test mode (30s interval)"
	@echo "  make test-containers  Create test containers"
	@echo "  make verify           Verify hosts file entries"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Clean managed section from /etc/hosts"
	@echo "  make backup           Backup current /etc/hosts"

dev-setup:
	@echo "Setting up development environment..."
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "✓ Development environment ready!"
	@echo "  - Pre-commit hooks installed"
	@echo "  - Run 'make format' to auto-format code"
	@echo "  - Run 'make lint' to check code quality"

pre-commit:
	pre-commit run --all-files

format:
	@echo "Formatting code..."
	black --line-length 120 *.py
	isort --profile black --line-length 120 *.py
	@echo "✓ Code formatted"

lint:
	@echo "Running linting checks..."
	@echo "=== Black ===" && black --check --line-length 120 *.py || true
	@echo ""
	@echo "=== isort ===" && isort --check --profile black --line-length 120 *.py || true
	@echo ""
	@echo "=== flake8 ===" && flake8 --max-line-length=120 --extend-ignore=E203,W503 *.py || true
	@echo ""
	@echo "=== pylint ===" && pylint --max-line-length=120 *.py || true
	@echo ""
	@echo "=== mypy ===" && mypy --ignore-missing-imports *.py || true

install:
	@echo "Installing Docker Hosts Updater..."
	sudo cp $(SCRIPT_NAME) $(INSTALL_DIR)/
	sudo chmod +x $(INSTALL_DIR)/$(SCRIPT_NAME)
	sudo cp $(SERVICE_NAME).service $(SERVICE_DIR)/
	sudo systemctl daemon-reload
	sudo systemctl enable $(SERVICE_NAME)
	@echo "Installation complete. Run 'make start' to start the service."

uninstall:
	@echo "Uninstalling Docker Hosts Updater..."
	-sudo systemctl stop $(SERVICE_NAME)
	-sudo systemctl disable $(SERVICE_NAME)
	sudo rm -f $(SERVICE_DIR)/$(SERVICE_NAME).service
	sudo rm -f $(INSTALL_DIR)/$(SCRIPT_NAME)
	sudo systemctl daemon-reload
	@echo "Uninstallation complete."

start:
	sudo systemctl start $(SERVICE_NAME)
	@sleep 2
	@make status

stop:
	sudo systemctl stop $(SERVICE_NAME)

restart:
	sudo systemctl restart $(SERVICE_NAME)
	@sleep 2
	@make status

status:
	sudo systemctl status $(SERVICE_NAME) --no-pager -l

logs:
	sudo journalctl -u $(SERVICE_NAME) -f

docker-up:
	docker-compose up -d
	@sleep 2
	docker-compose logs

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

test:
	@echo "Running in test mode (Ctrl+C to stop)..."
	sudo python3 $(SCRIPT_NAME) 30s

test-containers:
	@echo "Creating test containers..."
	docker run -d --name test-nginx --hostname webserver --network bridge nginx:alpine
	docker run -d --name test-redis --hostname cache --network bridge redis:alpine
	docker run -d --name test-postgres --hostname db --network bridge postgres:alpine -e POSTGRES_PASSWORD=test
	@echo "Test containers created. Check /etc/hosts for entries."
	@sleep 3
	@make verify

verify:
	@echo "=== Current Docker Hosts Entries ==="
	@sudo grep -A 20 "BEGIN DOCKER CONTAINERS" /etc/hosts || echo "No managed section found"
	@echo ""
	@echo "=== Running Containers ==="
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

clean:
	@echo "Cleaning managed section from /etc/hosts..."
	@sudo sed -i '/^# BEGIN DOCKER CONTAINERS$$/,/^# END DOCKER CONTAINERS$$/d' /etc/hosts
	@echo "Managed section removed. Rerun the script to recreate it."

backup:
	@echo "Backing up /etc/hosts..."
	sudo cp /etc/hosts /etc/hosts.backup.$$(date +%Y%m%d_%H%M%S)
	@echo "Backup created: /etc/hosts.backup.$$(date +%Y%m%d_%H%M%S)"

check-docker:
	@echo "Checking Docker installation..."
	@docker info > /dev/null 2>&1 && echo "✓ Docker is running" || echo "✗ Docker is not available"
	@docker ps > /dev/null 2>&1 && echo "✓ Can access Docker socket" || echo "✗ Cannot access Docker socket (permission issue?)"

check-perms:
	@echo "Checking permissions..."
	@[ "$$(id -u)" = "0" ] && echo "✓ Running as root" || echo "✗ Not running as root (use sudo)"
	@test -w /etc/hosts && echo "✓ Can write to /etc/hosts" || echo "✗ Cannot write to /etc/hosts"

preflight: check-docker check-perms
	@echo ""
	@echo "Preflight checks complete. Ready to install."
