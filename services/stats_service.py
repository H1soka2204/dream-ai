from collections import Counter

from sqlalchemy import func

from models import Course, Test, TestResult, User


def platform_overview():
    avg_score = TestResult.query.with_entities(func.avg(TestResult.score)).scalar() or 0
    role_counts = Counter(user.role for user in User.query.all())
    return {
        "users": User.query.count(),
        "courses": Course.query.count(),
        "tests": Test.query.count(),
        "results": TestResult.query.count(),
        "avg_score": round(avg_score, 1),
        "roles": dict(role_counts),
    }


def student_overview(user):
    results = (
        TestResult.query.filter_by(user_id=user.id)
        .order_by(TestResult.created_at.desc())
        .all()
    )
    avg_score = round(sum(result.score for result in results) / len(results), 1) if results else 0
    best_score = round(max([result.score for result in results], default=0), 1)
    passed_count = sum(1 for result in results if result.passed)
    weak_counter = Counter()
    for result in results:
        weak_counter.update(result.wrong_topics)
    chart = [
        {
            "label": result.created_at.strftime("%d.%m"),
            "value": round(result.score, 1),
            "test": result.test.title,
        }
        for result in reversed(results[:8])
    ]
    return {
        "results": results,
        "avg_score": avg_score,
        "best_score": best_score,
        "passed_count": passed_count,
        "weak_topics": weak_counter.most_common(5),
        "chart": chart,
    }


def teacher_overview(teacher_id):
    courses = Course.query.filter_by(teacher_id=teacher_id).all()
    tests = Test.query.filter_by(teacher_id=teacher_id).all()
    test_ids = [test.id for test in tests]
    results = TestResult.query.filter(TestResult.test_id.in_(test_ids)).all() if test_ids else []
    avg_score = round(sum(result.score for result in results) / len(results), 1) if results else 0
    return {
        "courses": courses,
        "tests": tests,
        "results": results,
        "avg_score": avg_score,
        "students_count": len({result.user_id for result in results}),
    }
