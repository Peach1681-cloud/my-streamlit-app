import streamlit as st
import os
import uuid
import subprocess
import base64
import streamlit.components.v1 as components
from ui_theme import apply_theme
from analytics import record_export
from render_engine import cleanup_directory, render_gate, render_openscad, session_workdir

try:
    from config import get_openscad_path
    from font_catalog import GLOBAL_FONT_OPTIONS, GLOBAL_FONT_DICT, LANGUAGE_FONT_EXAMPLES
    from icon_catalog_v2 import get_icon_path
    from icon_picker import visual_icon_picker
except ImportError:
    st.error("❌ Error importing from config.py.")
    st.stop()

st.set_page_config(page_title="3D Text Keychain Generator", page_icon="🏷️", layout="wide")
apply_theme()

st.markdown("## 🏷️ 3D Text Keychain Generator")
st.markdown("### Create custom multilingual 3D text keychains with synced dual-color preview")

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("## 🛠️ Keychain Settings")
    
    main_text = st.text_input("Main Text (บรรทัดแรก):", "รักติดลบ")
    
    show_second_line = st.checkbox("Show Second Line (แสดงบรรทัดที่ 2)", value=True)
    second_line_text = st.text_input("Second Line (บรรทัดที่ 2 / เบอร์โทร):", "081-234-5678")
    
    font_choice = st.selectbox("Language & Font (ภาษาและฟอนต์):", GLOBAL_FONT_OPTIONS)
    st.caption(LANGUAGE_FONT_EXAMPLES)
    selected_font = GLOBAL_FONT_DICT[font_choice]  # ดึงค่าฟอนต์จาก Dictionary กลางเช่นเดียวกับโปรเจกต์อื่น
    
    icon_choice = visual_icon_picker("เลือกไอคอน", "text_keychain_icon")
    icon_size = st.slider("Icon Size (ขนาดไอคอน mm):", 8.0, 40.0, 18.0, 1.0)
    icon_spacing = st.slider("Icon Spacing (ระยะห่างไอคอน mm):", 0.0, 10.0, 1.0, 0.5)
    ring_position_offset = st.slider("Ring Position (ปรับตำแหน่งห่วง ซ้าย-ขวา mm):", -15.0, 15.0, 0.0, 0.5)
    
    st.markdown("---")
    text_size = st.slider("Main Text Size (mm):", 10.0, 40.0, 20.0, 1.0)
    second_line_size = st.slider("Second Line Size (mm):", 5.0, 25.0, 10.0, 1.0)
    
    st.markdown("---")
    base_thickness = st.slider("Base Thickness (ความหนาฐาน mm):", 1.0, 10.0, 3.0, 0.5)
    text_thickness = st.slider("Text Thickness (ความหนาตัวอักษร mm):", 1.0, 5.0, 2.0, 0.5)
    outline_size = st.slider("Outline Size (ขนาดขอบรอบตัวอักษร mm):", 1.0, 8.0, 3.0, 0.5)
    
    st.markdown("---")
    hole_diameter = st.slider("Hole Diameter (ขนาดรูร้อยห่วง mm):", 2.0, 10.0, 5.0, 0.5)
    hole_ring_thickness = st.slider("Ring Thickness (ความหนาขอบห่วง mm):", 1.0, 6.0, 3.0, 0.5)
    
    openscad_path = get_openscad_path()

# --- จัดการไฟล์และสคริปต์ OpenSCAD ---
output_dir = session_workdir("text_keychain")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
cleanup_directory(output_dir)

unique_id = str(uuid.uuid4())
base_scad = os.path.join(output_dir, f"base_{unique_id}.scad")
base_stl = os.path.join(output_dir, f"base_{unique_id}.stl")
text_scad = os.path.join(output_dir, f"text_{unique_id}.scad")
text_stl = os.path.join(output_dir, f"text_{unique_id}.stl")

icon_file = get_icon_path(icon_choice)
openscad_has_icon = "true" if icon_file else "false"
openscad_show_second = "true" if show_second_line else "false"

