FROM python:3.12-slim

WORKDIR /app

# Build deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install runtime deps (+ ruff, used by xsdata to format generated code)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e . ruff

COPY adapter/   ./adapter/
COPY sources/   ./sources/
COPY outputs/   ./outputs/
COPY api/       ./api/
COPY profiles/  ./profiles/
COPY data/      ./data/
COPY schemas/   ./schemas/
COPY scripts/   ./scripts/
COPY static/    ./static/

# Generate the DATEX II dataclasses from the committed XSDs (generated/ is gitignored)
RUN python scripts/generate_dataclasses.py

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
