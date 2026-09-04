import os
import tempfile
import subprocess
import streamlit as st
import pyvista as pv
import streamlit.components.v1 as components
from config import get_openscad_path
from font_catalog import GLOBAL_FONT_OPTIONS, GLOBAL_FONT_DICT, LANGUAGE_FONT_EXAMPLES
from ui_theme import apply_theme
from analytics import record_export
from render_engine import render_gate, render_openscad, session_workdir

apply_theme()

def generate_lightbox_scad_split(text_string, font_name, letter_size, letter_spacing, box_depth, wall_thick, cover_face_thick, lip_height, tolerance, lip_thick_reduce, cover_margin, cover_offset_y):
    string_len = len(text_string)
    
    scad_box = f"""
    $fn = 60;
    Text_Str = "{text_string}";
    Font_Name = "{font_name}";
    Letter_Size = {letter_size};
    Letter_Spacing = {letter_spacing};
    Box_Depth = {box_depth};
    Wall_Thickness = {wall_thick};

    module single_char_box(ch, f_name) {{
        difference() {{
            linear_extrude(height = Box_Depth)
                text(ch, size = Letter_Size, font = f_name, halign = "center", valign = "center");
            
            translate([0, 0, Wall_Thickness])
                linear_extrude(height = Box_Depth)
                    offset(r = -Wall_Thickness)
                        text(ch, size = Letter_Size, font = f_name, halign = "center", valign = "center");
        }}
    }}

    for (i = [0 : len(Text_Str) - 1]) {{
        translate([i * Letter_Spacing, 0, 0]) 
            single_char_box(Text_Str[i], Font_Name);
    }}
    """
    
    scad_cover = f"""
    $fn = 60;
    Text_Str = "{text_string}";
    Font_Name = "{font_name}";
    Letter_Size = {letter_size};
    Letter_Spacing = {letter_spacing};
    Wall_Thickness = {wall_thick};
    Cover_Face_Thick = {cover_face_thick};
    Lip_Height = {lip_height};
    Tolerance = {tolerance};
    Lip_Thick_Reduce = {lip_thick_reduce};
    Cover_Lip_Margin = {cover_margin};
    Cover_Offset_Y = {cover_offset_y};

    module single_letter_cover(char, f_name) {{
        rotate([180, 0, 0]) {{
            mirror([1, 0, 0]) {{
                union() {{
                    linear_extrude(height = Cover_Face_Thick)
                        offset(r = Cover_Lip_Margin)
                            text(char, size = Letter_Size, font = f_name, halign = "center", valign = "center");
                        
                    translate([0, 0, Cover_Face_Thick]) {{
                        difference() {{
                            linear_extrude(height = Lip_Height)
                                offset(r = -Wall_Thickness - (Tolerance / 2))
                                    text(char, size = Letter_Size, font = f_name, halign = "center", valign = "center");
                                    
                            translate([0, 0, -0.1])
                                linear_extrude(height = Lip_Height + 0.2)
                                    offset(r = -Wall_Thickness - (Tolerance / 2) - (Wall_Thickness - Lip_Thick_Reduce))
                                        text(char, size = Letter_Size, font = f_name, halign = "center", valign = "center");
                        }}
                    }}
                }}
            }}
        }}
    }}

    for (i = [0 : len(Text_Str) - 1]) {{
        translate([i * Letter_Spacing, Cover_Offset_Y, Cover_Face_Thick + Lip_Height])
            single_letter_cover(Text_Str[i], Font_Name);
    }}
    """
    
    return scad_box, scad_cover

st.title("💡 3D LED Lightbox Studio Pro")
st.subheader("Create hollow 3D text lightboxes with removable face covers")

st.sidebar.subheader("📝 Lightbox Settings")
lb_text = st.sidebar.text_input("Lightbox Text:", value="MKF")

st.sidebar.subheader("🌐 Lightbox Font Selection")
font_lb_option = st.sidebar.selectbox("Lightbox Language & Font:", GLOBAL_FONT_OPTIONS, key="lb_font")
lb_font_name = GLOBAL_FONT_DICT[font_lb_option]
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)

col_l1, col_l2 = st.sidebar.columns(2)
lb_letter_size = col_l1.number_input("Letter Height (mm):", value=60)
lb_letter_spacing = col_l2.number_input("Letter Spacing (mm):", value=75)

lb_box_depth = st.sidebar.number_input("Box Depth (mm):", value=25)
lb_wall_thick = st.sidebar.number_input("Wall Thickness (mm):", value=2.0)

