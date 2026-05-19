FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    poppler-utils \
    fonts-liberation \
    && pip3 install requests flask reportlab --break-system-packages \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

ENV PYTHONPATH=/workspace

CMD ["python3", "-m", "src.app"]