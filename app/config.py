import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _runtime_path(env_name: str, default_relative: str) -> str:
    raw = os.getenv(env_name, "").strip()
    path = Path(raw).expanduser() if raw else BASE_DIR / default_relative
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path.resolve())


def _parse_auth_users() -> list[dict[str, str]]:
    raw = os.getenv("AUTH_USERS", "").strip()
    users = []
    if raw:
        for part in raw.split(","):
            if ":" not in part:
                continue
            username, password = [value.strip() for value in part.split(":", 1)]
            if username and password:
                users.append({"username": username, "password": password, "display_name": username})
    if users:
        return users
    return [
        {
            "username": os.getenv("AUTH_USERNAME", "admin").strip(),
            "password": os.getenv("AUTH_PASSWORD", "admin123").strip(),
            "display_name": "管理员",
        }
    ]


class Config:
    APP_NAME = os.getenv("APP_NAME", "小凯哥电商进销存")
    APP_SUBTITLE = os.getenv("APP_SUBTITLE", "成品货 / 半成品 / 物料 / 包材 / 账目")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5100"))
    DATABASE_PATH = _runtime_path("DATABASE_PATH", "data/app.db")
    EXPORT_DIR = _runtime_path("EXPORT_DIR", "exports")
    AUTH_USERS = _parse_auth_users()
    RETURN_API_TOKEN = os.getenv("RETURN_API_TOKEN", "change-me").strip()
    RETURN_SYSTEM_DATABASE_PATH = os.getenv(
        "RETURN_SYSTEM_DATABASE_PATH",
        "/home/hyk/warehouse-management/data/app.db",
    ).strip()
