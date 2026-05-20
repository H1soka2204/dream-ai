import json
from collections import Counter

from flask_login import current_user

from backend import db
from models import AIRecommendation, TestResult
from services.ai_service import generate_recommendation


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {item}" for key, item in value.items() if str(item).strip()
        )
    return str(value).strip()


def evaluate_and_save(test, form_data):
    correct_count = 0
    answers_payload = []
    wrong_items = []

    for question in test.questions:
        selected_id = form_data.get(f"answer_{question.id}", type=int)
        selected_answer = next(
            (answer for answer in question.answers if answer.id == selected_id), None
        )
        correct_answer = next(
            (answer for answer in question.answers if answer.is_correct), None
        )
        is_correct = bool(selected_answer and selected_answer.is_correct)
        if is_correct:
            correct_count += 1
        else:
            wrong_items.append(
                {
                    "question": question.text,
                    "topic": question.topic,
                    "selected": selected_answer.text if selected_answer else "Не выбран",
                    "correct": correct_answer.text if correct_answer else "",
                    "explanation": question.explanation,
                }
            )
        answers_payload.append(
            {
                "question_id": question.id,
                "question": question.text,
                "topic": question.topic,
                "selected": selected_answer.text if selected_answer else "Не выбран",
                "correct": correct_answer.text if correct_answer else "",
                "is_correct": is_correct,
                "explanation": question.explanation,
            }
        )

    total = max(len(test.questions), 1)
    score = round((correct_count / total) * 100, 2)
    weak_topics = [topic for topic, _ in Counter(item["topic"] for item in wrong_items).most_common()]
    time_spent = form_data.get("time_spent_seconds", default=0, type=int)

    result = TestResult(
        user_id=current_user.id,
        test_id=test.id,
        score=score,
        total_questions=total,
        correct_answers=correct_count,
        wrong_topics_json=json.dumps(weak_topics, ensure_ascii=False),
        answers_json=json.dumps(answers_payload, ensure_ascii=False),
        time_spent_seconds=time_spent,
    )
    db.session.add(result)
    db.session.flush()

    ai_payload = generate_recommendation(current_user, result, wrong_items)
    recommendation = AIRecommendation(
        user_id=current_user.id,
        result_id=result.id,
        summary=_as_text(ai_payload["summary"]),
        weak_topics=_as_text(ai_payload["weak_topics"]),
        plan=_as_text(ai_payload["plan"]),
    )
    db.session.add(recommendation)
    db.session.commit()
    return result
