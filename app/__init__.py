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


# ... các đoạn code khác ở trên ...

    # --- ĐOẠN CODE CỨU HỘ START ---
    @app.route('/debug-db')
    def debug_db():
        import os
        from sqlalchemy import text
        
        # 1. Kiểm tra xem app có nhận được đường dẫn Database không
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        # 2. Thử kết nối và tạo bảng
        try:
            # In ra loại database đang dùng (Postgres hay SQLite)
            db_type = "PostgreSQL" if "postgres" in db_url else "SQLite"
            
            # Lệnh tạo bảng
            db.create_all()
            
            # Thử thêm một user giả để xem database có hoạt động không
            return f"""
            <h1>Kết quả sửa lỗi:</h1>
            <ul>
                <li><strong>Database URL:</strong> {db_type} (Đã nhận diện đúng)</li>
                <li><strong>Trạng thái tạo bảng:</strong> THÀNH CÔNG! ✅</li>
                <li><strong>Hướng dẫn:</strong> Bây giờ bạn hãy quay lại trang chủ và đăng ký tài khoản.</li>
            </ul>
            <a href="/">Về trang chủ</a>
            """
        except Exception as e:
            return f"""
            <h1>CÓ LỖI XẢY RA ❌</h1>
            <p>Hãy chụp màn hình lỗi này và gửi cho AI:</p>
            <div style="background: #f8d7da; padding: 20px; border: 1px solid #f5c6cb;">
                {str(e)}
            </div>
            <h3>Thông tin debug:</h3>
            <p>DB URL Config: {db_url.split('@')[-1] if '@' in db_url else db_url}</p>
            """
    # --- ĐOẠN CODE CỨU HỘ END ---

    
    return app


   