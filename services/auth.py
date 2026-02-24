from functools import wraps
from flask import request, jsonify, make_response
from config import Config

def check_auth(username, password):
    """Kullanıcı adı ve şifreyi kontrol et"""
    return username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD

def authenticate():
    """Basic Authentication isteği gönder"""
    return make_response(
        jsonify({"error": "Could not verify your access level for that URL.\nYou have to login with proper credentials", "WWW-Authenticate": "Basic realm='Login Required'"}),
        401,
        {"WWW-Authenticate": "Basic realm='Login Required'"}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
