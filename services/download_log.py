from flask import request
from models import DownloadLog, db
from config import Config

def log_download_preview(video_url, file_size=None):
    """Preview işlemi logla"""
    # Gerçek IP adresini al (reverse proxy arkasında çalışmak için)
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    
    # User-Agent bilgilerini al
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Yeni download log kaydı oluştur
    download_log = DownloadLog(ip=ip, video_url=video_url, status='preview', user_agent=user_agent, file_size=file_size)
    db.session.add(download_log)
    db.session.commit()

def log_download_attempt(video_url, file_size=None):
    """Download denemesi logla"""
    # Gerçek IP adresini al (reverse proxy arkasında çalışmak için)
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    
    # User-Agent bilgilerini al
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Yeni download log kaydı oluştur
    download_log = DownloadLog(ip=ip, video_url=video_url, status='downloading', user_agent=user_agent, file_size=file_size)
    db.session.add(download_log)
    db.session.commit()

def log_download_result(video_url, success=True, file_size=None):
    """Download sonucu logla"""
    # Gerçek IP adresini al (reverse proxy arkasında çalışmak için)
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    
    # User-Agent bilgilerini al
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Status belirle
    status = 'success' if success else 'failed'
    
    # Yeni download log kaydı oluştur
    download_log = DownloadLog(ip=ip, video_url=video_url, status=status, user_agent=user_agent, file_size=file_size)
    db.session.add(download_log)
    db.session.commit()
    
    # FIFO mantığı: Toplam kayıt limiti geçerse en eski kayıtları sil
    cleanup_old_download_logs()

def cleanup_old_download_logs():
    """Eski download log kayıtlarını temizle"""
    total_count = DownloadLog.query.count()
    if total_count > Config.DOWNLOAD_LOG_LIMIT:
        # En eski (total_count - DOWNLOAD_LOG_LIMIT) kaydı sil
        oldest_logs = DownloadLog.query.order_by(DownloadLog.created_at.asc()).limit(total_count - Config.DOWNLOAD_LOG_LIMIT).with_entities(DownloadLog.id).all()
        if oldest_logs:
            oldest_ids = [log.id for log in oldest_logs]
            DownloadLog.query.filter(DownloadLog.id.in_(oldest_ids)).delete(synchronize_session=False)
            db.session.commit()

def get_recent_download_logs(limit=500):
    """Son download log kayıtlarını getir"""
    return DownloadLog.query.order_by(DownloadLog.created_at.desc()).limit(limit).all()
