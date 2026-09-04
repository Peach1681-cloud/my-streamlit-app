"""Live SVG catalog: rescans the icon folder on every Streamlit rerun."""

from pathlib import Path


ICON_DIR = Path(__file__).resolve().parent / "icon"

FEATURED_ICONS = {
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
    stem = Path(filename).stem
    for suffix in ("-brands-solid-full", "-regular-full", "-solid-full", "-full"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return "🔹 " + stem.replace("-", " ").title()


def get_icon_choices() -> dict[str, str | None]:
    """Build a fresh catalog so newly uploaded SVG files appear immediately."""
    catalog = dict(FEATURED_ICONS)
    known_files = {filename for filename in catalog.values() if filename}
    if ICON_DIR.is_dir():
        for path in sorted(ICON_DIR.iterdir(), key=lambda item: item.name.lower()):
            if path.is_file() and path.suffix.lower() == ".svg" and path.name not in known_files:
                catalog[_display_name(path.name)] = path.name
    return catalog


def get_icon_path(choice: str) -> str:
    filename = get_icon_choices().get(choice)
    if not filename:
        return ""
    path = ICON_DIR / filename
    return path.resolve().as_posix() if path.is_file() else ""
