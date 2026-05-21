from backend import db
from models import AIRecommendation, TestResult


def _delete_recommendations_for_test_ids(test_ids):
    if not test_ids:
        return

    result_ids = [
        result_id
        for (result_id,) in TestResult.query.with_entities(TestResult.id)
        .filter(TestResult.test_id.in_(test_ids))
        .all()
    ]
    if result_ids:
        AIRecommendation.query.filter(
            AIRecommendation.result_id.in_(result_ids)
        ).delete(synchronize_session=False)


def delete_test_with_related_data(test):
    _delete_recommendations_for_test_ids([test.id])
    db.session.delete(test)


def delete_course_with_related_data(course):
    _delete_recommendations_for_test_ids([test.id for test in course.tests])
    db.session.delete(course)
