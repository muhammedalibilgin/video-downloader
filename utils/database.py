from sqlalchemy import event
from sqlalchemy.engine import Engine

def configure_sqlite():
    """SQLite için WAL mode aktif et (performans için)"""
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
