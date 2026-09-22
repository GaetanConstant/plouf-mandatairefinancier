# Backend FastAPI — build avec uv, exécution non-root.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv sync --locked --no-dev

FROM python:3.12-slim-bookworm AS production
WORKDIR /app/backend

# WeasyPrint (PDF) veut pango/cairo/harfbuzz ; l'OCR des justificatifs veut
# tesseract (français) et poppler pour convertir les PDF en images.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        fonts-dejavu-core \
        tesseract-ocr \
        tesseract-ocr-fra \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/backend /app/backend
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Les données (bases SQLite, justificatifs, signature) arrivent par un volume.
RUN mkdir -p /app/data && chown -R 1000:1000 /app/data
USER 1000:1000
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
