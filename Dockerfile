# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS ui
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY docs/UI_LOCALIZATION_STYLE.md /build/docs/UI_LOCALIZATION_STYLE.md
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/data FRONTEND_DIST=/app/frontend/dist CHARACTER_IMAGE_DIR=/app/image DEMO_AUTH_ENABLED=false CHAT_TRANSPORT=direct GROUP_ROUTER_MODE=local ROLEPLAY_MUSIC_DIR=/media/music
WORKDIR /app
COPY pyproject.toml ./
COPY character_chat/ ./character_chat/
RUN pip install --no-cache-dir ".[modal]"
COPY --from=ui /build/frontend/dist ./frontend/dist/
COPY image/ ./image/
COPY sound_effect/ ./sound_effect/
COPY docs/UI_LOCALIZATION_STYLE.md ./docs/UI_LOCALIZATION_STYLE.md
COPY scripts/service_entrypoint.py scripts/service_data.py ./scripts/
RUN useradd --uid 10001 --create-home companion && mkdir -p /data /media/music && chown companion:companion /data
USER companion
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4)"
CMD ["python", "scripts/service_entrypoint.py"]
