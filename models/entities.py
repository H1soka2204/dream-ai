import json
from datetime import datetime
from uuid import uuid4

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from backend import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="student")
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship("Course", backref="teacher", lazy=True)
    results = db.relationship("TestResult", backref="student", lazy=True)
    recommendations = db.relationship("AIRecommendation", backref="student", lazy=True)

    @property
    def is_active(self):
        return self.is_enabled

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    difficulty = db.Column(db.String(40), nullable=False, default="beginner")
    status = db.Column(db.String(30), default="published")
    accent = db.Column(db.String(30), default="blue")
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lessons = db.relationship(
        "Lesson", backref="course", lazy=True, cascade="all, delete-orphan"
    )
    tests = db.relationship(
        "Test", backref="course", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def progress_label(self):
        return {"beginner": "Начальный", "middle": "Средний", "advanced": "Продвинутый"}.get(
            self.difficulty, self.difficulty
        )


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=1)
    estimated_minutes = db.Column(db.Integer, default=15)


class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(40), nullable=False, default="middle")
    time_limit_minutes = db.Column(db.Integer, default=20)
    passing_score = db.Column(db.Integer, default=70)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship(
        "Question", backref="test", lazy=True, cascade="all, delete-orphan"
    )
    results = db.relationship(
        "TestResult", backref="test", lazy=True, cascade="all, delete-orphan"
    )


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(40), default="middle")
    explanation = db.Column(db.Text, default="")

    answers = db.relationship(
        "Answer", backref="question", lazy=True, cascade="all, delete-orphan"
    )


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class TestResult(db.Model):
    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    wrong_topics_json = db.Column(db.Text, default="[]")
    answers_json = db.Column(db.Text, default="[]")
    time_spent_seconds = db.Column(db.Integer, default=0)
    certificate_code = db.Column(db.String(40), default=lambda: uuid4().hex[:12].upper())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recommendation = db.relationship(
        "AIRecommendation", backref="result", lazy=True, uselist=False
    )

    @property
    def wrong_topics(self):
        try:
            return json.loads(self.wrong_topics_json or "[]")
        except json.JSONDecodeError:
            return []

    @property
    def answers_payload(self):
        try:
            return json.loads(self.answers_json or "[]")
        except json.JSONDecodeError:
            return []

    @property
    def passed(self):
        return self.score >= self.test.passing_score


class AIRecommendation(db.Model):
    __tablename__ = "ai_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    result_id = db.Column(db.Integer, db.ForeignKey("test_results.id"), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    weak_topics = db.Column(db.Text, default="")
    plan = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
