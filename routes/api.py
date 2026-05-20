from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from werkzeug.datastructures import MultiDict

from models import AIRecommendation, Course, Test, TestResult, User
from services.ai_service import chat_with_gemini, generate_questions
from services.authz import role_required
from services.stats_service import platform_overview
from services.test_service import evaluate_and_save


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/courses")
def api_courses():
    courses = Course.query.filter_by(status="published").all()
    return jsonify(
        [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "topic": course.topic,
                "difficulty": course.difficulty,
                "lessons_count": len(course.lessons),
                "tests_count": len(course.tests),
            }
            for course in courses
        ]
    )


@api_bp.get("/courses/<int:course_id>")
def api_course(course_id):
    course = Course.query.get_or_404(course_id)
    return jsonify(
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "topic": course.topic,
            "difficulty": course.difficulty,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content,
                    "estimated_minutes": lesson.estimated_minutes,
                }
                for lesson in course.lessons
            ],
            "tests": [{"id": test.id, "title": test.title} for test in course.tests],
        }
    )


@api_bp.get("/tests/<int:test_id>")
@login_required
def api_test(test_id):
    test = Test.query.get_or_404(test_id)
    return jsonify(
        {
            "id": test.id,
            "title": test.title,
            "time_limit_minutes": test.time_limit_minutes,
            "passing_score": test.passing_score,
            "questions": [
                {
                    "id": question.id,
                    "text": question.text,
                    "topic": question.topic,
                    "answers": [
                        {"id": answer.id, "text": answer.text} for answer in question.answers
                    ],
                }
                for question in test.questions
            ],
        }
    )


@api_bp.post("/tests/<int:test_id>/submit")
@login_required
@role_required("student", "admin")
def api_submit_test(test_id):
    test = Test.query.get_or_404(test_id)
    payload = request.get_json(force=True, silent=True) or {}
    answers = payload.get("answers", {})
    form_data = MultiDict(
        [(f"answer_{question_id}", answer_id) for question_id, answer_id in answers.items()]
    )
    form_data.add("time_spent_seconds", payload.get("time_spent_seconds", 0))
    result = evaluate_and_save(test, form_data)
    return jsonify(
        {
            "result_id": result.id,
            "score": result.score,
            "correct_answers": result.correct_answers,
            "total_questions": result.total_questions,
            "passed": result.passed,
        }
    )


@api_bp.get("/results")
@login_required
def api_results():
    query = TestResult.query
    if current_user.role != "admin":
        query = query.filter_by(user_id=current_user.id)
    results = query.order_by(TestResult.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": result.id,
                "test": result.test.title,
                "course": result.test.course.title,
                "score": result.score,
                "passed": result.passed,
                "created_at": result.created_at.isoformat(),
            }
            for result in results
        ]
    )


@api_bp.get("/recommendations/<int:result_id>")
@login_required
def api_recommendation(result_id):
    recommendation = AIRecommendation.query.filter_by(result_id=result_id).first_or_404()
    if current_user.role != "admin" and recommendation.user_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403
    return jsonify(
        {
            "summary": recommendation.summary,
            "weak_topics": recommendation.weak_topics,
            "plan": recommendation.plan,
            "created_at": recommendation.created_at.isoformat(),
        }
    )


@api_bp.post("/ai/questions")
@login_required
@role_required("teacher", "admin")
def api_ai_questions():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        count = int(payload.get("count", 5))
    except (TypeError, ValueError):
        count = 5
    questions = generate_questions(
        payload.get("topic", "Общая тема"),
        count=max(1, min(count, 25)),
        difficulty=payload.get("difficulty", "middle"),
    )
    return jsonify({"questions": questions})


@api_bp.post("/ai/chat")
@login_required
def api_ai_chat():
    payload = request.get_json(force=True, silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message is required"}), 400
    result = chat_with_gemini(
        message,
        history=payload.get("history", []),
        user=current_user,
    )
    return jsonify(result)


@api_bp.get("/users")
@login_required
@role_required("admin")
def api_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_enabled": user.is_enabled,
            }
            for user in users
        ]
    )


@api_bp.get("/stats/overview")
def api_stats():
    return jsonify(platform_overview())
