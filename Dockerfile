FROM python:3.12-alpine@sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b

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
