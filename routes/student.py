from flask import Blueprint, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from models import AIRecommendation, Course, Test, TestResult
from services.authz import role_required
from services.i18n import t
from services.pdf_service import build_result_pdf
from services.stats_service import student_overview
from services.test_service import evaluate_and_save


student_bp = Blueprint("student", __name__, url_prefix="/student")


def _best_recommendations_by_test(items):
    best_items = {}
    general_items = []

    for item in items:
        if not item.result:
            general_items.append(item)
            continue

        key = item.result.test_id
        current = best_items.get(key)
        if current is None:
            best_items[key] = item
            continue

        is_better_score = item.result.score > current.result.score
        is_newer_tie = (
            item.result.score == current.result.score
            and item.created_at > current.created_at
        )
        if is_better_score or is_newer_tie:
            best_items[key] = item

    result_items = list(best_items.values())
    if general_items:
        result_items.append(max(general_items, key=lambda item: item.created_at))

    return sorted(result_items, key=lambda item: item.created_at, reverse=True)


@student_bp.route("/dashboard")
@login_required
@role_required("student", "admin")
def dashboard():
    overview = student_overview(current_user)
    courses = Course.query.filter_by(status="published").limit(6).all()
    recommendations = (
        AIRecommendation.query.filter_by(user_id=current_user.id)
        .order_by(AIRecommendation.created_at.desc())
        .all()
    )
    recommendations = _best_recommendations_by_test(recommendations)[:3]
    return render_template(
        "student/dashboard.html",
        title=t("Кабинет ученика"),
        overview=overview,
        courses=courses,
        recommendations=recommendations,
    )


@student_bp.route("/tests/<int:test_id>", methods=["GET", "POST"])
@login_required
@role_required("student", "admin")
def take_test(test_id):
    test = Test.query.get_or_404(test_id)
    if not test.questions:
        flash(t("В этом тесте пока нет вопросов."), "warning")
        return redirect(url_for("main.course_detail", course_id=test.course_id))

    from flask import request

    if request.method == "POST":
        result = evaluate_and_save(test, request.form)
        flash(t("Тест проверен. AI-рекомендация уже готова."), "success")
        return redirect(url_for("student.result", result_id=result.id))

    return render_template("student/test.html", title=t(test.title), test=test)


@student_bp.route("/results/<int:result_id>")
@login_required
@role_required("student", "admin")
def result(result_id):
    result_item = TestResult.query.get_or_404(result_id)
    if current_user.role != "admin" and result_item.user_id != current_user.id:
        flash(t("Этот результат принадлежит другому пользователю."), "danger")
        return redirect(url_for("student.dashboard"))
    return render_template("student/result.html", title=t("Результат теста"), result=result_item)


@student_bp.route("/recommendations")
@login_required
@role_required("student", "admin")
def recommendations():
    items = (
        AIRecommendation.query.filter_by(user_id=current_user.id)
        .order_by(AIRecommendation.created_at.desc())
        .all()
    )
    items = _best_recommendations_by_test(items)
    if items:
        items = [
            max(
                items,
                key=lambda item: (
                    item.result.score if item.result else -1,
                    item.created_at,
                ),
            )
        ]
    return render_template(
        "student/recommendations.html",
        title=t("AI-рекомендации"),
        recommendations=items,
    )


@student_bp.route("/results/<int:result_id>/pdf")
@login_required
@role_required("student", "admin")
def export_result_pdf(result_id):
    result_item = TestResult.query.get_or_404(result_id)
    if current_user.role != "admin" and result_item.user_id != current_user.id:
        flash(t("Нет доступа к этому результату."), "danger")
        return redirect(url_for("student.dashboard"))
    pdf_buffer = build_result_pdf(result_item)
    filename = f"result-{result_item.id}-{result_item.certificate_code}.pdf"
    return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
