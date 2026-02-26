import os
from dotenv import load_dotenv

# .env dosyasını yükle (local development için)
load_dotenv()

class Config:
    # Flask konfigürasyonu
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'gizli_anahtar')
    
    # Admin Basic Authentication konfigürasyonu
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # SQLite veritabanı konfigürasyonu
    DATABASE_URL = 'sqlite:///visitors.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Download klasörü
    DOWNLOAD_FOLDER = 'downloads'
    
    # Visitor log limiti
    VISITOR_LOG_LIMIT = 500
    
    # Download log limiti
    DOWNLOAD_LOG_LIMIT = 500
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = "3 per minute"
    RATE_LIMIT_PER_DAY = "30 per day"
