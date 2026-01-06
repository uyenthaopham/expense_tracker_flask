import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Datenbank URL laden
    db_url = os.environ.get('DATABASE_URL')
    
    # Fix für Render.com: postgres:// zu postgresql:// ändern, falls nötig
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or \
        f"sqlite:///{os.path.join(basedir, 'app.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False