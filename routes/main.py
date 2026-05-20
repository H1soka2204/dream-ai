from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import login_required
from sqlalchemy import or_

from models import Course, TestResult
from services.i18n import LANGUAGES, t
from services.stats_service import platform_overview


main_bp = Blueprint("main", __name__)


@main_bp.route("/language/<language>")
def set_language(language):
    if language in LANGUAGES:
        session["language"] = language
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/")
def index():
    featured_courses = Course.query.filter_by(status="published").limit(3).all()
    overview = platform_overview()
    return render_template(
        "index.html",
        title="AI Edu Test",
        featured_courses=featured_courses,
        overview=overview,
    )


@main_bp.route("/courses")
def courses():
    query = Course.query.filter_by(status="published")
    search = request.args.get("q", "").strip()
    topic = request.args.get("topic", "").strip()
    difficulty = request.args.get("difficulty", "").strip()
    if search:
        query = query.filter(
            or_(
                Course.title.ilike(f"%{search}%"),
                Course.description.ilike(f"%{search}%"),
                Course.topic.ilike(f"%{search}%"),
            )
        )
    if topic:
        query = query.filter(Course.topic == topic)
    if difficulty:
        query = query.filter(Course.difficulty == difficulty)

    topics = [row[0] for row in Course.query.with_entities(Course.topic).distinct().all()]
    courses_list = query.order_by(Course.created_at.desc()).all()
    return render_template(
        "courses.html",
        title=t("Курсы"),
        courses=courses_list,
        topics=topics,
        search=search,
        selected_topic=topic,
        selected_difficulty=difficulty,
    )


@main_bp.route("/chat")
@login_required
def chat():
    gemini_enabled = (
        current_app.config.get("AI_PROVIDER") == "gemini"
        and bool(current_app.config.get("GEMINI_API_KEY"))
    )
    initial_prompt = request.args.get("prompt", "").strip()[:4000]
    return render_template(
        "chat.html",
        title=t("AI чат"),
        gemini_enabled=gemini_enabled,
        gemini_model=current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash-lite"),
        initial_prompt=initial_prompt,
    )


@main_bp.route("/courses/<int:course_id>")
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template("course_detail.html", title=t(course.title), course=course)


@main_bp.route("/stats")
def stats():
    overview = platform_overview()
    recent_results = TestResult.query.order_by(TestResult.created_at.desc()).limit(10).all()
    return render_template(
        "stats.html",
        title=t("Статистика"),
        overview=overview,
        recent_results=recent_results,
    )


@main_bp.app_errorhandler(403)
def forbidden(_error):
    return render_template("errors/403.html", title=t("Нет доступа")), 403


@main_bp.app_errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html", title=t("Страница не найдена")), 404
