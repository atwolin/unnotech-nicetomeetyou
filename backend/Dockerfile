FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /app/staticfiles && chown -R nonroot:nonroot /app/staticfiles \
    && chown -R nonroot:nonroot /tmp

USER nonroot
ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000
CMD ["uv", "run", "daphne", "config.asgi:application", "--bind", "0.0.0.0", "-p", "8000"]
