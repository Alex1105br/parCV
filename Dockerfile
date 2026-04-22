FROM ubuntu:24.04

# Dependências base + pdftotext para converter PDFs
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    poppler-utils \
    && pip3 install requests flask --break-system-packages \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["python3", "src/app.py"]