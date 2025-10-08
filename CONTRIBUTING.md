# Contributing to Docker Hosts File Updater

Thank you for your interest in contributing! This document provides guidelines and setup instructions.

## Development Setup

### Prerequisites

- Python 3.12+
- Docker
- pip

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd docker-hostsfile

# Set up development environment (installs dependencies and pre-commit hooks)
make dev-setup
```

This will:

- Install all development dependencies from `requirements-dev.txt`
- Set up pre-commit hooks
- Configure linting and formatting tools

## Code Quality

### Pre-commit Hooks

Pre-commit hooks automatically run before each commit to ensure code quality:

```bash
# Manually run pre-commit on all files
make pre-commit

# Or directly
pre-commit run --all-files

# Run on specific files only
pre-commit run --files docker_hosts_updater.py
```

### Formatting

Auto-format your code with:

```bash
make format
```

This runs:

- **Black**: Opinionated Python code formatter (120 char line length)
- **isort**: Import statement organizer

### Linting

Check code quality with:

```bash
make lint
```

This runs:

- **Black**: Check formatting
- **isort**: Check import order
- **flake8**: Style guide enforcement
- **pylint**: Static code analysis
- **mypy**: Type checking

## Pre-commit Hook Configuration

The following checks run automatically on commit:

### General Checks

- Trailing whitespace removal
- End-of-file fixer
- YAML syntax validation
- Large file prevention
- Merge conflict detection

### Python

- **black**: Code formatting (120 char lines)
- **isort**: Import sorting
- **flake8**: Linting (max complexity: 15)
- **pylint**: Static analysis
- **mypy**: Type checking
- **bandit**: Security linting

### Docker

- **hadolint**: Dockerfile linting

### GitHub Actions

- **actionlint**: Workflow file validation

### Markdown

- **markdownlint**: Markdown formatting

### Shell

- **shellcheck**: Shell script linting

## Making Changes

### Workflow

1. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Format and lint:

   ```bash
   make format
   make lint
   ```

4. Run tests:

   ```bash
   make test
   # Or run the test suite
   python -m pytest
   ```

5. Commit (pre-commit hooks run automatically):

   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. Push and create a pull request:

   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Guidelines

- Use clear, descriptive commit messages
- Start with a verb in imperative mood (e.g., "Add", "Fix", "Update")
- Keep the first line under 72 characters
- Add detailed explanation in the body if needed

Example:

```
Add support for custom domain configuration

- Allow domain base to be set via CLI argument
- Add environment variable fallback
- Update documentation with examples
```

## Testing

### Manual Testing

```bash
# Test script directly (30 second interval)
sudo python3 docker_hosts_updater.py 30s

# Create test containers
make test-containers

# Verify entries in /etc/hosts
make verify
```

### Unit Tests

```bash
# Run pytest
python -m pytest

# With coverage
python -m pytest --cov=docker_hosts_updater --cov-report=html
```

## Troubleshooting Pre-commit

### Skip Hooks (Not Recommended)

If you need to skip pre-commit hooks temporarily:

```bash
git commit --no-verify -m "Your message"
```

### Update Pre-commit Hooks

```bash
pre-commit autoupdate
```

### Clear Cache

If hooks are misbehaving:

```bash
pre-commit clean
pre-commit install --install-hooks
```

## Code Style Guidelines

### Python Style

- Line length: 120 characters
- Use type hints where practical
- Follow PEP 8
- Use meaningful variable names
- Add docstrings for functions and classes
- Keep functions focused (single responsibility)

### Example

```python
def parse_time_interval(interval_str: str) -> int:
    """
    Parse time interval string to seconds.

    Args:
        interval_str: Time interval like '30s', '5m', '1h'

    Returns:
        Number of seconds as integer

    Raises:
        ValueError: If format is invalid
    """
    # Implementation...
```

## Questions or Issues?

- Check existing issues on GitHub
- Open a new issue with detailed description
- Join the discussion in pull requests

Thank you for contributing!
