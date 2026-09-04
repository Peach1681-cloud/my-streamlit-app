"""Concurrency-safe login and export counters for the studio."""

import json
import os
import threading
from pathlib import Path


ANALYTICS_FILE = Path(__file__).resolve().parent / "analytics_data.json"
LOCK_FILE = ANALYTICS_FILE.with_suffix(".lock")
DEFAULT_DATA = {"total_logins": 0, "total_exports": 0, "project_exports": {}}
_THREAD_LOCK = threading.Lock()


def _normalise(data):
    if not isinstance(data, dict):
        data = {}
    return {
        "total_logins": int(data.get("total_logins", 0) or 0),
        "total_exports": int(data.get("total_exports", 0) or 0),
        "project_exports": dict(data.get("project_exports", {}) or {}),
    }


def _read_unlocked():
    try:
        with ANALYTICS_FILE.open("r", encoding="utf-8") as handle:
            return _normalise(json.load(handle))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_DATA)


def _write_unlocked(data):
    temp_file = ANALYTICS_FILE.with_suffix(f".{os.getpid()}.tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(_normalise(data), handle, ensure_ascii=False, indent=4)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_file, ANALYTICS_FILE)


def _locked_update(callback):
    """Lock across Streamlit sessions before a read-modify-write cycle."""
    with _THREAD_LOCK:
        LOCK_FILE.touch(exist_ok=True)
        with LOCK_FILE.open("r+", encoding="utf-8") as lock_handle:
            try:
                import fcntl

                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
            try:
                data = _read_unlocked()
                callback(data)
                _write_unlocked(data)
                return data
            finally:
                try:
                    import fcntl

                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass


def load_analytics():
    return _read_unlocked()


def record_login():
    def update(data):
        data["total_logins"] = int(data.get("total_logins", 0)) + 1

    return _locked_update(update)


def record_export(project_name):
    """Count one successful click on a download button."""
    project_name = str(project_name).strip() or "unknown"

    def update(data):
        data["total_exports"] = int(data.get("total_exports", 0)) + 1
        projects = data.setdefault("project_exports", {})
        projects[project_name] = int(projects.get(project_name, 0)) + 1

    return _locked_update(update)
