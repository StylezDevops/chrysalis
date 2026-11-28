FROM python:3.12-alpine@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
WORKDIR /app
COPY --chown=10101:10101 . /app
USER 10101
HEALTHCHECK CMD wget -qO- http://localhost:8080/ || exit 1
CMD ["python", "-m", "http.server", "8080"]
