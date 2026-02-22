from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from playwright.sync_api import sync_playwright
import yt_dlp
import os
import time

app = Flask(__name__)
app.secret_key = "gizli_anahtar" # Hata mesajları (flash) için gerekli

# Videoların geçici olarak kaydedileceği klasör
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/templates/<path:filename>')
def serve_template_static(filename):
    return send_from_directory('templates', filename)

def get_m3u8_url(web_url):
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview', methods=['POST'])
def preview():
    url = request.form.get('url')
    
    if not url:
        flash('Lütfen bir URL girin.')
        return redirect(url_for('index'))
    
    try:
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
            
        return render_template('index.html', 
                             preview_url=video_url, 
                             preview_title=title,
                             original_url=url)
    except Exception as e:
        flash(f'Video önizlenemedi: {e}')
        return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')

    if not url:
        flash('Lütfen bir URL girin.')
        return redirect(url_for('index'))

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
            import time
            title = f"video_{int(time.time())}"
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/{title}.%(ext)s',
            'restrictfilenames': True,  # Dosya adında geçersiz karakterleri temizle
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(final_url, download=True)
            filename = ydl.prepare_filename(info)
            return send_file(filename, as_attachment=True)
    except Exception as e:
        # print(f"Hata oluştu: {e}")
        flash(f"Hata oluştu: {e}")

        return f"<h3>Hata: Bu URL desteklenmiyor veya video bulunamadı.</h3><a href='/'>Geri Dön</a>", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)