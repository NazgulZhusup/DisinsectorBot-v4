from flask import Blueprint, render_template, redirect, url_for, session, flash, request, current_app
from flask_login import login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.model import Admin, Disinsector
from app import db
from sqlalchemy.exc import IntegrityError
from app.forms import RegisterDisinsectorForm, RegisterAdminForm, LoginAdminForm, LoginDisinsectorForm
import random
import string

auth_bp = Blueprint('auth', __name__)

# Регистрация администратора
@auth_bp.route('/admin/register_admin', methods=['GET', 'POST'])
def admin_register():
    form = RegisterAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        confirm_password = form.confirm_password.data

        current_app.logger.info(f"Попытка регистрации администратора с email: {email}")

        if password != confirm_password:
            flash('Пароли не совпадают.', 'danger')
            current_app.logger.warning(f"Пароли не совпадают для email: {email}")
            return redirect(url_for('auth.admin_register'))

        hashed_password = generate_password_hash(password)

        new_admin = Admin(email=email, password=hashed_password)

        try:
            db.session.add(new_admin)
            db.session.commit()
            flash('Администратор успешно зарегистрирован!', 'success')
            current_app.logger.info(f"Администратор с email {email} успешно зарегистрирован.")
            return redirect(url_for('auth.admin_login'))
        except IntegrityError:
            db.session.rollback()
            flash('Администратор с таким email уже существует.', 'danger')
            current_app.logger.error(f"Администратор с email {email} уже существует.")
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации.', 'danger')
            current_app.logger.error(f"Ошибка при регистрации администратора: {e}")

    return render_template('admin_register.html', form=form)

# Вход для администратора
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        try:
            admin = Admin.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password, password):
                session['admin_id'] = admin.id
                login_user(admin)
                current_app.logger.info(f"Администратор {admin.email} вошел в систему.")
                return redirect(url_for('main.admin_dashboard'))
            else:
                flash("Неверный email или пароль.", 'danger')
                current_app.logger.warning(f"Неудачная попытка входа для email: {email}")
        except Exception as e:
            current_app.logger.error(f"Ошибка при входе администратора: {e}")
            flash("Произошла ошибка. Пожалуйста, попробуйте позже.", 'danger')

    return render_template('admin_login.html', form=form)

# Регистрация дезинсектора (только для администратора)

def generate_short_id(length=6):
    """Генерирует случайный уникальный ID длиной length."""
    characters = string.ascii_uppercase + string.digits  # Используем заглавные буквы и цифры
    return ''.join(random.choices(characters, k=length))

@auth_bp.route('/admin/register_disinsector', methods=['GET', 'POST'])
def register_disinsector():
    if not isinstance(current_user, Admin):
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('auth.admin_login'))

    form = RegisterDisinsectorForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.strip().lower()
        token = form.token.data.strip()
        password = form.password.data

        current_app.logger.info(f"Попытка регистрации дезинсектора с email: {email}")

        existing_disinsector = Disinsector.query.filter_by(email=email).first()
        if existing_disinsector:
            flash('Дезинсектор с таким email уже существует.', 'danger')
            current_app.logger.warning(f"Дезинсектор с email {email} уже существует.")
            return redirect(url_for('auth.register_disinsector'))

        # Генерация уникального короткого disinsector_id
        disinsector_id = None
        while disinsector_id is None or Disinsector.query.filter_by(disinsector_id=disinsector_id).first():
            disinsector_id = generate_short_id()

        # Создаем нового дезинсектора
        new_disinsector = Disinsector(
            name=name,
            email=email,
            token=token,
            password=generate_password_hash(password),
            disinsector_id=disinsector_id  # Сохраняем короткий disinsector_id
        )

        try:
            db.session.add(new_disinsector)
            db.session.commit()
            flash(f"Дезинсектор {name} успешно зарегистрирован! ID: {disinsector_id}", 'success')
            current_app.logger.info(f"Дезинсектор с email {email} успешно зарегистрирован. ID: {disinsector_id}")
            return redirect(url_for('main.admin_dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash('Дезинсектор с таким email уже существует.', 'danger')
            current_app.logger.error(f"Дезинсектор с email {email} уже существует.")
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации.', 'danger')
            current_app.logger.error(f"Ошибка при регистрации дезинсектора: {e}")

    return render_template('register_disinsector.html', form=form)

# Вход для дезинсектора
@auth_bp.route('/login', methods=['GET', 'POST'])
def disinsector_login():
    form = LoginDisinsectorForm()
    if request.method == 'POST':
        disinsector_id = request.form.get('disinsector_id').strip()
        password = request.form.get('password').strip()

        disinsector = Disinsector.query.filter_by(disinsector_id=disinsector_id).first()

        # Проверяем, существует ли дезинсектор и совпадает ли токен
        if disinsector and check_password_hash(disinsector.password, password):
            # Авторизуем дезинсектора
            login_user(disinsector)
            flash(f"Добро пожаловать, {disinsector.name}!", 'success')
            current_app.logger.info(f"Попытка входа: disinsector_id={disinsector_id}, password={password}")
            current_app.logger.info(f"Дезинсектор {disinsector.name} (ID: {disinsector.id}) успешно вошел в систему.")
            return redirect(url_for('main.disinsector_dashboard'))
        else:
            flash('Неверный disinsector_id или пароль.', 'danger')
            current_app.logger.warning(f"Неудачная попытка входа для disinsector_id: {disinsector_id}")

    return render_template('disinsector_login.html', form=form)


# Выход из системы
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('main.index'))
