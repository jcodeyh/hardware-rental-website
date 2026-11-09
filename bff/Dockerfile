FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    GRPC_HOST=127.0.0.1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto/ ./proto/
RUN python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. \
    proto/projects.proto proto/hardware.proto proto/users.proto proto/upstream/hardware.proto
COPY app/ ./app/
RUN useradd --create-home appuser
USER appuser
EXPOSE 8002
CMD ["python", "-m", "app.serve"]
