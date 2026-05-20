from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend import db
from models import AIRecommendation, Course, Test, TestResult, User
from services.authz import role_required
from services.i18n import t
from services.stats_service import platform_overview


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    overview = platform_overview()
    users = User.query.order_by(User.created_at.desc()).all()
    courses = Course.query.order_by(Course.created_at.desc()).all()
    tests = Test.query.order_by(Test.created_at.desc()).all()
    results = TestResult.query.order_by(TestResult.created_at.desc()).limit(12).all()
    return render_template(
        "admin/dashboard.html",
        title=t("Админ-панель"),
        overview=overview,
        users=users,
        courses=courses,
        tests=tests,
        results=results,
    )


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get("role", user.role)
    if role in {"student", "teacher", "admin"}:
        user.role = role
        db.session.commit()
        flash(t("Роль пользователя обновлена."), "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/password", methods=["POST"])
@login_required
@role_required("admin")
def update_user_password(user_id):
    user = User.query.get_or_404(user_id)
    password = request.form.get("new_password", "").strip()
    if len(password) < 6:
        flash("Пароль должен быть не короче 6 символов.", "warning")
        return redirect(url_for("admin.dashboard"))

    user.set_password(password)
    db.session.commit()
    flash("Пароль пользователя обновлён.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_enabled = not user.is_enabled
    db.session.commit()
    flash(t("Статус пользователя изменен."), "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Нельзя удалить свой аккаунт.", "danger")
        return redirect(url_for("admin.dashboard"))

    result_ids = [
        result_id
        for (result_id,) in TestResult.query.with_entities(TestResult.id)
        .filter_by(user_id=user.id)
        .all()
    ]
    if result_ids:
        AIRecommendation.query.filter(
            AIRecommendation.result_id.in_(result_ids)
        ).delete(synchronize_session=False)

    AIRecommendation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    TestResult.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Course.query.filter_by(teacher_id=user.id).update(
        {"teacher_id": None}, synchronize_session=False
    )
    Test.query.filter_by(teacher_id=user.id).update(
        {"teacher_id": None}, synchronize_session=False
    )

    db.session.delete(user)
    db.session.commit()
    flash("Пользователь удалён.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/courses/<int:course_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def update_course_status(course_id):
    course = Course.query.get_or_404(course_id)
    course.status = request.form.get("status", course.status)
    db.session.commit()
    flash(t("Статус курса обновлен."), "success")
    return redirect(url_for("admin.dashboard"))
