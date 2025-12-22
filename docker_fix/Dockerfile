FROM agentscope/runtime-sandbox-filesystem:latest

# Fix pydantic version
RUN /agentscope_runtime/venv/bin/pip install "pydantic>=2.10" --quiet

# Fix uvicorn single worker blocking issue
# Use 4 workers to prevent long-running commands from blocking all requests
RUN printf '#!/bin/bash\nuvicorn app:app --app-dir=/agentscope_runtime --host=0.0.0.0 --port 8000 --workers 4 &\nwait\n' \
    > /agentscope_runtime/scripts/start.sh && \
    chmod +x /agentscope_runtime/scripts/start.sh
