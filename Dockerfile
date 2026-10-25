FROM python:3.15-alpine@sha256:d44b1254cb92329418d164b22b20d86bbd3869d48e80e09e476531a409a728bb

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -S freely && adduser -S -G freely freely

COPY pip-bootstrap.txt requirements.lock ./
COPY app ./app
RUN pip install --no-cache-dir --require-hashes -r pip-bootstrap.txt \
    && pip install --no-cache-dir --require-hashes -r requirements.lock

USER freely

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
