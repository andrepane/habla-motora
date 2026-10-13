FROM --platform=linux/amd64 python:3.12.14-slim-bookworm
ARG PRAAT_VERSION=6.4.27
ARG PRAAT_ARCHIVE_SHA256=6f60fba398f7490881a569b874a1c66ca026e1f748946d50a6017941c4137f7e
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN test "$PRAAT_VERSION" = "6.4.27" \
    && curl -fL "https://github.com/praat/praat.github.io/releases/download/v${PRAAT_VERSION}/praat6427_linux-intel64-barren.tar.gz" -o /tmp/praat.tar.gz \
    && echo "$PRAAT_ARCHIVE_SHA256  /tmp/praat.tar.gz" | sha256sum -c - \
    && tar --no-same-owner -xzf /tmp/praat.tar.gz -C /usr/local/bin praat_barren \
    && mv /usr/local/bin/praat_barren /usr/local/bin/praat \
    && rm /tmp/praat.tar.gz \
    && praat --version
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation -e . \
    && useradd --create-home --uid 10001 app
USER app
ENV PRAAT_EXECUTABLE=/usr/local/bin/praat
RUN python -m pytest -q
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
