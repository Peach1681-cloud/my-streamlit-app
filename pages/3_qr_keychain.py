import os
import tempfile
import subprocess
import streamlit as st
import pyvista as pv
import streamlit.components.v1 as components
from config import HAS_QR_LIBS, get_openscad_path
from font_catalog import GLOBAL_FONT_OPTIONS, GLOBAL_FONT_DICT, LANGUAGE_FONT_EXAMPLES
from ui_theme import apply_theme
from analytics import record_export
from render_engine import render_gate, render_openscad, session_workdir

apply_theme()

try:
    import qrcode
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    pass

def decode_qr_from_image(uploaded_file):
    if not HAS_QR_LIBS:
        return None
    try:
        image = Image.open(uploaded_file)
        img_np = np.array(image.convert('RGB'))
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img_np)
        return data if data else None
    except Exception:
        return None

def generate_qr_scad_split(qr_data, label_text="", qr_size=40, base_thick=3.0, qr_thick=1.5, hole_dia=5.0, ring_type="Corner Hole", hole_margin=3.0, label_font="Montserrat:style=Bold"):
    if not HAS_QR_LIBS:
        return "", ""
        
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(qr_data if qr_data else "https://google.com")
    qr.make(fit=True)
    matrix = qr.get_matrix()
    
    grid_size = len(matrix)
    pixel_size = qr_size / grid_size
    
    has_label = bool(label_text.strip())
    extra_height = 8.0 if has_label else 0.0
    
    scad_base = f"""
    $fn = 60;
    qr_size = {qr_size};
    base_thick = {base_thick};
    hole_dia = {hole_dia};
    extra_h = {extra_height};
    margin = {hole_margin};
    
    difference() {{
        union() {{
            translate([-margin, -margin - extra_h, 0]) cube([qr_size + (margin*2), qr_size + (margin*2) + extra_h, base_thick]);
            {"translate([-margin - hole_dia, qr_size + margin - (hole_dia/2), 0]) difference() { cylinder(h = base_thick, r = hole_dia * 0.9); translate([0, 0, -1]) cylinder(h = base_thick + 2, r = hole_dia / 2); }" if ring_type == "Thick Ring" else ""}
        }}
        {"translate([-margin + (hole_dia * 0.8), qr_size + margin - (hole_dia * 0.8), -1]) cylinder(h = base_thick + 2, r = hole_dia / 2);" if ring_type == "Corner Hole" else ""}
    }}
    """
    
    scad_pixel = f"""
    $fn = 60;
    qr_size = {qr_size};
    base_thick = {base_thick};
    qr_thick = {qr_thick};
    label_txt = "{label_text.strip()}";
    
    translate([0, 0, base_thick]) {{
        if (label_txt != "") {{
            translate([qr_size / 2, -6.5, 0])
                linear_extrude(height = qr_thick)
                    text(text = label_txt, size = 5, font = "{label_font}", halign = "center", valign = "baseline");
        }}
    """
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:
                x = c * pixel_size
                y = (grid_size - 1 - r) * pixel_size
                scad_pixel += f"translate([{x}, {y}, 0]) cube([{pixel_size + 0.05}, {pixel_size + 0.05}, qr_thick]);\n"
                
    scad_pixel += "}"
    
    return scad_base, scad_pixel

st.title("📱 3D QR Code Keychain Generator")
st.subheader("Create scannable 3D QR code keychains for payment or links")

st.sidebar.subheader("📱 QR Data Source")
qr_mode_input = st.sidebar.radio("Input Method:", ["🔗 Text / URL Link", "🖼️ Upload QR Code Image"])

qr_final_text = "https://www.facebook.com/profile.php?id=61590771869852"

if qr_mode_input == "🔗 Text / URL Link":
    qr_input_text = st.sidebar.text_input("Target URL / Text / Phone:", value="https://www.facebook.com/profile.php?id=61590771869852")
    if qr_input_text.strip():
        qr_final_text = qr_input_text.strip()
else:
    uploaded_qr_file = st.sidebar.file_uploader("Upload QR Image (PNG, JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_qr_file is not None:
        decoded_link = decode_qr_from_image(uploaded_qr_file)
        if decoded_link:
            st.sidebar.success(f"✅ Decoded URL: {decoded_link}")
            qr_final_text = decoded_link
        else:
            st.sidebar.error("❌ Could not decode QR code from image. Please use a clearer image.")

st.sidebar.subheader("🌐 Bottom Label Font Selection")
qr_font_option = st.sidebar.selectbox("Label Language & Font:", GLOBAL_FONT_OPTIONS, key="qr_font")
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)
qr_selected_font = GLOBAL_FONT_DICT[qr_font_option]

st.sidebar.subheader("🏷️ Bottom Label Text")
qr_label_input = st.sidebar.text_input("Label Below QR (e.g., FACEBOOK, LINE, PAY):", value="FACEBOOK")

