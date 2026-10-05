FROM python:3.14-slim@sha256:c3e521df8b2b498a7a682e7e18676771cb80c6b75b8699af886b2d554ce40151

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY attendance/ ./attendance/

RUN useradd --create-home --uid 10001 attendance \
    && mkdir -p /data \
    && chown -R attendance:attendance /data /app
USER attendance

CMD ["python", "-m", "attendance"]
