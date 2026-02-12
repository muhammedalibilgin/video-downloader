# Video Downloader

Video indirme uygulaması - YouTube ve nsosyal.com destekli

## Kurulum

```bash
# Virtual environment oluştur
python -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Playwright tarayıcılarını yükle
playwright install

# Sistem bağımlılıkları (isteğe bağlı)
sudo apt install ffmpeg
```

## Çalıştırma

```bash
source venv/bin/activate
python app.py
```

Uygulama http://localhost:5001 adresinde çalışır

## Docker ile Deploy

```bash
# Build
docker build -t video-downloader .

# Run
docker run -p 5000:5000 video-downloader
```

## Dokploy Deploy

1. Repoyu GitHub'a push et
2. Dokploy'da yeni proje oluştur
3. GitHub reposunu bağla
4. Otomatik deploy gerçekleşir

**Önemli:** Dokploy'da port 5000 olarak ayarlanmalı

