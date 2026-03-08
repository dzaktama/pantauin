import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Pastikan memuat .env dari direktori root proyek
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    """Konfigurasi utama aplikasi PANTAUIN."""
    
    # Keamanan Dasar
    # Idealnya ditaruh di .env: SECRET_KEY=kunci_rahasia_anda_yang_sangat_panjang
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kunci_rahasia_pantauin_fallback_karena_env_kosong'
    
    # Konfigurasi Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'pantauin.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Keamanan Session Cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Konfigurasi Cache (Flask-Caching)
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 menit cache by default
    
    # Konfigurasi Upload
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # Maksimal ukuran file 2MB
