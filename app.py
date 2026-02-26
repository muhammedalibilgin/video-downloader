from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from models import db
from services.auth import requires_auth
from services.video import get_video_info, download_video
from services.visitor import log_visitor, get_recent_visitors
from services.download_log import log_download_preview, log_download_attempt, log_download_result, get_recent_download_logs
from utils.database import configure_sqlite
import os
import time

def cleanup_old_files():
    """20 dakikadan eski dosyaları temizle"""
    try:
        download_folder = Config.DOWNLOAD_FOLDER
        current_time = time.time()
        
        if os.path.exists(download_folder):
            for filename in os.listdir(download_folder):
                file_path = os.path.join(download_folder, filename)
                if os.path.isfile(file_path):
                    # Dosya yaşını kontrol et (20 dakika = 1200 saniye)
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 1200:  # 20 dakika
                        os.remove(file_path)
                        print(f"Eski dosya silindi: {filename}")
    except Exception as e:
        print(f"Cleanup hatası: {e}")

app = Flask(__name__)
app.config.from_object(Config)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[Config.RATE_LIMIT_PER_MINUTE, Config.RATE_LIMIT_PER_DAY]
)

# Database konfigürasyonu
db.init_app(app)

# SQLite konfigürasyonunu çağır
configure_sqlite()

 # Veritabanı tablolarını oluştur
with app.app_context():
    db.create_all()
    print("Veritabanı tabloları (Gunicorn/Main) kontrol edildi/oluşturuldu.")

# Download klasörünün varlığını kontrol et
if not os.path.exists(Config.DOWNLOAD_FOLDER):
    os.makedirs(Config.DOWNLOAD_FOLDER)

# Başlangıç cleanup'ı çalıştır
cleanup_old_files()

# Her request'te çalışan loglama fonksiyonu
@app.before_request
def log_visitor_request():
    log_visitor()

# Her 10 dakikada bir cleanup çalıştır
import threading
import time

def periodic_cleanup():
    while True:
        time.sleep(600)  # 10 dakika
        cleanup_old_files()

# Background thread'de periodic cleanup başlat
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

@app.route('/templates/<path:filename>')
def serve_template_static(filename):
    return send_from_directory('templates', filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview', methods=['POST'])
@limiter.limit("3 per minute;30 per day")
def preview():
    url = request.form.get('url')
    
    if not url:
        flash('Lütfen bir URL girin.')
        return redirect(url_for('index'))
    
    try:
        # Preview işlemi logla
        log_download_preview(url)
        
        video_info = get_video_info(url)
        return render_template('index.html', 
                             preview_url=video_info['video_url'], 
                             preview_title=video_info['title'],
                             original_url=video_info['original_url'])
    except Exception as e:
        # Özel hata mesajları
        error_msg = str(e)
        if "çok büyük" in error_msg.lower():
            flash(f'⚠️ {error_msg}')
        elif "güvenli olmayan url" in error_msg.lower():
            flash(f'🔒 {error_msg}')
        else:
            flash(f'Video önizlenemedi: {e}')
        return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
@limiter.limit("3 per minute;30 per day")
def download():
    url = request.form.get('url')

    if not url:
        flash('Lütfen bir URL girin.')
        return redirect(url_for('index'))
    
    try:
        # Download denemesini logla
        log_download_attempt(url)
        
        # Videoyu indirmeyi dene
        result = download_video(url)
        
        # Başarılı olduğunu logla
        log_download_result(url, success=True)
        
        return result
    except Exception as e:
        # Başarısız olduğunu logla
        log_download_result(url, success=False)
        
        flash(f"Hata oluştu: {e}")
        return f"<h3>Hata: Bu URL desteklenmiyor / Boyut sınırı aşıldı veya Video bulunamadı.</h3><a href='/'>Geri Dön</a>", 400

# Admin endpoint'i - ziyaretçi loglarını görüntüle (Basic Authentication ile korumalı)
@app.route('/admin/visitors')
@requires_auth
def admin_visitors():
    try:
        visitors = get_recent_visitors()
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

# Admin endpoint'i - download loglarını görüntüle (Basic Authentication ile korumalı)
@app.route('/admin/downloads')
@requires_auth
def admin_downloads():
    try:
        download_logs = get_recent_download_logs()
        return jsonify({
            'success': True,
            'count': len(download_logs),
            'downloads': [log.to_dict() for log in download_logs]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=5001, debug=False)