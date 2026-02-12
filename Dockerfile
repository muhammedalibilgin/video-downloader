FROM python:3.12-slim

# Gerekli sistem araçlarını yükle
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Playwright bağımlılıkları
RUN apt-get update && apt-get install -y \
    libgstreamer-plugins-bad1.0-0 \
    libavif16 \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright tarayıcılarını yükle
RUN playwright install chromium
RUN playwright install-deps

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]