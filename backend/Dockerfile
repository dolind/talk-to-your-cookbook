FROM python:3.10-slim

# Set workdir
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Poetry install
RUN pip install --no-cache-dir poetry

# Copy files
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root


COPY backend /app/backend

# Set env vars (override in .env or compose)
ENV PYTHONUNBUFFERED=1

# Expose app port
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
