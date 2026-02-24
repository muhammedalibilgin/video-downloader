from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, send_from_directory
from config import Config
from models import db
from services.auth import requires_auth
from services.video import get_video_info, download_video
from services.visitor import log_visitor, get_recent_visitors
from utils.database import configure_sqlite
import os

app = Flask(__name__)
app.config.from_object(Config)

# Database konfigürasyonu
db.init_app(app)

# SQLite konfigürasyonunu çağır
configure_sqlite()

# Download klasörünün varlığını kontrol et
if not os.path.exists(Config.DOWNLOAD_FOLDER):
    os.makedirs(Config.DOWNLOAD_FOLDER)

# Her request'te çalışan loglama fonksiyonu
@app.before_request
def log_visitor_request():
    log_visitor()

@app.route('/templates/<path:filename>')
def serve_template_static(filename):
    return send_from_directory('templates', filename)

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
        video_info = get_video_info(url)
        return render_template('index.html', 
                             preview_url=video_info['video_url'], 
                             preview_title=video_info['title'],
                             original_url=video_info['original_url'])
    except Exception as e:
        flash(f'Video önizlenemedi: {e}')
        return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')

    if not url:
        flash('Lütfen bir URL girin.')
        return redirect(url_for('index'))
    
    try:
        return download_video(url)
    except Exception as e:
        flash(f"Hata oluştu: {e}")
        return f"<h3>Hata: Bu URL desteklenmiyor veya video bulunamadı.</h3><a href='/'>Geri Dön</a>", 400

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

if __name__ == '__main__':
    # Veritabanı tablolarını oluştur
    with app.app_context():
        db.create_all()
        print("Veritabanı tabloları oluşturuldu.")
    
    app.run(host='0.0.0.0', port=5001, debug=True)