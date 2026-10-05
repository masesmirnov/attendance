import hashlib
import json
import os
import shutil
from pathlib import Path

from infra.common import read_json, run, write, write_json
from infra.components import content_digest

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("/home/admin/attendance")
RUNTIME = TARGET / "runtime"
ACCOUNT = TARGET / "service_account.json"
MARKER = Path("/etc/infra/attendance-deployed.json")
CONTAINER = "attendance-bot"
SERVICE_UID = 10001
TREES = ["attendance"]
FILES = ["Dockerfile", "compose.yaml", "requirements.txt", ".dockerignore"]
REQUIRED = [
    "bot_token",
    "openai_api_key",
    "google_service_account",
    "worksheet_name",
    "roster_name_col",
    "roster_start_row",
]
VARIABLES = {
    "bot_token": "BOT_TOKEN",
    "openai_api_key": "OPENAI_API_KEY",
    "openai_base_url": "OPENAI_BASE_URL",
    "openai_model": "OPENAI_MODEL",
    "default_sheet_id": "DEFAULT_SHEET_ID",
    "worksheet_name": "WORKSHEET_NAME",
    "roster_name_col": "ROSTER_NAME_COL",
    "roster_start_row": "ROSTER_START_ROW",
    "present_mark": "PRESENT_MARK",
    "absent_mark": "ABSENT_MARK",
    "admin_ids": "ADMIN_IDS",
}


def running() -> bool:
    result = run(
        ["docker", "inspect", "--format", "{{.State.Running}}", CONTAINER],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def chown_tree(target: Path, uid: int) -> None:
    os.chown(target, uid, uid)
    for child in target.rglob("*"):
        os.chown(child, uid, uid)


def replace_tree(source: Path, target: Path, uid: int = 0) -> None:
    fresh = target.with_name("." + target.name + ".new")
    if fresh.exists():
        shutil.rmtree(fresh)
    shutil.copytree(source, fresh)
    chown_tree(fresh, uid)
    if target.exists():
        shutil.rmtree(target)
    os.rename(fresh, target)


def install_file(source: Path, target: Path, mode: int, uid: int = 0) -> None:
    fresh = target.with_name("." + target.name + ".new")
    shutil.copyfile(source, fresh)
    os.chmod(fresh, mode)
    os.chown(fresh, uid, uid)
    os.replace(fresh, target)


def settings(secret: dict) -> dict:
    return secret.get("attendance") or {}


def environment(values: dict) -> str:
    return "".join(f"{name}={values[key]}\n" for key, name in VARIABLES.items() if values.get(key))


def account(values: dict) -> str:
    document = values["google_service_account"]
    return document if isinstance(document, str) else json.dumps(document)


def compose(*arguments: str) -> None:
    run(["docker", "compose", "-f", str(TARGET / "compose.yaml"), *arguments], cwd=TARGET)


def configure() -> None:
    from infra.node import secret_data

    values = settings(secret_data())
    if not all(values.get(key) for key in REQUIRED):
        print("attendance: секреты не заданы, установка пропущена", flush=True)
        return

    digest = content_digest(ROOT)
    previous = read_json(MARKER) if MARKER.exists() else {}
    rendered = environment(values)
    credentials = account(values)
    fingerprint = hashlib.sha256((rendered + credentials).encode()).hexdigest()
    unchanged = previous.get("sha256") == digest and previous.get("env") == fingerprint
    if unchanged and running():
        print("attendance: компонент " + digest[:12] + " уже установлен", flush=True)
        return

    TARGET.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(exist_ok=True)
    os.chown(RUNTIME, SERVICE_UID, SERVICE_UID)
    for name in TREES:
        replace_tree(ROOT / name, TARGET / name)
    for name in FILES:
        install_file(ROOT / name, TARGET / name, 0o644)
    write(TARGET / ".env", rendered, 0o600)
    write(ACCOUNT, credentials, 0o600)
    os.chown(ACCOUNT, SERVICE_UID, SERVICE_UID)

    compose("build")
    compose("up", "-d", "--force-recreate")
    write_json(MARKER, {"sha256": digest, "env": fingerprint})
    print("attendance: бот установлен из компонента " + digest[:12], flush=True)
