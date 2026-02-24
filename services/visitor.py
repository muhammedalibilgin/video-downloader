from flask import request
from models import Visitor, db
from config import Config

def log_visitor():
    """Ziyaretçi bilgilerini logla"""
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
    
    # FIFO mantığı: Toplam kayıt limiti geçerse en eski kayıtları sil
    cleanup_old_visitors()

def cleanup_old_visitors():
    """Eski visitor kayıtlarını temizle"""
    total_count = Visitor.query.count()
    if total_count > Config.VISITOR_LOG_LIMIT:
        # En eski (total_count - VISITOR_LOG_LIMIT) kaydı sil
        oldest_visitors = Visitor.query.order_by(Visitor.created_at.asc()).limit(total_count - Config.VISITOR_LOG_LIMIT).with_entities(Visitor.id).all()
        if oldest_visitors:
            oldest_ids = [v.id for v in oldest_visitors]
            Visitor.query.filter(Visitor.id.in_(oldest_ids)).delete(synchronize_session=False)
            db.session.commit()

def get_recent_visitors(limit=500):
    """Son ziyaretçi kayıtlarını getir"""
    return Visitor.query.order_by(Visitor.created_at.desc()).limit(limit).all()
