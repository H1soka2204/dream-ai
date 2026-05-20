from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, request, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from backend.config import Config


db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    (base_dir / "database").mkdir(exist_ok=True)

    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите в аккаунт, чтобы продолжить."
    login_manager.login_message_category = "warning"

    from models.entities import User
    from services.i18n import LANGUAGES, current_language, t

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        flash(t("Войдите в аккаунт, чтобы продолжить."), "warning")
        return redirect(url_for("auth.login", next=request.full_path))

    @app.context_processor
    def inject_i18n():
        return {
            "t": t,
            "current_language": current_language(),
            "languages": LANGUAGES,
        }

    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.student import student_bp
    from routes.teacher import teacher_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        from services.seed import seed_demo_data

        seed_demo_data()

    return app
