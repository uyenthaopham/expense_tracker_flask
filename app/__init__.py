from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, csrf
from sqlalchemy import text  # <--- Quan trọng: Để chạy lệnh SQL trực tiếp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Khởi tạo
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Route trang chủ
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('base.html')

    # Import models
    from app import models
   
    # Blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.categories import bp as categories_bp
    app.register_blueprint(categories_bp, url_prefix='/categories')
    
    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # --- ĐOẠN CODE "BÚA TẠ" (SQL TRỰC TIẾP) ---
    @app.route('/force-fix')
    def force_fix():
        try:
            # Chúng ta dùng SQL để ép Database mở rộng cột password lên 512 ký tự
            # Bất kể models.py viết gì, lệnh này sẽ ghi đè lên Database thực tế.
            with db.engine.connect() as conn:
                # Lệnh dành cho PostgreSQL
                conn.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(512);'))
                conn.commit()
            
            return """
            <div style="text-align: center; margin-top: 50px; font-family: sans-serif;">
                <h1 style="color: green;">✅ THÀNH CÔNG RỰC RỠ!</h1>
                <p>Tôi đã ép Database mở rộng cột mật khẩu lên <b>512 ký tự</b>.</p>
                <p>Bây giờ bạn có thể đăng ký thoải mái.</p>
                <br>
                <a href="/" style="background: blue; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Về trang chủ và Đăng ký ngay</a>
            </div>
            """
        except Exception as e:
            return f"""
            <h1 style="color: red;">Vẫn có lỗi:</h1>
            <p>{str(e)}</p>
            <p>Nếu lỗi báo "relation user does not exist", nghĩa là bảng chưa được tạo. Hãy chạy lại lệnh cũ trước.</p>
            """

    return app