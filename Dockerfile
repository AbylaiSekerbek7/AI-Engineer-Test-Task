FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY src /app/src
COPY mcp_servers /app/mcp_servers
COPY scripts /app/scripts

# (Optional) create data dir inside image (volume will override if mounted)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "ai_mcp_agent.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
