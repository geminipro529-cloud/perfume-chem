FROM python:3.11-slim AS builder

ENV POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# The backend has an editable path dependency on the root engine package.
COPY pyproject.toml ./pyproject.toml
COPY engine ./engine
COPY data ./data
COPY backend/pyproject.toml backend/poetry.lock ./backend/

WORKDIR /app/backend
RUN poetry install --only main --no-root --no-ansi


FROM python:3.11-slim AS runtime

ENV PATH="/app/backend/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

COPY --from=builder /app/backend/.venv /app/backend/.venv
COPY engine /app/engine
COPY data /app/data
COPY backend/app /app/backend/app
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/config /app/backend/config
COPY backend/data /app/backend/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