st.sidebar.subheader("🔒 Translucent Cover Settings")
lb_cover_face_thick = st.sidebar.number_input("Cover Face Thickness (mm):", value=1.2)
lb_lip_height = st.sidebar.number_input("Lip Height (mm):", value=3.5)
lb_tolerance = st.sidebar.number_input("Fit Tolerance (mm):", value=0.4, step=0.05)
lb_cover_offset_y = st.sidebar.number_input("Back Cover Offset Y (mm):", value=100)

FIX_BG_COLOR = "#2A2A2A"
FIX_BOX_COLOR = "#111111"
FIX_COVER_COLOR = "#FFFFFF"

openscad_exe = get_openscad_path()
temp_dir = session_workdir("led_lightbox")

scad_box_code, scad_cover_code = generate_lightbox_scad_split(
    text_string=lb_text,
    font_name=lb_font_name,
    letter_size=lb_letter_size,
    letter_spacing=lb_letter_spacing,
    box_depth=lb_box_depth,
    wall_thick=lb_wall_thick,
    cover_face_thick=lb_cover_face_thick,
    lip_height=lb_lip_height,
    tolerance=lb_tolerance,
    lip_thick_reduce=0.5,
    cover_margin=1.0,
    cover_offset_y=lb_cover_offset_y
)

render_gate([scad_box_code, scad_cover_code], "led_lightbox")

if scad_box_code and scad_cover_code:
    scad_lb_box_p = os.path.join(temp_dir, "lb_box.scad")
    stl_lb_box_p = os.path.join(temp_dir, "lb_box.stl")
    with open(scad_lb_box_p, "w", encoding="utf-8") as f:
        f.write(scad_box_code)

    scad_lb_cover_p = os.path.join(temp_dir, "lb_cover.scad")
    stl_lb_cover_p = os.path.join(temp_dir, "lb_cover.stl")
    with open(scad_lb_cover_p, "w", encoding="utf-8") as f:
        f.write(scad_cover_code)

    try:
        render_openscad(openscad_exe, scad_lb_box_p, stl_lb_box_p)
        render_openscad(openscad_exe, scad_lb_cover_p, stl_lb_cover_p)

        box_content = ""
        cover_content = ""
        if os.path.exists(stl_lb_box_p):
            with open(stl_lb_box_p, "r", encoding="utf-8", errors="ignore") as f:
                box_content = f.read()
        if os.path.exists(stl_lb_cover_p):
            with open(stl_lb_cover_p, "r", encoding="utf-8", errors="ignore") as f:
                cover_content = f.read()

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
                camera.position.set(0, 0, 200);

                const renderer = new THREE.WebGLRenderer({{ antialias: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                container.appendChild(renderer.domElement);

                const controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;

                scene.add(new THREE.AmbientLight(0xffffff, 0.8));
                const light = new THREE.DirectionalLight(0xffffff, 0.8);
                light.position.set(1, 1, 1).normalize();
                scene.add(light);

                const boxMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_BOX_COLOR}', roughness: 0.4, metalness: 0.1 }});
                const coverMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_COVER_COLOR}', roughness: 0.2, metalness: 0.2 }});

                const loader = new THREE.STLLoader();

                const boxString = `{box_content}`;
                if (boxString && boxString.trim().length > 0) {{
                    try {{
                        const geomBox = loader.parse(boxString);
                        const meshBox = new THREE.Mesh(geomBox, boxMaterial);
                        scene.add(meshBox);
                    }} catch(e) {{}}
                }}

                const coverString = `{cover_content}`;
                if (coverString && coverString.trim().length > 0) {{
                    try {{
                        const geomCover = loader.parse(coverString);
                        const meshCover = new THREE.Mesh(geomCover, coverMaterial);
                        scene.add(meshCover);
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

        m_lb_box = pv.read(stl_lb_box_p)
        m_lb_cover = pv.read(stl_lb_cover_p)
        combined_lb = m_lb_box.merge(m_lb_cover)
        combined_lb_stl_path = os.path.join(temp_dir, "LED_Lightbox.stl")
        combined_lb.save(combined_lb_stl_path)

        with open(combined_lb_stl_path, "rb") as file:
            st.download_button(
                label="💾 Save & Download LED Lightbox .STL",
                data=file,
                file_name=f"LED_Lightbox_{lb_text}.stl",
                mime="application/octet-stream",
                use_container_width=True,
                on_click=record_export,
                args=("led_lightbox",)
            )

    except Exception as e:
        st.error(f"Render Error: {e}")
