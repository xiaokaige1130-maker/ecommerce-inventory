from flask import Flask

from .config import Config
from .data.database import ensure_directories, init_db
from .data.repositories import ensure_default_users
from .routes.main import main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    ensure_directories(app.config)
    init_db(app.config["DATABASE_PATH"])
    ensure_default_users(app.config["DATABASE_PATH"], app.config["AUTH_USERS"])
    app.register_blueprint(main_bp)
    return app
