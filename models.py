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
    projects = db.relationship('Project', backref='owner', lazy=True)
    project_memberships = db.relationship('ProjectMember', backref='user', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))

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
    members = db.relationship('ProjectMember', backref='project', lazy=True)


# Project Member / Участник проекта
class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(100), default='Участник')
    joined_at = db.Column(db.DateTime, default=datetime.now(timezone(timedelta(hours=3))))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
