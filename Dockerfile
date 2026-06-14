FROM python:3.11-slim

WORKDIR /app

# Install build deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY adapter/   ./adapter/
COPY sources/   ./sources/
COPY outputs/   ./outputs/
COPY api/       ./api/
COPY profiles/  ./profiles/
COPY data/      ./data/
COPY schemas/   ./schemas/
COPY generated/ ./generated/

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
