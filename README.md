# Video Downloader

Video indirme uygulaması - YouTube ve nsosyal.com destekli

## Kurulum

```bash
# Virtual environment oluştur (ilk kez oluşturursun - eğer venv varsa atla)
python -m venv venv

# Virtual environment aktifleştir (mac/linux için)
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Playwright tarayıcılarını yükle
playwright install
# Eğer sadece chromium kullanırsan
playwright install chromium


# Sistem bağımlılıkları (isteğe bağlı)
sudo apt install ffmpeg
```

## Güvenlik Ayarları

**ÖNEMLİ:** Production ortamında güvenlik için environment variable'ları kullanın:

```bash
# .env dosyası oluştur
cp .env.example .env

# .env dosyasını düzenle ve güvenli şifreler kullan
nano .env
```

**Environment Variables:**
- `ADMIN_USERNAME`: Admin paneli kullanıcı adı
- `ADMIN_PASSWORD`: Admin paneli şifresi (güçlü şifre kullanın!)
- `FLASK_SECRET_KEY`: Flask secret key (rastgele string kullanın)

**Production İçin Güvenlik Önerileri:**
1. `.env` dosyasını asla GitHub'a push etmeyin (.gitignore'da var)
2. Güçlü şifreler kullanın
3. Docker/Dokploy'da environment variable'ları güvenli şekilde ayarlayın

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