# 1. สคริปต์สร้างฐาน (Base)
base_script = f"""
Name = "{main_text}";
Show_Second_Line = {openscad_show_second};
Second_Line = "{second_line_text}";
Has_Icon = {openscad_has_icon};
Icon_File = "{icon_file}";
Icon_Size = {icon_size};
Icon_Spacing = {icon_spacing};
Ring_Offset = {ring_position_offset};
Font_Name = "{selected_font}";
Text_Size = {text_size};
Second_Line_Size = {second_line_size};
Base_Thickness = {base_thickness};
Outline_Size = {outline_size};
Hole_Diameter = {hole_diameter};
Hole_Ring_Thickness = {hole_ring_thickness};
$fn = 60;

icon_offset = Has_Icon ? Icon_Size + Icon_Spacing : 0;

module icon_2d() {{
    if (Has_Icon) {{
        translate([Icon_Size / 2, Text_Size * 0.35, 0])
            resize([Icon_Size, Icon_Size], auto = true)
                import(file = Icon_File, center = true);
    }}
}}

module text_2d() {{
    translate([icon_offset, 0, 0]) {{
        union() {{
            text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
            if (Show_Second_Line) {{
                translate([0, -(Second_Line_Size * 1.3), 0])
                    text(text = Second_Line, size = Second_Line_Size, font = Font_Name, halign = "left", valign = "baseline");
            }}
        }}
    }}
}}

module combined_content_2d() {{
    union() {{
        icon_2d();
        text_2d();
    }}
}}

module base_2d() {{
    offset(r = Outline_Size) {{
        combined_content_2d();
    }}
}}

module keychain_hole_2d() {{
    ring_outer_radius = (Hole_Diameter / 2) + Hole_Ring_Thickness;
    translate([-ring_outer_radius - 1 + Ring_Offset, Text_Size * 0.35, 0]) {{
        difference() {{
            circle(r = ring_outer_radius);
            circle(r = Hole_Diameter / 2);
        }}
    }}
}}

linear_extrude(height = Base_Thickness) {{
    union() {{
        base_2d();
        keychain_hole_2d();
    }}
}}
"""

# 2. สคริปต์สร้างตัวหนังสือ (Text)
text_script = f"""
Name = "{main_text}";
Show_Second_Line = {openscad_show_second};
Second_Line = "{second_line_text}";
Has_Icon = {openscad_has_icon};
Icon_File = "{icon_file}";
Icon_Size = {icon_size};
Icon_Spacing = {icon_spacing};
Font_Name = "{selected_font}";
Text_Size = {text_size};
Second_Line_Size = {second_line_size};
Base_Thickness = {base_thickness};
Text_Thickness = {text_thickness};
$fn = 60;

icon_offset = Has_Icon ? Icon_Size + Icon_Spacing : 0;

module icon_2d() {{
    if (Has_Icon) {{
        translate([Icon_Size / 2, Text_Size * 0.35, 0])
            resize([Icon_Size, Icon_Size], auto = true)
                import(file = Icon_File, center = true);
    }}
}}

module text_2d() {{
    translate([icon_offset, 0, 0]) {{
        union() {{
            text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
            if (Show_Second_Line) {{
                translate([0, -(Second_Line_Size * 1.3), 0])
                    text(text = Second_Line, size = Second_Line_Size, font = Font_Name, halign = "left", valign = "baseline");
            }}
        }}
    }}
}}

module combined_content_2d() {{
    union() {{
        icon_2d();
        text_2d();
    }}
}}

translate([0, 0, Base_Thickness]) {{
    linear_extrude(height = Text_Thickness) {{
        combined_content_2d();
    }}
}}
"""

render_gate([base_script, text_script], "text_keychain")

with open(base_scad, "w", encoding="utf-8") as f:
    f.write(base_script)
with open(text_scad, "w", encoding="utf-8") as f:
    f.write(text_script)

try:
    render_openscad(openscad_path, base_scad, base_stl)
    render_openscad(openscad_path, text_scad, text_stl)
