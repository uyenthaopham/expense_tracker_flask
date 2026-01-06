import pytest
from app import create_app, db
from app.models import User
from config import Config

# Wir bauen eine Test-Konfiguration
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Datenbank nur im RAM (schnell & wegwerfbar)
    WTF_CSRF_ENABLED = False # CSRF im Test ausschalten, macht es viel einfacher

@pytest.fixture(scope='module')
def test_client():
    # 1. App erstellen
    flask_app = create_app(TestConfig)

    # 2. Test-Client erstellen (wie ein Fake-Browser)
    testing_client = flask_app.test_client()

    # 3. App-Kontext und Datenbank aufbauen
    ctx = flask_app.app_context()
    ctx.push()
    
    db.create_all() # Tabellen erstellen

    yield testing_client  # Hier läuft der eigentliche Test

    # 4. Aufräumen nach dem Test
    db.session.remove()
    db.drop_all()
    ctx.pop()

@pytest.fixture(scope='module')
def init_database(test_client):
    # Erstelle einen Test-User
    user = User(email='test@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    
    yield db  # Datenbank für Tests bereitstellen

    db.session.remove()