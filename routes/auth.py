from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend import db
from models import User
from services.authz import dashboard_endpoint_for
from services.i18n import t


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.values.get("next", "")
    if next_url and (not next_url.startswith("/") or next_url.startswith("//")):
        next_url = ""

    if current_user.is_authenticated:
        return redirect(next_url or url_for(dashboard_endpoint_for(current_user.role)))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_enabled:
            login_user(user, remember=bool(request.form.get("remember")))
            flash(t("Вы успешно вошли в систему."), "success")
            return redirect(next_url or url_for(dashboard_endpoint_for(user.role)))
        flash(t("Неверный email или пароль."), "danger")

    return render_template("auth/login.html", title=t("Вход"), next_url=next_url)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_endpoint_for(current_user.role)))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if role not in {"student", "teacher"}:
            role = "student"
        if not name or not email or len(password) < 6:
            flash(t("Заполните все поля. Пароль должен быть не короче 6 символов."), "warning")
        elif User.query.filter_by(email=email).first():
            flash(t("Пользователь с таким email уже существует."), "warning")
        else:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(t("Аккаунт создан. Добро пожаловать!"), "success")
            return redirect(url_for(dashboard_endpoint_for(user.role)))

    return render_template("auth/register.html", title=t("Регистрация"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash(t("Вы вышли из аккаунта."), "info")
    return redirect(url_for("main.index"))