except Exception as exc:
    st.error(
        "สร้างโมเดลไม่สำเร็จ: ไม่พบหรือเรียกใช้ OpenSCAD ไม่ได้ "
        "กรุณาตรวจสอบว่าได้ติดตั้งแพ็กเกจ `openscad` บนเซิร์ฟเวอร์แล้ว"
    )
    st.exception(exc)
    st.stop()

base_content = ""
text_content = ""
if os.path.exists(base_stl):
    try:
        with open(base_stl, "rb") as f:
            base_content = base64.b64encode(f.read()).decode("ascii")
    except OSError as exc:
        st.error(f"อ่านไฟล์ฐาน STL ไม่สำเร็จ: {exc}")
if os.path.exists(text_stl):
    try:
        with open(text_stl, "rb") as f:
            text_content = base64.b64encode(f.read()).decode("ascii")
    except OSError as exc:
        st.error(f"อ่านไฟล์ตัวอักษร STL ไม่สำเร็จ: {exc}")

if not base_content and not text_content:
    st.error("OpenSCAD ไม่ได้สร้างไฟล์ STL สำหรับพรีวิว กรุณาตรวจสอบ log ของการ deploy")
    st.stop()

st.markdown("### 👁️ 3D Real-time Preview (Synced Dual-Color)")

viewer_html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        body {{ margin: 0; background-color: #1a1a1a; overflow: hidden; }}
        #canvas-container {{ width: 100%; height: 450px; }}
    </style>
</head>
<body>
    <div id="canvas-container"></div>
    <script>
        const container = document.getElementById('canvas-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color('#1a1a1a');

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

        const baseMaterial = new THREE.MeshStandardMaterial({{ color: 0x1e3799, roughness: 0.4, metalness: 0.1 }});
        const textMaterial = new THREE.MeshStandardMaterial({{ color: 0xffffff, roughness: 0.2, metalness: 0.2 }});

        const loader = new THREE.STLLoader();
        const modelGroup = new THREE.Group();
        scene.add(modelGroup);

        function decodeBase64(value) {{
            const binary = atob(value);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            return bytes.buffer;
        }}

        function addStl(encoded, material) {{
            if (!encoded) return;
            const geometry = loader.parse(decodeBase64(encoded));
            geometry.computeVertexNormals();
            modelGroup.add(new THREE.Mesh(geometry, material));
        }}

        const baseString = `{base_content}`;
        const textString = `{text_content}`;
        try {{
            addStl(baseString, baseMaterial);
            addStl(textString, textMaterial);

            const bounds = new THREE.Box3().setFromObject(modelGroup);
            const center = bounds.getCenter(new THREE.Vector3());
            const size = bounds.getSize(new THREE.Vector3());
            modelGroup.position.sub(center);
            const maxSize = Math.max(size.x, size.y, size.z, 1);
            const distance = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
            camera.position.set(0, 0, distance * 1.35);
            camera.near = Math.max(distance / 100, 0.01);
            camera.far = distance * 100;
            camera.updateProjectionMatrix();
            controls.target.set(0, 0, 0);
            controls.update();
        }} catch (error) {{
            container.innerHTML = '<div style="color:#ff8a8a;padding:20px;font-family:sans-serif">เปิดไฟล์ 3D ไม่สำเร็จ: ' + error.message + '</div>';
            throw error;
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

components.html(viewer_html, height=460)

st.markdown("---")
st.markdown("### 📥 Download STL Files")
col1, col2 = st.columns(2)

with col1:
    if os.path.exists(base_stl):
        with open(base_stl, "rb") as file:
            st.download_button(
                label="💾 Download Base .STL (ฐานน้ำเงิน)",
                data=file,
                file_name="keychain_base.stl",
                mime="application/octet-stream",
                type="primary",
                on_click=record_export,
                args=("text_keychain",)
            )

with col2:
    if os.path.exists(text_stl):
        with open(text_stl, "rb") as file:
            st.download_button(
                label="💾 Download Text .STL (ตัวอักษรขาว)",
                data=file,
                file_name="keychain_text.stl",
                mime="application/octet-stream",
                type="secondary",
                on_click=record_export,
                args=("text_keychain",)
            )
