FROM node:22-slim@sha256:de170b39439eb0e5a3444ad7d60b015614a381e10fecae2e30ec9e735122f38d AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
# vite writes to ../src/lugnut/static
RUN npm run build

FROM python:3.13-slim@sha256:b3575dcf816cdacc5292df77a6e3e59b8941631078373a045efa2ac1e9c5c3b2 AS wheel
COPY --from=ghcr.io/astral-sh/uv:0.11.1@sha256:fc93e9ecd7218e9ec8fba117af89348eef8fd2463c50c13347478769aaedd0ce /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml LICENSE README.md ./
COPY src/ src/
COPY --from=frontend /app/src/lugnut/static src/lugnut/static
RUN uv build --wheel --out-dir /dist

FROM python:3.13-slim@sha256:b3575dcf816cdacc5292df77a6e3e59b8941631078373a045efa2ac1e9c5c3b2
RUN useradd --uid 1000 --create-home lugnut && mkdir /data && chown lugnut /data
RUN --mount=type=bind,from=wheel,source=/dist,target=/dist \
    --mount=type=bind,from=wheel,source=/usr/local/bin/uv,target=/usr/local/bin/uv \
    uv pip install --system --no-cache /dist/*.whl
USER 1000
ENV LUGNUT_DATA_DIR=/data LUGNUT_HOST=0.0.0.0
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD ["python", "-c", "import os, urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('LUGNUT_PORT', '8080'), timeout=3)"]
CMD ["lugnut", "serve"]
