FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
COPY frontend/postcss.config.js ./
COPY frontend/tailwind.config.js ./
COPY frontend/vite.config.js ./
COPY frontend/index.html ./
COPY frontend/src ./src

RUN npm install
RUN mkdir -p /app/static
RUN npm run build

FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --group dev

COPY . .
COPY --from=frontend-builder /app/static/demo_app ./app/static/demo_app

EXPOSE 8000

CMD ["sh", "./scripts/start-backend.sh"]
