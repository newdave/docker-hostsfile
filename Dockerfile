FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/newdave/docker-hostsfile
LABEL org.opencontainers.image.description="Automatically updates /etc/hosts with Docker container IPs and FQDNs"
LABEL org.opencontainers.image.licenses=MIT

# Install Docker CLI from official Docker repository
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy the updater script
COPY src/docker_hosts_updater.py /app/

# Make script executable
RUN chmod +x /app/docker_hosts_updater.py

# Set Python to unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
ENTRYPOINT ["python3", "/app/docker_hosts_updater.py"]
CMD ["30s"]
