from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# erstellen die Instanzen hier, verknüpfen sie aber später in __init__.py mit der App
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Wohin User geleitet werden, wenn sie nicht eingeloggt sind
login_manager.login_message_category = 'info'
csrf = CSRFProtect()