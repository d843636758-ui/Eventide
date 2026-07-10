import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from eventide import EventideRuntime


DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
STATE_FILE = DATA_DIR / "eventide_state.json"

_runtime = EventideRuntime()
_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_default_state() -> Dict[str, Any]:
    state = _runtime.create_state(_utc_now())
    return _runtime.dump_state(state)


def load_state() -> Dict[str, Any]:
    ensure_storage()

    with _lock:
        if not STATE_FILE.exists():
            state_data = create_default_state()
            _write_state_unlocked(state_data)
            return state_data

        try:
            with STATE_FILE.open("r", encoding="utf-8") as file:
                state_data = json.load(file)

            if not isinstance(state_data, dict):
                raise ValueError("状态文件内容不是对象")

            _runtime.load_state(state_data)
            return state_data

        except Exception:
            backup_corrupted_state()
            state_data = create_default_state()
            _write_state_unlocked(state_data)
            return state_data


def save_state(state_data: Dict[str, Any]) -> Dict[str, Any]:
    ensure_storage()

    if not isinstance(state_data, dict):
        raise TypeError("state_data 必须是字典")

    state = _runtime.load_state(state_data)
    normalized_state = _runtime.dump_state(state)

    with _lock:
        _write_state_unlocked(normalized_state)

    return normalized_state


def reset_state() -> Dict[str, Any]:
    state_data = create_default_state()

    with _lock:
        ensure_storage()
        _write_state_unlocked(state_data)

    return state_data


def backup_corrupted_state() -> None:
    if not STATE_FILE.exists():
        return

    timestamp = _utc_now().strftime("%Y%m%d_%H%M%S")
    backup_file = DATA_DIR / f"eventide_state_corrupted_{timestamp}.json"

    try:
        STATE_FILE.replace(backup_file)
    except OSError:
        pass


def get_state_file_path() -> str:
    return str(STATE_FILE)


def _write_state_unlocked(state_data: Dict[str, Any]) -> None:
    temporary_file = STATE_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            state_data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.flush()
        os.fsync(file.fileno())

    temporary_file.replace(STATE_FILE)
