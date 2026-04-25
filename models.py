from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), default='student')  # 'student' or 'teacher'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    sessions      = db.relationship('Session', backref='user', lazy=True)
    reports       = db.relationship('ProgressReport', backref='user', lazy=True)


class Session(db.Model):
    __tablename__  = 'sessions'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic          = db.Column(db.String(100))
    session_number = db.Column(db.Integer)   # 1, 2, 3... per user
    date           = db.Column(db.DateTime, default=datetime.utcnow)

    turns          = db.relationship('Turn', backref='session', lazy=True)
    analysis       = db.relationship('SessionAnalysis', backref='session',
                                     uselist=False, lazy=True)


class Turn(db.Model):
    __tablename__   = 'turns'
    id              = db.Column(db.Integer, primary_key=True)
    session_id      = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    turn_number     = db.Column(db.Integer)
    app_question    = db.Column(db.Text)
    student_speech  = db.Column(db.Text)
    fluency_comment = db.Column(db.Text)


class SessionAnalysis(db.Model):
    __tablename__        = 'session_analysis'
    id                   = db.Column(db.Integer, primary_key=True)
    session_id           = db.Column(db.Integer, db.ForeignKey('sessions.id'),
                                     nullable=False)
    vocabulary_score     = db.Column(db.Float)
    vocabulary_note      = db.Column(db.Text)
    phrasing_score       = db.Column(db.Float)
    phrasing_note        = db.Column(db.Text)
    structure_score      = db.Column(db.Float)
    structure_note       = db.Column(db.Text)
    overall_score        = db.Column(db.Float)
    overall_note         = db.Column(db.Text)
    suggestion           = db.Column(db.Text)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)


class ProgressReport(db.Model):
    __tablename__             = 'progress_reports'
    id                        = db.Column(db.Integer, primary_key=True)
    user_id                   = db.Column(db.Integer, db.ForeignKey('users.id'),
                                          nullable=False)
    report_number             = db.Column(db.Integer)   # 1, 2, 3...
    sessions_from             = db.Column(db.Integer)   # e.g. 1
    sessions_to               = db.Column(db.Integer)   # e.g. 5
    vocabulary_score          = db.Column(db.Float)
    vocabulary_label          = db.Column(db.String(20))
    vocabulary_description    = db.Column(db.Text)
    phrasing_score            = db.Column(db.Float)
    phrasing_label            = db.Column(db.String(20))
    phrasing_description      = db.Column(db.Text)
    structure_score           = db.Column(db.Float)
    structure_label           = db.Column(db.String(20))
    structure_description     = db.Column(db.Text)
    overall_score             = db.Column(db.Float)
    overall_label             = db.Column(db.String(20))
    improvement_description   = db.Column(db.Text)
    generated_at              = db.Column(db.DateTime, default=datetime.utcnow)
