from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, send_from_directory, send_file
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
import re

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
        # Preview işlemi logla (boyut bilgisi ile)
        video_info = get_video_info(url)
        file_size = video_info.get('file_size')  # Boyut bilgisini al
        log_download_preview(url, file_size=file_size)
        
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
        return jsonify({'success': False, 'error': 'Lütfen bir URL girin.'})
    
    try:
        # Download denemesini logla (boyut bilgisi ile)
        video_info = get_video_info(url)
        file_size = video_info.get('file_size')
        log_download_attempt(url, file_size=file_size)
        
        # Videoyu indirmeyi dene
        result = download_video(url)
        
        # Başarılı olduğunu logla
        log_download_result(url, success=True, file_size=file_size)
        
        # AJAX request için JSON response döndür
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(result)
        else:
            return result
    except Exception as e:
        # Başarısız olduğunu logla
        video_info = None
        try:
            video_info = get_video_info(url)
            file_size = video_info.get('file_size')
        except:
            file_size = None
        
        log_download_result(url, success=False, file_size=file_size)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)})
        else:
            flash(f"Hata oluştu: {e}")
            return f"<h3>Hata: Bu URL desteklenmiyor / Boyut sınırı aşıldı veya Video bulunamadı.</h3><a href='/'>Geri Dön</a>", 400

@app.route('/get_file/<file_id>')
def get_file(file_id):
    """File ID ile dosyayı gönder"""
    try:
        # Download klasöründe dosyayı ara
        download_folder = Config.DOWNLOAD_FOLDER
        for filename in os.listdir(download_folder):
            if file_id in filename:
                file_path = os.path.join(download_folder, filename)
                if os.path.isfile(file_path):
                    # Dosya adını temizle - sadece uzantıyı koru
                    clean_filename = filename.replace(file_id, '')
                    if clean_filename.startswith('_'):
                        clean_filename = clean_filename[1:]
                    if clean_filename.startswith('.'):
                        clean_filename = 'video' + clean_filename
                    
                    response = send_file(file_path, as_attachment=True, download_name=clean_filename)
                    
                    # Response kapandığında dosyayı sil
                    @response.call_on_close
                    def cleanup():
                        try:
                            os.remove(file_path)
                            print(f"Dosya silindi: {file_path}")
                        except Exception as e:
                            print(f"Dosya silinemedi: {e}")
                    
                    return response
        
        return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
    except Exception as e:
        print(f"Get file error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

# Custom rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('rate_limit.html', limit=str(e.description)), 429

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=5001, debug=False)