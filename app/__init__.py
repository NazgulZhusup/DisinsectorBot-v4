import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from database import db

csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Замените на безопасный ключ
    jwt = JWTManager(app)

    # Загрузка переменных окружения
    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(basedir, '..', '.env'))

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Настройка исключения CSRF для API
    with app.app_context():
        from app.api import api_bp
        csrf.exempt(api_bp)  # Отключение CSRF для маршрутов API

    # Настройка Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.disinsector_login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.model import Admin, Disinsector  # Ленивая загрузка моделей
        # Проверка, является ли пользователь администратором
        admin = Admin.query.get(user_id)
        if admin:
            return admin
        disinsector = Disinsector.query.get(int(user_id))
        if disinsector:
            return disinsector

        return None

    # Импорт моделей (для обнаружения Flask-Migrate)
    from app.model import Admin, Disinsector, Client, Order

    # Настройка логирования
    setup_logging(app)

    # Регистрация Blueprint'ов
    register_blueprints(app)

    return app

def setup_logging(app):
    """Настройка логирования приложения."""
    if not app.debug and not app.testing:
        log_file = app.config.get('LOG_FILE', 'app.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

        # StreamHandler для вывода логов в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('DisinsectorBot-v3 startup')


    logging.basicConfig(level=logging.DEBUG)
    app.logger.info("Сервер запущен")

def register_blueprints(app):
    """Регистрация Blueprint'ов."""
    with app.app_context():
        from app.api import api_bp
        from app.auth import auth_bp
        from app.main import main_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
