from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from random import shuffle

from backend import db
from models import Answer, Course, Lesson, Question, Test
from services.ai_service import generate_questions
from services.authz import role_required
from services.i18n import t
from services.stats_service import teacher_overview


teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def _prepared_answers(raw_answers):
    raw_answers = raw_answers or []
    answers = [answer for answer in raw_answers if isinstance(answer, dict)]
    correct_answer = next(
        (answer for answer in answers if answer.get("is_correct")),
        {"text": "Правильный ответ", "is_correct": True},
    )
    wrong_answers = [answer for answer in answers if not answer.get("is_correct")]

    prepared = [
        {
            "text": correct_answer.get("text", "Правильный ответ"),
            "is_correct": True,
        }
    ]
    prepared.extend(
        {
            "text": answer.get("text", "Вариант ответа"),
            "is_correct": False,
        }
        for answer in wrong_answers[:3]
    )

    while len(prepared) < 4:
        prepared.append(
            {
                "text": f"Дополнительный вариант {len(prepared) + 1}",
                "is_correct": False,
            }
        )

    shuffle(prepared)
    return prepared


@teacher_bp.route("/dashboard")
@login_required
@role_required("teacher", "admin")
def dashboard():
    overview = teacher_overview(current_user.id)
    all_courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template(
        "teacher/dashboard.html",
        title=t("Кабинет преподавателя"),
        overview=overview,
        all_courses=all_courses,
    )


@teacher_bp.route("/courses", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def create_course():
    course = Course(
        title=request.form.get("title", "").strip(),
        description=request.form.get("description", "").strip(),
        topic=request.form.get("topic", "").strip() or t("Общее"),
        difficulty=request.form.get("difficulty", "beginner"),
        accent=request.form.get("accent", "blue"),
        teacher_id=current_user.id,
    )
    if not course.title or not course.description:
        flash(t("Название и описание курса обязательны."), "warning")
    else:
        db.session.add(course)
        db.session.commit()
        flash(t("Курс добавлен."), "success")
    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route("/lessons", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def create_lesson():
    lesson = Lesson(
        course_id=request.form.get("course_id", type=int),
        title=request.form.get("title", "").strip(),
        content=request.form.get("content", "").strip(),
        position=request.form.get("position", default=1, type=int),
        estimated_minutes=request.form.get("estimated_minutes", default=15, type=int),
    )
    if not lesson.course_id or not lesson.title or not lesson.content:
        flash(t("Заполните курс, название и содержание материала."), "warning")
    else:
        db.session.add(lesson)
        db.session.commit()
        flash(t("Учебный материал добавлен."), "success")
    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route("/tests", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def create_test():
    course_id = request.form.get("course_id", type=int)
    title = request.form.get("title", "").strip()
    topic = request.form.get("topic", "").strip() or title
    difficulty = request.form.get("difficulty", "middle")
    question_count = request.form.get("question_count", default=5, type=int)
    if not course_id or not title:
        flash(t("Выберите курс и укажите название теста."), "warning")
        return redirect(url_for("teacher.dashboard"))

    test = Test(
        course_id=course_id,
        teacher_id=current_user.id,
        title=title,
        description=request.form.get("description", "").strip() or t("AI-тест по теме {topic}", topic=topic),
        difficulty=difficulty,
        time_limit_minutes=request.form.get("time_limit_minutes", default=20, type=int),
        passing_score=request.form.get("passing_score", default=70, type=int),
    )
    db.session.add(test)
    db.session.flush()

    questions = generate_questions(topic, count=max(1, min(question_count, 25)), difficulty=difficulty)
    for question_data in questions:
        question = Question(
            test_id=test.id,
            text=question_data.get("text", t("Новый вопрос")),
            topic=question_data.get("topic", topic),
            difficulty=question_data.get("difficulty", difficulty),
            explanation=question_data.get("explanation", ""),
        )
        db.session.add(question)
        db.session.flush()
        question_data["answers"] = _prepared_answers(question_data.get("answers", []))
        answers = question_data.get("answers", [])
        if not any(answer.get("is_correct") for answer in answers):
            answers = [{"text": t("Правильный ответ"), "is_correct": True}] + answers[:3]
        while len(answers) < 4:
            answers.append({"text": t("Дополнительный вариант {number}", number=len(answers) + 1), "is_correct": False})
        for answer_data in answers[:4]:
            db.session.add(
                Answer(
                    question_id=question.id,
                    text=answer_data.get("text", t("Вариант ответа")),
                    is_correct=bool(answer_data.get("is_correct")),
                )
            )
    db.session.commit()
    flash(t("Тест создан. Вопросы сгенерированы AI-сервисом или локальным fallback."), "success")
    return redirect(url_for("main.course_detail", course_id=course_id))
