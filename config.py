import os
import platform
from pathlib import Path

PASSCODE_CORRECT = "1681"

# The labels are intentionally bilingual and include a flag so every generator
# gets the same clear language picker without duplicating configuration.
GLOBAL_FONT_DICT = {
    "🇹🇭 ไทย / Thai — Kanit": "Kanit:style=Regular",
    "🇹🇭 ไทย / Thai — Prompt": "Prompt:style=Regular",
    "🇹🇭 ไทย / Thai — Sarabun Bold": "Sarabun:style=Bold",
    "🌐 Latin — Montserrat": "Montserrat:style=Regular",
    "🌐 Latin — Roboto Condensed": "Roboto Condensed:style=Regular",
    "🌐 Latin — Pacifico": "Pacifico:style=Regular",

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

LANGUAGE_FONT_EXAMPLES = (
    "ตัวอย่าง: ไทย • 한국어 • 日本語 • 中文 • हिन्दी • العربية"
)


def register_local_fonts():
    """Make bundled fonts visible to OpenSCAD without a manual install.

    Linux/OpenSCAD uses Fontconfig, so a small project-local configuration is
    inherited by every OpenSCAD subprocess. On Windows the fonts are registered
    for the current desktop session. A failure is non-fatal: installed system
    fonts remain available as before.
    """
    font_dir = Path(__file__).resolve().parent / "GLOBAL_FONT_DICT"
    if not font_dir.is_dir():
        return

    system = platform.system()
    if system in {"Linux", "Darwin"}:
        fontconfig_file = font_dir / "local-fonts.conf"
        xml = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
            f'  <dir>{font_dir.as_posix()}</dir>\n'
            '</fontconfig>\n'
        )
        try:
            if not fontconfig_file.exists() or fontconfig_file.read_text(encoding="utf-8") != xml:
                fontconfig_file.write_text(xml, encoding="utf-8")
            os.environ["FONTCONFIG_FILE"] = str(fontconfig_file)
        except OSError:
            pass
    elif system == "Windows":
        try:
            import ctypes

            add_font = ctypes.windll.gdi32.AddFontResourceExW
            for font_path in font_dir.glob("*.ttf"):
                add_font(str(font_path), 0, 0)
        except (AttributeError, OSError):
            pass


register_local_fonts()

ICON_CHOICES = {
    "None": "",
    "Heart ❤️": "heart",
    "Star ⭐": "star",
    "Smile 😊": "smile",
    "Home 🏠": "home"
}

HAS_QR_LIBS = True

def build_threejs_viewer(*args, **kwargs):
    import streamlit as st
    import streamlit.components.v1 as components
    
    stl_path = args[0] if args else kwargs.get('stl_path', None)
    bg_color = kwargs.get('bg_color', '#1a1a1a')
    
    stl_content = ""
    if stl_path and os.path.exists(stl_path):
        try:
            with open(stl_path, "r", encoding="utf-8", errors="ignore") as f:
                stl_content = f.read()
        except:
            pass

    # แปลงข้อมูล STL ให้พร้อมส่งเข้า Three.js STLLoader
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <style>
            body {{ margin: 0; background-color: {bg_color}; overflow: hidden; }}
            #canvas-container {{ width: 100%; height: 450px; }}
        </style>
    </head>
    <body>
        <div id="canvas-container"></div>
        <script>
            const container = document.getElementById('canvas-container');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color('{bg_color}');

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 150);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            scene.add(new THREE.AmbientLight(0xffffff, 0.8));
            const light = new THREE.DirectionalLight(0xffffff, 0.8);
            light.position.set(1, 1, 1).normalize();
            scene.add(light);

            const material = new THREE.MeshStandardMaterial({{ color: 0x00a8ff, roughness: 0.3, metalness: 0.2 }});
            
            const stlString = `{stl_content}`;
            
            if (stlString && stlString.trim().length > 0) {{
                try {{
                    const loader = new THREE.STLLoader();
                    const geometry = loader.parse(stlString);
                    geometry.center();
                    const mesh = new THREE.Mesh(geometry, material);
                    scene.add(mesh);
                }} catch (err) {{
                    // Fallback เป็นกล่องถ้า parse ไม่ผ่าน
                    const geometry = new THREE.BoxGeometry(60, 25, 10);
                    scene.add(new THREE.Mesh(geometry, material));
                }}
            }} else {{
                const geometry = new THREE.BoxGeometry(60, 25, 10);
                scene.add(new THREE.Mesh(geometry, material));
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=460)

def get_openscad_path():
    system = platform.system()
    if system == "Windows":
        paths = [
            r"C:\Program Files\OpenSCAD\openscad.exe",
            r"C:\Program Files (x86)\OpenSCAD\openscad.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    return "openscad"
