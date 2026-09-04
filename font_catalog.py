"""Single source of truth for multilingual 3D fonts used by every studio."""

import os
import platform
from pathlib import Path


GLOBAL_FONT_DICT = {
    "🇹🇭 ไทย / Thai — Kanit": "Kanit:style=Regular",
    "🇹🇭 ไทย / Thai — Prompt": "Prompt:style=Regular",
    "🇹🇭 ไทย / Thai — Sarabun Bold": "Sarabun:style=Bold",
    "🌐 English / Latin — Montserrat": "Montserrat:style=Regular",
    "🌐 English / Latin — Roboto Condensed": "Roboto Condensed:style=Regular",
    "🌐 English / Latin — Pacifico": "Pacifico:style=Regular",
    "🇰🇷 한국어 / Korean — Regular": "Noto Sans KR:style=Regular",
    "🇰🇷 한국어 / Korean — Bold": "Noto Sans KR:style=Bold",
    "🇰🇷 한국어 / Korean — Black": "Noto Sans KR:style=Black",
    "🇯🇵 日本語 / Japanese — Regular": "Noto Sans JP:style=Regular",
    "🇯🇵 日本語 / Japanese — Bold": "Noto Sans JP:style=Bold",
    "🇯🇵 日本語 / Japanese — Black": "Noto Sans JP:style=Black",
    "🇨🇳 中文 / Chinese — Regular": "Noto Sans SC:style=Regular",
    "🇨🇳 中文 / Chinese — Bold": "Noto Sans SC:style=Bold",
    "🇨🇳 中文 / Chinese — Black": "Noto Sans SC:style=Black",
    "🇮🇳 हिन्दी / Hindi — Regular": "Noto Sans Devanagari Condensed:style=Regular",
    "🇮🇳 हिन्दी / Hindi — Bold": "Noto Sans Devanagari Condensed:style=Bold",
    "🇮🇳 हिन्दी / Hindi — Black": "Noto Sans Devanagari Condensed:style=Black",
    "🇸🇦 العربية / Arabic — Regular": "Noto Sans Arabic ExtraCondensed:style=Regular",
    "🇸🇦 العربية / Arabic — Bold": "Noto Sans Arabic ExtraCondensed:style=Bold",
    "🇸🇦 العربية / Arabic — Black": "Noto Sans Arabic ExtraCondensed:style=Black",
}

GLOBAL_FONT_OPTIONS = list(GLOBAL_FONT_DICT)
LANGUAGE_FONT_EXAMPLES = "รองรับ: ไทย • English • 한국어 • 日本語 • 中文 • हिन्दी • العربية"


def register_bundled_fonts():
    """Expose the bundled TTF files to child OpenSCAD processes."""
    font_dir = Path(__file__).resolve().parent / "GLOBAL_FONT_DICT"
    if not font_dir.is_dir():
        return

    if platform.system() in {"Linux", "Darwin"}:
        config_file = font_dir / "local-fonts.conf"
        xml = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
            f'  <dir>{font_dir.as_posix()}</dir>\n'
            '</fontconfig>\n'
        )
        try:
            if not config_file.exists() or config_file.read_text(encoding="utf-8") != xml:
                config_file.write_text(xml, encoding="utf-8")
            os.environ["FONTCONFIG_FILE"] = str(config_file)
        except OSError:
            pass
    elif platform.system() == "Windows":
        try:
            import ctypes

            for font_file in font_dir.glob("*.ttf"):
                ctypes.windll.gdi32.AddFontResourceExW(str(font_file), 0, 0)
        except (AttributeError, OSError):
            pass


register_bundled_fonts()
