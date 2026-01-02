FROM agentscope/runtime-sandbox-filesystem:latest

# Install rsync with China mirror fallback
# This is critical for cherry-pick conflict resolution sync operations
RUN apt-get update -qq && apt-get install -y -qq rsync 2>/dev/null || \
    ( \
        echo "Falling back to China mirrors..." && \
        sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true && \
        sed -i 's|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i 's|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true && \
        apt-get update -qq && apt-get install -y -qq rsync \
    ) && \
    rm -rf /var/lib/apt/lists/* && \
    rsync --version | head -1

# Fix pydantic version
RUN /agentscope_runtime/venv/bin/pip install "pydantic>=2.10" --quiet

# Fix uvicorn single worker blocking issue
# Use 4 workers to prevent long-running commands from blocking all requests
RUN printf '#!/bin/bash\nuvicorn app:app --app-dir=/agentscope_runtime --host=0.0.0.0 --port 8000 --workers 4 &\nwait\n' \
    > /agentscope_runtime/scripts/start.sh && \
    chmod +x /agentscope_runtime/scripts/start.sh

# Install Claude Code CLI for in-container code editing
RUN npm install -g @anthropic-ai/claude-code && \
    claude --version

# Prepare for non-root Claude Code execution
# The 'node' user (uid=1000) already exists in the base image
# Ensure /workspace can be written by node user
RUN mkdir -p /workspace && chown -R node:node /workspace && \
    mkdir -p /home/node/.claude && chown -R node:node /home/node/.claude
