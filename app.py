# **************TeamEasy**************
# By Denis Galkin
# V1.0 - BETA 5
# ************************************

# English / Russian

# Imports of libraries / Импорты библиотек
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Project, login_manager, ProjectMember, allowed_file, MAX_FILE_SIZE
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teameasy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROFILE_PHOTO_FOLDER'] = 'static/uploads/profile_photos'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB

os.makedirs(app.config['PROFILE_PHOTO_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

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


@app.context_processor
def inject_categories():
    return dict(CATEGORIES=CATEGORIES)


# Files upload folder / Папка загрузки файлов
@app.route('/static/uploads/profile_photos/<filename>')
def serve_profile_photo(filename):
    return send_from_directory(app.config['PROFILE_PHOTO_FOLDER'], filename)


# Index page / Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('index.html')


# Home page / Домашняя страница
@app.route('/home')
@login_required
def home():
    return render_template('home.html')


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
        discord = request.form.get('discord', '')

        if telegram and telegram.startswith('@'):
            telegram = telegram[1:]

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', category='error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Эта почта уже привязана к другому аккаунту', category='error')
            return redirect(url_for('register'))

        user = User(username=username, email=email, github=github, telegram=telegram, discord=discord)
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

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                if file.content_length > MAX_FILE_SIZE:
                    flash('Файл слишком большой. Максимальный размер - 2MB.', 'error')
                else:
                    # Delete old profile photo if it exists and is not default
                    if current_user.profile_photo and current_user.profile_photo != 'default-avatar.png':
                        old_photo_path = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], current_user.profile_photo)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)

                    # Save new profile photo
                    filename = secure_filename(f"{current_user.id}_{file.filename}")
                    file.save(os.path.join(app.config['PROFILE_PHOTO_FOLDER'], filename))
                    current_user.profile_photo = filename
            elif file and file.filename != '':
                flash('Недопустимый формат файла. Разрешены: PNG, JPG, JPEG, GIF.', 'error')

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


# Delete profile photo / Удаление фото профиля
@app.route('/delete_profile_photo', methods=['POST'])
@login_required
def delete_profile_photo():
    if current_user.profile_photo and current_user.profile_photo != 'default-avatar.png':
        photo_path = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], current_user.profile_photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)

        current_user.profile_photo = 'default-avatar.png'
        db.session.commit()
        flash('Фото профиля удалено', 'success')
    else:
        flash('Нет фото для удаления', 'error')

    return redirect(url_for('edit_profile'))


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
            db.session.flush()

            owner_member = ProjectMember(
                project_id=project.id,
                user_id=current_user.id,
                role='Владелец'
            )
            db.session.add(owner_member)

            db.session.commit()
            flash('Проект успешно создан', 'success')
            return redirect(url_for('my_projects'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при создании проекта: ' + str(e), 'error')

    return render_template('create_project.html')


# My projects / Мои проекты
@app.route('/my_projects')
@login_required
def my_projects():
    user_projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    for project in user_projects:
        project.category_name = CATEGORIES.get(project.category, "Неизвестная категория")
    return render_template('my_projects.html', projects=user_projects)


# Project workspace / Рабочее пространство проекта
@app.route('/project/<int:project_id>/workspace')
@login_required
def project_workspace(project_id):
    project = Project.query.get_or_404(project_id)

    is_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    if not is_member and project.owner_id != current_user.id:
        flash('У вас нет доступа к этому проекту', 'error')
        return redirect(url_for('my_projects'))

    return render_template('project_workspace.html', project=project)


# Project members / Участники проекта
@app.route('/project/<int:project_id>/members')
@login_required
def project_members(project_id):
    project = Project.query.get_or_404(project_id)

    is_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    if not is_member and project.owner_id != current_user.id:
        flash('У вас нет доступа к этому проекту', 'error')
        return redirect(url_for('my_projects'))

    members = ProjectMember.query.filter_by(project_id=project_id).all()

    return render_template('project_members.html', project=project, members=members)


# Edit role / Изменение роли участника
@app.route('/project/<int:project_id>/members/<int:member_id>/edit_role', methods=['POST'])
@login_required
def edit_member_role(project_id, member_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash('Только владелец проекта может изменять роли участников', 'error')
        return redirect(url_for('project_members', project_id=project_id))

    member = ProjectMember.query.get_or_404(member_id)
    new_role = request.form.get('role', '').strip()

    if new_role:
        member.role = new_role
        try:
            db.session.commit()
            flash('Роль участника успешно обновлена', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при изменении роли: ' + str(e), 'error')

    return redirect(url_for('project_members', project_id=project_id))


# Remove member / Удаление участника
@app.route('/project/<int:project_id>/members/<int:member_id>/remove', methods=['POST'])
@login_required
def remove_member(project_id, member_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash('Только владелец проекта может удалять участников', 'error')
        return redirect(url_for('project_members', project_id=project_id))

    member = ProjectMember.query.get_or_404(member_id)

    try:
        db.session.delete(member)
        db.session.commit()
        flash('Участник удален из проекта', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении участника: ' + str(e), 'error')

    return redirect(url_for('project_members', project_id=project_id))


# Project settings / Настройки проекта
@app.route('/project/<int:project_id>/settings', methods=['GET', 'POST'])
@login_required
def project_settings(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash('Только владелец проекта может изменять настройки', 'error')
        return redirect(url_for('project_workspace', project_id=project_id))

    if request.method == 'POST':
        project.name = request.form['project_name']
        project.description = request.form['project_description']
        project.github_url = request.form.get('github_url', '')
        project.category = request.form['category']
        project.is_public = request.form.get('is_public') == 'true'

        try:
            db.session.commit()
            flash('Настройки проекта изменены', 'success')
            return redirect(url_for('project_settings', project_id=project_id))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении настроек: ' + str(e), 'error')

    return render_template('project_settings.html', project=project)


# Delete project / Удаление проекта
@app.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash('Только владелец проекта может удалить проект', 'error')
        return redirect(url_for('project_workspace', project_id=project_id))

    try:
        ProjectMember.query.filter_by(project_id=project_id).delete()
        db.session.delete(project)
        db.session.commit()
        flash('Проект удален', 'success')
        return redirect(url_for('my_projects'))
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении проекта: ' + str(e), 'error')
        return redirect(url_for('project_settings', project_id=project_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
