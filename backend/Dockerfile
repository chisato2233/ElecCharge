# backend/Dockerfile
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["gunicorn", "ev_charge.wsgi:application", "--bind", "0.0.0.0:8000"]