st.sidebar.subheader("⭕ Hanging Ring Style")
ring_type_option = st.sidebar.selectbox("Select Ring Style:", ["Corner Hole", "Thick Ring", "No Ring"])

qr_size_input = st.sidebar.number_input("QR Width (mm):", value=40)
qr_base_thick = st.sidebar.number_input("Base Thickness (mm):", value=3.0)
qr_pixel_thick = st.sidebar.number_input("QR Pixel Raised Thickness (mm):", value=1.5)

st.sidebar.subheader("📐 Ring Dimensions")
hole_dia_input = st.sidebar.number_input("Hole Diameter (mm):", value=5.0, step=0.5)

FIX_BG_COLOR = "#2A2A2A"
FIX_BASE_COLOR = "#FFFFFF"
FIX_PIXEL_COLOR = "#000000"

openscad_exe = get_openscad_path()
temp_dir = session_workdir("qr_keychain")

scad_base_code, scad_pixel_code = generate_qr_scad_split(
    qr_data=qr_final_text,
    label_text=qr_label_input,
    qr_size=qr_size_input,
    base_thick=qr_base_thick,
    qr_thick=qr_pixel_thick,
    hole_dia=hole_dia_input,
    ring_type=ring_type_option,
    label_font=qr_selected_font
)

render_gate([scad_base_code, scad_pixel_code], "qr_keychain")

if scad_base_code and scad_pixel_code:
    scad_qr_base_p = os.path.join(temp_dir, "qr_base.scad")
    stl_qr_base_p = os.path.join(temp_dir, "qr_base.stl")
    with open(scad_qr_base_p, "w", encoding="utf-8") as f:
        f.write(scad_base_code)

    scad_qr_pixel_p = os.path.join(temp_dir, "qr_pixel.scad")
    stl_qr_pixel_p = os.path.join(temp_dir, "qr_pixel.stl")
    with open(scad_qr_pixel_p, "w", encoding="utf-8") as f:
        f.write(scad_pixel_code)

    try:
        render_openscad(openscad_exe, scad_qr_base_p, stl_qr_base_p)
        render_openscad(openscad_exe, scad_qr_pixel_p, stl_qr_pixel_p)

        # อ่านไฟล์ STL สำหรับแสดงผลแบบแยกชิ้น 2 สี
        base_content = ""
        pixel_content = ""
        if os.path.exists(stl_qr_base_p):
            with open(stl_qr_base_p, "r", encoding="utf-8", errors="ignore") as f:
                base_content = f.read()
        if os.path.exists(stl_qr_pixel_p):
            with open(stl_qr_pixel_p, "r", encoding="utf-8", errors="ignore") as f:
                pixel_content = f.read()

        st.markdown("### 👁️ 3D Real-time Preview (Synced Dual-Color)")

        viewer_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
            <style>
                body {{ margin: 0; background-color: {FIX_BG_COLOR}; overflow: hidden; }}
                #canvas-container {{ width: 100%; height: 480px; }}
            </style>
        </head>
        <body>
            <div id="canvas-container"></div>
            <script>
                const container = document.getElementById('canvas-container');
                const scene = new THREE.Scene();
                scene.background = new THREE.Color('{FIX_BG_COLOR}');

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

                const baseMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_BASE_COLOR}', roughness: 0.4, metalness: 0.1 }});
                const pixelMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_PIXEL_COLOR}', roughness: 0.2, metalness: 0.2 }});

                const loader = new THREE.STLLoader();

                const baseString = `{base_content}`;
                if (baseString && baseString.trim().length > 0) {{
                    try {{
                        const geomBase = loader.parse(baseString);
                        const meshBase = new THREE.Mesh(geomBase, baseMaterial);
                        scene.add(meshBase);
                    }} catch(e) {{}}
                }}

                const pixelString = `{pixel_content}`;
                if (pixelString && pixelString.trim().length > 0) {{
                    try {{
                        const geomPixel = loader.parse(pixelString);
                        const meshPixel = new THREE.Mesh(geomPixel, pixelMaterial);
                        scene.add(meshPixel);
                    }} catch(e) {{}}
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

        components.html(viewer_html, height=500)

        # สร้างไฟล์สำหรับดาวน์โหลด
        m_qr_base = pv.read(stl_qr_base_p)
        m_qr_pixel = pv.read(stl_qr_pixel_p)
        combined_qr = m_qr_base.merge(m_qr_pixel)
        combined_qr_stl_path = os.path.join(temp_dir, "3D_QRCode_Keychain.stl")
        combined_qr.save(combined_qr_stl_path)

        with open(combined_qr_stl_path, "rb") as file:
            st.download_button(
                label="💾 Save & Download QR Code .STL",
                data=file,
                file_name=f"3D_QRCode_{qr_label_input.strip() if qr_label_input.strip() else 'Keychain'}.stl",
                mime="application/octet-stream",
                use_container_width=True,
                on_click=record_export,
                args=("qr_keychain",)
            )

    except Exception as e:
        st.error(f"Render Error: {e}")
