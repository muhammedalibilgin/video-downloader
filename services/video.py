from playwright.sync_api import sync_playwright
import yt_dlp
import os
import time
from flask import send_file
from config import Config

def get_m3u8_url(web_url):
    """Web sayfasından m3u8 linkini yakala"""
    try:
        with sync_playwright() as p:
            # Arka planda tarayıcıyı başlat
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            m3u8_link = None

            # Network trafiğini dinleyen fonksiyon
            def handle_request(request):
                nonlocal m3u8_link
                if ".m3u8" in request.url:
                    m3u8_link = request.url

            page.on("request", handle_request)
            
            # Sayfaya git ve biraz bekle (videonun yüklenmesi için)
            try:
                page.goto(web_url, wait_until="load", timeout=60000)
            except:
                pass
            
            # Eğer hemen çıkmazsa 5 saniye daha trafiği izle
            timeout = 0
            while not m3u8_link and timeout < 20:
                time.sleep(1)
                timeout += 1
                
            browser.close()
            return m3u8_link
    except Exception as e:
        if "Executable doesn't exist" in str(e) or "playwright install" in str(e) or "doesn't exist at" in str(e):
            raise Exception("Playwright kurulu değil.")
        raise

def get_video_info(url):
    """Video bilgilerini al"""
    # 1. Önce m3u8 linkini yakalamaya çalış
    print(f"Kaynak taranıyor: {url}")
    m3u8_url = get_m3u8_url(url)
    
    # 2. Eğer m3u8 bulunduysa onu, bulunamadıysa orijinal linki kullan
    final_url = m3u8_url if m3u8_url else url
    print(f"Önizleme URL: {final_url}")
    
    # 3. Video bilgilerini al
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(final_url, download=False)
        video_url = info.get('url', final_url)  # Eğer url gelmezse m3u8 linkini kullan
        title = info.get('title', 'Video')
        
    return {
        'video_url': video_url,
        'title': title,
        'original_url': url
    }

def download_video(url):
    """Videoyu indir ve dosya olarak gönder"""
    # 1. Önce m3u8 linkini yakalamaya çalış
    print(f"Kaynak taranıyor: {url}")
    m3u8_url = get_m3u8_url(url)

    # 2. Eğer m3u8 bulunduysa onu, bulunamadıysa orijinal linki kullan
    final_url = m3u8_url if m3u8_url else url
    print(f"İndirilecek URL: {final_url}")
    
    try:
        # Önce orijinal URL'den başlık bilgisi almayı dene
        title = None
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', None)
        except:
            pass
        
        # Başlık alınamazsa zaman damgası kullan
        if not title:
            title = f"video_{int(time.time())}"
        
        # Download klasörünün varlığını kontrol et
        if not os.path.exists(Config.DOWNLOAD_FOLDER):
            os.makedirs(Config.DOWNLOAD_FOLDER)
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{Config.DOWNLOAD_FOLDER}/{title}.%(ext)s',
            'restrictfilenames': True,  # Dosya adında geçersiz karakterleri temizle
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(final_url, download=True)
            filename = ydl.prepare_filename(info)
            return send_file(filename, as_attachment=True)
    except Exception as e:
        raise Exception(f"Hata: Bu URL desteklenmiyor veya video bulunamadı. {e}")
