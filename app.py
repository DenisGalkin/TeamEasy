# **************TeamEasy**************
# By Denis Galkin
# V1.0 - BETA 2
# ************************************

# Englis / Russian

# Imports of libraries / Импорты библиотек
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Project, login_manager
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teameasy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите в аккаунт для доступа к этой странице'
login_manager.login_message_category = 'error'

# Matching category names / Сопоставление названий категорий
CATEGORIES = {
    "software-development": "Разработка программного обеспечения",
    "web-development": "Веб-разработка",
    "mobile-apps": "Мобильные приложения",
    "game-development": "Игровая разработка",
    "blockchain-cryptocurrency": "Блокчейн и криптовалюты",
    "artificial-intelligence": "Искусственный интеллект",
    "internet-of-things": "Интернет вещей",
    "cybersecurity": "Кибербезопасность",
    "data-analytics": "Аналитика данных",
    "cloud-technologies": "Облачные технологии",
    "other": "Другое"
}

# Index page / Главная страница
@app.route('/')
def index():
    return render_template('index.html')


# Registration by Flask Login / Регистрация через библиотеку Flask Login
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        github = request.form.get('github', '')
        telegram = request.form.get('telegram', '')

        if telegram and telegram.startswith('@'):
            telegram = telegram[1:]

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', category='error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Эта почта уже привязана к другому аккаунту', category='error')
            return redirect(url_for('register'))

        user = User(username=username, email=email, github=github, telegram=telegram)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Успешная регистрация', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Login / Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


# Logout / Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из аккаунта', 'success')
    return redirect(url_for('index'))


# User profile / Профиль пользователя
@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    user_projects = Project.query.filter_by(owner_id=user.id, is_public=True).order_by(Project.created_at.desc()).all()
    for project in user_projects:
        project.category_name = CATEGORIES.get(project.category, "Неизвестная категория")

    return render_template('profile.html', user=user, projects=user_projects)


# Edit profile / Редактирование профиля
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.email = request.form['email']
        current_user.github = request.form.get('github', '')
        current_user.bio = request.form.get('bio', '')
        telegram = request.form.get('telegram', '')

        if telegram and telegram.startswith('@'):
            telegram = telegram[1:]
        current_user.telegram = telegram

        existing_user = User.query.filter(User.email == current_user.email, User.id != current_user.id).first()
        if existing_user:
            flash('Эта почта уже привязана к другому аккаунту', 'error')
            return redirect(url_for('edit_profile'))

        try:
            db.session.commit()
            flash('Профиль успешно изменен', 'success')
            return redirect(url_for('profile', username=current_user.username))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при редактировании профиля: ' + str(e), 'error')

    return render_template('edit_profile.html')


# Create project / Функция создания проекта
@app.route('/create_project', methods=['GET', 'POST'])
def create_project():
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=request.url))

    if request.method == 'POST':
        project_name = request.form['project_name']
        project_description = request.form['project_description']
        github_url = request.form.get('github_url', '')
        category = request.form['category']
        is_public = request.form.get('is_public') == 'true'

        project = Project(
            name=project_name,
            description=project_description,
            github_url=github_url,
            owner_id=current_user.id,
            category=category,
            is_public=is_public
        )

        try:
            db.session.add(project)
            db.session.commit()
            flash('Проект успешно создан', 'success')
            return redirect(url_for('my_projects'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при создании проекта: ' + str(e), 'error')

    return render_template('create_project.html')


# Join project / Присоединиться к проекту
@app.route('/join_project')
def join_project():
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=request.url))
    return render_template('join_project.html')


# My projects / Мои проекты
@app.route('/my_projects')
@login_required
def my_projects():
    user_projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    for project in user_projects:
        project.category_name = CATEGORIES.get(project.category, "Неизвестная категория")
    return render_template('my_projects.html', projects=user_projects)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
