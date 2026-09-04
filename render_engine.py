"""Cached OpenSCAD rendering and automatic temporary-file housekeeping."""

import hashlib
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CACHE_DIR = PROJECT_DIR / ".render_cache"
CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
CACHE_MAX_FILES = 400
SESSION_ROOT = PROJECT_DIR / ".session_jobs"
_RENDER_THREAD_LOCK = threading.Lock()


def _cache_key(scad_bytes: bytes, output_suffix: str) -> str:
    digest = hashlib.sha256()
    digest.update(b"studio-render-cache-v1\0")
    digest.update(output_suffix.lower().encode("ascii", errors="ignore"))
    digest.update(b"\0")
    digest.update(scad_bytes)
    # SVG imports are external dependencies. Include their bytes so replacing
    # an icon at the same path invalidates the old cached STL automatically.
    source_text = scad_bytes.decode("utf-8", errors="ignore")
    dependencies = set(re.findall(r'import\s*\(\s*file\s*=\s*"([^"]+)"', source_text))
    dependencies.update(re.findall(r'"([^"]+\.svg)"', source_text, flags=re.IGNORECASE))
    for dependency in sorted(dependencies):
        dependency_path = Path(dependency)
        if dependency_path.is_file():
            try:
                digest.update(b"\0dependency\0")
                digest.update(str(dependency_path).encode("utf-8"))
                digest.update(dependency_path.read_bytes())
            except OSError:
                pass
    return digest.hexdigest()


def cleanup_directory(directory, max_age_seconds=24 * 60 * 60, max_files=120):
    """Delete only old generated SCAD/STL/OBJ files from a known work folder."""
    path = Path(directory).resolve()
    if not path.is_dir():
        return
    allowed = {".scad", ".stl", ".obj"}
    files = [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in allowed]
    now = time.time()
    for item in files:
        try:
            if now - item.stat().st_mtime > max_age_seconds:
                item.unlink()
        except OSError:
            pass
    remaining = sorted(
        (item for item in path.iterdir() if item.is_file() and item.suffix.lower() in allowed),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for item in remaining[max_files:]:
        try:
            item.unlink()
        except OSError:
            pass


def session_workdir(page_key):
    """Return an isolated render folder for the current Streamlit session."""
    import streamlit as st

    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    state_key = "studio_render_session_id"
    if state_key not in st.session_state:
        st.session_state[state_key] = uuid.uuid4().hex
    safe_page_key = re.sub(r"[^a-zA-Z0-9_-]", "_", str(page_key))
    workdir = SESSION_ROOT / st.session_state[state_key] / safe_page_key
    workdir.mkdir(parents=True, exist_ok=True)

    # Remove only stale generated session directories under the known root.
    cutoff = time.time() - (12 * 60 * 60)
    for session_dir in SESSION_ROOT.iterdir():
        try:
            if session_dir.is_dir() and session_dir.stat().st_mtime < cutoff:
                shutil.rmtree(session_dir)
        except OSError:
            pass
    try:
        os.utime(workdir.parent, None)
    except OSError:
        pass
    return str(workdir)


def _prune_cache():
    cleanup_directory(CACHE_DIR, CACHE_MAX_AGE_SECONDS, CACHE_MAX_FILES)


def _render_openscad_unlocked(openscad_exe, scad_path, output_path, timeout=120):
    """Render once per unique SCAD source, then reuse the cached result."""
    scad_path = Path(scad_path).resolve()
    output_path = Path(output_path).resolve()
    scad_bytes = scad_path.read_bytes()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(scad_bytes, output_path.suffix)
    cached_path = CACHE_DIR / f"{key}{output_path.suffix.lower()}"
    lock_path = CACHE_DIR / f"{key}.lock"

    with lock_path.open("a+b") as lock_handle:
        try:
            import fcntl

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        try:
            if cached_path.is_file() and cached_path.stat().st_size > 0:
                shutil.copy2(cached_path, output_path)
                return {"cached": True, "path": str(output_path)}

            temp_cached = CACHE_DIR / f"{key}.{os.getpid()}.tmp{output_path.suffix.lower()}"
            command = [str(openscad_exe), "-o", str(temp_cached), str(scad_path)]
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            if not temp_cached.is_file() or temp_cached.stat().st_size == 0:
                raise RuntimeError("OpenSCAD did not create a usable output file")
            os.replace(temp_cached, cached_path)
            shutil.copy2(cached_path, output_path)
            return {
                "cached": False,
                "path": str(output_path),
                "stderr": completed.stderr.decode("utf-8", errors="ignore"),
            }
        finally:
            try:
                import fcntl

                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            _prune_cache()


def render_openscad(openscad_exe, scad_path, output_path, timeout=120):
    """Queue CPU-heavy OpenSCAD work within this server process."""
    with _RENDER_THREAD_LOCK:
        return _render_openscad_unlocked(openscad_exe, scad_path, output_path, timeout)


def render_gate(scad_sources, key):
    """Allow each Streamlit rerun to render the current settings immediately."""
    import streamlit as st

    if isinstance(scad_sources, str):
        scad_sources = [scad_sources]
    digest = hashlib.sha256()
    for source in scad_sources:
        digest.update(str(source).encode("utf-8"))
        digest.update(b"\0")
    signature = digest.hexdigest()
    state_key = f"render_signature_{key}"
    st.session_state[state_key] = signature
    return signature
