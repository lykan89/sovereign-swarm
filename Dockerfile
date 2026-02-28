# STAGE 1: The Armory (Added Chaos & Dnsx)
FROM golang:1.24-bookworm AS armory
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v github.com/ffuf/ffuf/v2@latest && \
    # NEW: Chaos client for rapid subdomain Intel
    go install -v github.com/projectdiscovery/chaos-client/cmd/chaos@latest

# STAGE 2: The Main Runner (Python 3.12)
FROM python:3.12-slim-bookworm
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl libpcap-dev sqlmap ca-certificates python3.10 python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# Setup Isolated VulnHuntr (Python 3.10)
RUN python3.10 -m venv /opt/vulnhuntr_env && \
    /opt/vulnhuntr_env/bin/pip install --no-cache-dir git+https://github.com/protectai/vulnhuntr.git

# Install Main Swarm Logic (Includes Shodan, Censys, GreyNoise)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Go binaries from Stage 1 (Now includes 'chaos')
COPY --from=armory /go/bin/* /usr/local/bin/

COPY . .
VOLUME ["/app/results"]
CMD ["python3", "main.py"]