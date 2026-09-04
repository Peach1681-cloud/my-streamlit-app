"""SVG icon catalog shared by the Text Keychain generator."""

from pathlib import Path


ICON_DIR = Path(__file__).resolve().parent / "icon"

_FEATURED_ICONS = {
    "None": None,
    "⚡ Lightning Bolt": "bolt-solid-full.svg",
    "🍀 Clover": "clover-solid-full.svg",
    "❤️ Heart": "heart-solid-full.svg",
    "☕ Ko-fi": "ko-fi-brands-solid-full.svg",
    "🎵 Music Note": "music-solid-full.svg",
    "🕉️ Om": "om-solid-full.svg",
    "⭐ Star": "star-solid-full.svg",
    "🪄 Magic Wand & Sparkles": "wand-magic-sparkles-solid-full.svg",
    "👑 Web Awesome": "web-awesome-brands-solid-full.svg",
    "☯️ Yin Yang": "yin-yang-solid-full.svg",
}


def _display_name(filename: str) -> str:
    """Turn a Font Awesome filename into a friendly menu label."""
    stem = Path(filename).stem
    for suffix in ("-brands-solid-full", "-regular-full", "-solid-full", "-full"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return "🔹 " + stem.replace("-", " ").title()


def _build_catalog():
    # Featured items stay at the top; every other SVG dropped into /icon is
    # discovered automatically on the next app restart.
    catalog = dict(_FEATURED_ICONS)
    known_files = {name for name in catalog.values() if name}
    if ICON_DIR.is_dir():
        for path in sorted(ICON_DIR.glob("*.svg")):
            if path.name not in known_files:
                catalog[_display_name(path.name)] = path.name
    return catalog


ICON_CHOICES = _build_catalog()


def get_icon_path(choice: str) -> str:
    """Return an OpenSCAD-safe absolute path, or an empty string for None."""
    filename = ICON_CHOICES.get(choice)
    if not filename:
        return ""
    path = ICON_DIR / filename
    return path.resolve().as_posix() if path.is_file() else ""
