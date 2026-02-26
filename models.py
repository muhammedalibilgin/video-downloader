from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

db = SQLAlchemy()

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

class DownloadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), nullable=False)  # IPv6 desteklemek için 45 karakter
    video_url = db.Column(db.String(1000), nullable=False)  # Kullanıcının girdiği original URL
    status = db.Column(db.String(20), nullable=False)  # preview, downloading, success, failed
    user_agent = db.Column(db.Text, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)  # Byte cinsinden dosya boyutu
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'video_url': self.video_url,
            'status': self.status,
            'user_agent': self.user_agent,
            'file_size_mb': f"{self.file_size / (1024*1024):.1f}MB" if self.file_size else None,
            'created_at': self.to_tr_time().isoformat() if self.created_at else None
        }
    
    def to_tr_time(self):
        """UTC zamanı Türkiye saatine çevir (modern çözüm)"""
        return self.created_at.astimezone(ZoneInfo("Europe/Istanbul"))
