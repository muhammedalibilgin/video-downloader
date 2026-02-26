from playwright.sync_api import sync_playwright
import yt_dlp
import os
import time
import re
import uuid
from urllib.parse import urlparse
import ipaddress
import socket
from flask import send_file
from config import Config

def is_safe_url(url):
    """SSRF koruması: URL'in güvenli olup olmadığını kontrol et"""
    if not url:
        return False
    
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return False

    try:
        ip = socket.gethostbyname(parsed.hostname)
        ip_obj = ipaddress.ip_address(ip)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_link_local
            or ip_obj.is_multicast
        ):
            return False
    except:
        return False

    return True

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
                page.goto(web_url, wait_until="load", timeout=40000)
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
    # SSRF koruması
    if not is_safe_url(url):
        raise Exception("Güvenli olmayan URL: Private/local adreslere erişim engellenmiştir.")
    
    # 1. Önce m3u8 linkini yakalamaya çalış
    print(f"Kaynak taranıyor: {url}")
    m3u8_url = get_m3u8_url(url)
    
    # 2. Eğer m3u8 bulunduysa onu, bulunamadıysa orijinal linki kullan
    final_url = m3u8_url if m3u8_url else url
    print(f"Önizleme URL: {final_url}")
    
    # 3. Video bilgilerini al
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(final_url, download=False)
        
        # Dosya boyutu kontrolü
        file_size = info.get('filesize') or info.get('filesize_approx')
        if file_size and file_size > Config.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            limit_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
            raise Exception(f"Video dosyası çok büyük: {size_mb:.1f}MB (max: {limit_mb:.0f}MB)")
        
        video_url = info.get('url', final_url)  # Eğer url gelmezse m3u8 linkini kullan
        title = info.get('title', 'Video')
        
    return {
        'video_url': video_url,
        'title': title,
        'original_url': url,
        'file_size': file_size  # Boyut bilgisini de ekle
    }

def download_video(url):
    """Videoyu indir ve dosya olarak gönder"""
    # SSRF koruması
    if not is_safe_url(url):
        raise Exception("Güvenli olmayan URL: Private/local adreslere erişim engellenmiştir.")
    
    # 1. Önce m3u8 linkini yakalamaya çalış
    print(f"Kaynak taranıyor: {url}")
    m3u8_url = get_m3u8_url(url)

    # 2. Eğer m3u8 bulunduysa onu, bulunamadıysa orijinal linki kullan
    final_url = m3u8_url if m3u8_url else url
    print(f"İndirilecek URL: {final_url}")
    
    try:
        # Download klasörünün varlığını kontrol et
        if not os.path.exists(Config.DOWNLOAD_FOLDER):
            os.makedirs(Config.DOWNLOAD_FOLDER)
        
        # Unique filename oluştur (race condition önlemek için)
        unique_id = str(uuid.uuid4())
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{Config.DOWNLOAD_FOLDER}/{unique_id}.%(ext)s',
            'restrictfilenames': True,
            'max_filesize': Config.MAX_FILE_SIZE,  # Config'den oku
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(final_url, download=True)
            
            # Diskteki gerçek dosya adı
            filename = ydl.prepare_filename(info)
            
            # Kullanıcıya gösterilecek güvenli dosya adı
            title = info.get('title', f"video_{unique_id}")
            safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:80]
            file_ext = os.path.splitext(filename)[1]
            display_name = f"{safe_title}{file_ext}"
            
            response = send_file(filename, as_attachment=True, download_name=display_name)
            
            # Response gerçekten kapandığında dosyayı sil
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(filename)
                    print(f"Dosya silindi: {filename}")
                except Exception as e:
                    print(f"Dosya silinemedi: {e}")
            
            return response
    except Exception as e:
        raise Exception(f"Hata: Bu URL desteklenmiyor veya video bulunamadı. {e}")
