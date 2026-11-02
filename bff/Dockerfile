
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ ./proto/

RUN python -m grpc_tools.protoc \
    -I . \
    --python_out=. \
    --grpc_python_out=. \
    proto/projects.proto proto/hardware.proto

COPY app/ ./app/

RUN useradd --create-home appuser
USER appuser

EXPOSE 50051

CMD ["python", "-m", "app.grpc_server"]
