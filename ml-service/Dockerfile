FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*


RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy poetry files first for better caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev)
RUN poetry install --only main --no-root --no-interaction

# Copy application code
COPY app ./app
COPY model_weights_keys_improved_unet.pth ./model_weights_keys_improved_unet.pth
COPY model_weights_bass_improved_unet.pth ./model_weights_bass_improved_unet.pth

# Expose port
EXPOSE 8000

# Run with poetry
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
