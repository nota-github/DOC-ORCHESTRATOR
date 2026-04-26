FROM python:3.11-slim

WORKDIR /app

# Install System Packages
RUN apt update && apt install -y \
    git \
    curl \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv (MCP 서버용)
RUN pip install --no-cache-dir uv

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]

