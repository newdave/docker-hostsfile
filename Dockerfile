FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/newdave/docker-hostsfile
LABEL org.opencontainers.image.description="Automatically updates /etc/hosts with Docker container IPs and FQDNs"
LABEL org.opencontainers.image.licenses=MIT

# Install Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy the updater script
COPY docker_hosts_updater.py /app/

# Make script executable
RUN chmod +x /app/docker_hosts_updater.py

# Set Python to unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
ENTRYPOINT ["python3", "/app/docker_hosts_updater.py"]
CMD ["30s"]
