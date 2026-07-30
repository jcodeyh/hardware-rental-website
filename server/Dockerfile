FROM python:3.12-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install pip requirements first so this layer is cached unless
# requirements.txt itself changes (avoids reinstalling on every code edit)
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload watches for file changes, which matters because docker-compose
# bind-mounts the source over this copy for local dev.
# Port 8000 matches client/vite.config.js's proxy target and authService.js's baseUrl.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--reload", "app:app"]
