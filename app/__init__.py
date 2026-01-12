from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, csrf

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Khởi tạo các công cụ
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Route trang chủ
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('base.html')

    # Import models để migration hoạt động
    from app import models
   
    # Đăng ký các Blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.categories import bp as categories_bp
    app.register_blueprint(categories_bp, url_prefix='/categories')
    
    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    return app