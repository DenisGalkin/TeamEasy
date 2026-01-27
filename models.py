from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from datetime import datetime, timezone, timedelta

db = SQLAlchemy()
login_manager = LoginManager()

# Profile photo / Фото профиля
PROFILE_PHOTO_FOLDER = 'static/uploads/profile_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# User / Пользователь
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    github = db.Column(db.String(120))
    telegram = db.Column(db.String(33))
    discord = db.Column(db.String(32))
    bio = db.Column(db.String(500))
    password_hash = db.Column(db.String(128))
    profile_photo = db.Column(db.String(255), default='default-avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True)
    project_memberships = db.relationship('ProjectMember', back_populates='user', lazy=True)
    join_requests = db.relationship('JoinRequest', back_populates='user', lazy=True)
    notifications = db.relationship('Notification', back_populates='user', lazy=True)
    created_tasks = db.relationship('Task', foreign_keys='Task.created_by', back_populates='creator', lazy=True)
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assigned_to', back_populates='assignee', lazy=True)
    created_events = db.relationship('Event', back_populates='creator', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_profile_photo_url(self):
        if self.profile_photo and self.profile_photo != 'default-avatar.png':
            return f'/static/uploads/profile_photos/{self.profile_photo}'
        return '/static/images/default-avatar.png'


# Project / Проект
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    github_url = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))
    category = db.Column(db.String(40), nullable=False)
    is_public = db.Column(db.Boolean, default=True)

    # Relationships
    members = db.relationship('ProjectMember', back_populates='project', lazy=True, cascade='all, delete-orphan')
    join_requests = db.relationship('JoinRequest', back_populates='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='project', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='project', lazy=True, cascade='all, delete-orphan')


# Project Member / Участник проекта
class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(100), default='Участник')
    joined_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

    # Relationships
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', back_populates='project_memberships')


# Tasks / Задачи
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    due_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, done
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    project = db.relationship('Project', back_populates='tasks')
    assignee = db.relationship('User', foreign_keys=[assigned_to], back_populates='assigned_tasks')
    creator = db.relationship('User', foreign_keys=[created_by], back_populates='created_tasks')


# Events / События
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

    # Relationships
    project = db.relationship('Project', back_populates='events')
    creator = db.relationship('User', back_populates='created_events')


# Join Request / Запрос на присоединение
class JoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

    # Relationships
    project = db.relationship('Project', back_populates='join_requests')
    user = db.relationship('User', back_populates='join_requests')


# Notification / Уведомление
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)  # join_request, join_result, etc.
    related_id = db.Column(db.Integer)  # ID связанного объекта (join_request, project, etc.)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

    # Relationships
    user = db.relationship('User', back_populates='notifications')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))