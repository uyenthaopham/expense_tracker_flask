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
    
    # Route cơ bản
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('base.html')

    # Importiere Modelle, damit Flask-Migrate sie erkennt
    from app import models
   
    # --- Đăng ký Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.categories import bp as categories_bp
    app.register_blueprint(categories_bp, url_prefix='/categories')
    
    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # --- ROUTE SỬA LỖI DATABASE (Debug) ---
    @app.route('/debug-db')
    def debug_db():
        try:
            # 1. XÓA SẠCH DATABASE CŨ
            db.drop_all()
            
            # 2. TẠO LẠI DATABASE MỚI (Với cột password 256 ký tự)
            db.create_all()
            
            return "<h1>Đã Reset Database thành công!</h1><p>Cột password đã được mở rộng. Hãy về trang chủ đăng ký lại.</p><a href='/'>Về trang chủ</a>"
        except Exception as e:
            return f"<h1>Lỗi: {e}</h1>"

    return app