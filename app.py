from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from playwright.sync_api import sync_playwright
import yt_dlp
import os
import time
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
import base64
from functools import wraps
from dotenv import load_dotenv

# .env dosyasını yükle (local development için)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'gizli_anahtar') # Hata mesajları (flash) için gerekli

# Admin Basic Authentication konfigürasyonu
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  # Production'da environment variable'dan alınmalı

# SQLite veritabanı konfigürasyonu
database_url = 'sqlite:///visitors.db'
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy instance
db = SQLAlchemy(app)

# Visitor modeli
class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), nullable=False)  # IPv6 desteklemek için 45 karakter
    path = db.Column(db.String(500), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'path': self.path,
            'user_agent': self.user_agent,
            'created_at': self.to_tr_time().isoformat() if self.created_at else None
        }
    
    def to_tr_time(self):
        """UTC zamanı Türkiye saatine çevir (modern çözüm)"""
        return self.created_at.astimezone(ZoneInfo("Europe/Istanbul"))

# Videoların geçici olarak kaydedileceği klasör
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# SQLite için WAL mode aktif et (performans için)
def configure_sqlite():
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# SQLite konfigürasyonunu çağır
configure_sqlite()

# Basic Authentication decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def check_auth(username, password):
    """Kullanıcı adı ve şifreyi kontrol et"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """Basic Authentication isteği gönder"""
    return make_response(
        jsonify({"error": "Could not verify your access level for that URL.\nYou have to login with proper credentials", "WWW-Authenticate": "Basic realm='Login Required'"}),
        401,
        {"WWW-Authenticate": "Basic realm='Login Required'"}
    )

# Her request'te çalışan loglama fonksiyonu
@app.before_request
def log_visitor():
    # Statik dosyaları ve admin endpoint'ini loglama
    if request.path.startswith('/static/') or request.path.startswith('/admin/'):
        return
    
    # Gerçek IP adresini al (reverse proxy arkasında çalışmak için)
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    
    # Path ve User-Agent bilgilerini al
    path = request.path
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Yeni visitor kaydı oluştur
    visitor = Visitor(ip=ip, path=path, user_agent=user_agent)
    db.session.add(visitor)
    db.session.commit()
    
    # FIFO mantığı: Toplam kayıt 500'yi geçerse en eski kayıtları sil
    # Subquery kullanarak tek sorguda silme işlemi
    total_count = Visitor.query.count()
    if total_count > 500:
        # En eski (total_count - 500) kaydı sil
        oldest_visitors = Visitor.query.order_by(Visitor.created_at.asc()).limit(total_count - 500).with_entities(Visitor.id).all()
        if oldest_visitors:
            oldest_ids = [v.id for v in oldest_visitors]
            Visitor.query.filter(Visitor.id.in_(oldest_ids)).delete(synchronize_session=False)
            db.session.commit()

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

# Admin endpoint'i - ziyaretçi loglarını görüntüle (Basic Authentication ile korumalı)
@app.route('/admin/visitors')
@requires_auth
def admin_visitors():
    try:
        # Son 500 kaydı created_at DESC sıralı olarak al
        visitors = Visitor.query.order_by(Visitor.created_at.desc()).limit(500).all()
        return jsonify({
            'success': True,
            'count': len(visitors),
            'visitors': [visitor.to_dict() for visitor in visitors]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':


    from datetime import datetime
    print("utcnow-->", datetime.utcnow())
    print("now-->", datetime.now())
        
    # Veritabanı tablolarını oluştur
    with app.app_context():
        db.create_all()
        print("Veritabanı tabloları oluşturuldu.")
    
    app.run(host='0.0.0.0', port=5001, debug=True)