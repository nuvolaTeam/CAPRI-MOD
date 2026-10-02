FROM python:3.11-slim

LABEL org.opencontainers.image.title="CAPRI-MOD"
LABEL org.opencontainers.image.description="Python implementation of the CAPRI agricultural economic model"
LABEL org.opencontainers.image.source="https://github.com/nuvolaTeam/CAPRI-MOD"

# Avoid Python writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries required by scientific Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition first to maximise Docker layer caching
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy CAPRI-MOD source code and model data
COPY . .

# Make the CAPRI-MOD package importable
ENV PYTHONPATH=/app

# Default working directory
WORKDIR /app

# Basic import test during image creation
RUN python -c "import capri_mod; print('CAPRI-MOD environment OK')"

# Start an interactive shell by default.
# Users can run the model, notebooks, tests, etc. from inside the container.
CMD ["bash"]