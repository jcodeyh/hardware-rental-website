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

# Port 8000 matches client/vite.config.js's proxy target and authService.js's baseUrl.
# No --reload here: the file watcher it starts is useless once the image is
# immutable (as it is in Azure) and only adds work to every cold start.
# docker-compose adds it back for local dev, where the source is bind-mounted
# over this copy and picking up edits is the whole point.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
