from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, csrf

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialisiere Erweiterungen
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('base.html')

    # --- NEU HINZUFÜGEN ---
    # Importiere Modelle, damit Flask-Migrate sie erkennt
    from app import models
   
   
    # ... (nach login_manager.init_app(app))

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # ... (auth blueprint ist hier)
    
    from app.categories import bp as categories_bp
    app.register_blueprint(categories_bp, url_prefix='/categories')

    
    
    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')


    
    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    @app.route('/fix-db')
    def fix_db():
        from app import db
        try:
            db.create_all()
            return "<h1>Erfolg! Datenbank-Tabellen wurden erstellt.</h1><a href='/'>Zur Startseite</a>"
        except Exception as e:
            return f"<h1>Fehler: {e}</h1>"

    
    return app


   