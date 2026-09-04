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

def generate_monogram_scad_split(
    big_letter, big_font, 
    line1, line2, line3, name_font, 
    big_size, big_thick, name_thick, ratio, 
    recess_depth, tolerance, spacing, name_char_spacing, 
    y_offset_1, y_offset_2, y_offset_3, view_mode="combined"
):
    
    scad_base = f"""
    $fn = 60;
    Letter = "{big_letter}";
    Letter_Font = "{big_font}";
    
    Line1 = "{line1}";
    Line2 = "{line2}";
    Line3 = "{line3}";
    Name_Font = "{name_font}";
    
    Letter_Size = {big_size};
    Letter_Thickness = {big_thick};
    Name_Size_Ratio = {ratio};
    Recess_Depth = {recess_depth};
    Tolerance = {tolerance};
    
    Y_Offset_1 = {y_offset_1};
    Y_Offset_2 = {y_offset_2};
    Y_Offset_3 = {y_offset_3};

    module raw_base_letter() {{
        text(text = Letter, size = Letter_Size, font = Letter_Font, halign = "center", valign = "center");
    }}

    module name_cutters() {{
        sub_size = Letter_Size * Name_Size_Ratio;
        
        if (Line1 != "") {{
            translate([0, Y_Offset_1, 0])
                linear_extrude(height = Recess_Depth + 0.1)
                    offset(r = 0.5 + Tolerance)
                        text(text = Line1, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
        }}
        if (Line2 != "") {{
            translate([0, Y_Offset_2, 0])
                linear_extrude(height = Recess_Depth + 0.1)
                    offset(r = 0.5 + Tolerance)
                        text(text = Line2, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
        }}
        if (Line3 != "") {{
            translate([0, Y_Offset_3, 0])
                linear_extrude(height = Recess_Depth + 0.1)
                    offset(r = 0.5 + Tolerance)
                        text(text = Line3, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
        }}
    }}

    difference() {{
        linear_extrude(height = Letter_Thickness) {{
            raw_base_letter();
        }}
        translate([0, 0, Letter_Thickness - Recess_Depth]) {{
            name_cutters();
        }}
    }}
    """

    if view_mode == "combined":
        trans_z = big_thick - recess_depth
        name_z = trans_z
    else:
        trans_z = 0
        name_z = 0

    scad_name = f"""
    $fn = 60;
    Line1 = "{line1}";
    Line2 = "{line2}";
    Line3 = "{line3}";
    Name_Font = "{name_font}";
    Letter_Size = {big_size};
    Name_Thickness = {name_thick};
    Name_Size_Ratio = {ratio};
    sub_size = Letter_Size * Name_Size_Ratio;
    
    Y_Offset_1 = {y_offset_1};
    Y_Offset_2 = {y_offset_2};
    Y_Offset_3 = {y_offset_3};
    
    Separate_Spacing = {spacing};
    View_Mode = "{view_mode}";

    module render_names(z_pos) {{
        if (View_Mode == "combined") {{
            if (Line1 != "") {{
                translate([0, Y_Offset_1, z_pos])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line1, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
            if (Line2 != "") {{
                translate([0, Y_Offset_2, z_pos])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line2, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
            if (Line3 != "") {{
                translate([0, Y_Offset_3, z_pos])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line3, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
        }} else {{
            if (Line1 != "") {{
                translate([0, -Separate_Spacing + Y_Offset_1, 0])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line1, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
            if (Line2 != "") {{
                translate([0, -Separate_Spacing * 1.5 + Y_Offset_2, 0])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line2, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
            if (Line3 != "") {{
                translate([0, -Separate_Spacing * 2 + Y_Offset_3, 0])
                    linear_extrude(height = Name_Thickness)
                        offset(r = 0.5)
                            text(text = Line3, size = sub_size, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
        }}
    }}

    render_names({name_z});
    """
    
    return scad_base, scad_name

st.title("📌 3D Monogram Initial Name Sign Studio")
st.subheader("Create luxury recessed initial signs with multi-line custom inserts")

st.sidebar.subheader("👀 3D Preview Mode")
mode_option = st.sidebar.radio(
    "Select Display Mode:",
    ["🧩 Combined Assembly View", "✂️ Separate Parts View"]
)
view_mode_key = "combined" if "Combined" in mode_option else "separate"

st.sidebar.subheader("🔤 Back Big Letters & Font")
mono_big_char = st.sidebar.text_input("Main Initial (Max 5 chars):", value="PEACH")
if len(mono_big_char) > 5:
    mono_big_char = mono_big_char[:5]

font_big_option = st.sidebar.selectbox("Main Initial Font / Language:", GLOBAL_FONT_OPTIONS, key="mono_big_font")
mono_big_font = GLOBAL_FONT_DICT[font_big_option]
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)

st.sidebar.subheader("✍️ Front Insert Text (3 Lines)")
line_1 = st.sidebar.text_input("Line 1 Text:", value="Studio 3D")
line_2 = st.sidebar.text_input("Line 2 Text:", value="Custom Design")
line_3 = st.sidebar.text_input("Line 3 Text:", value="")

st.sidebar.subheader("🌐 Front Text Font Selection (Supports Cursive)")
CURSIVE_FONTS = {
    "Pacifico (Cursive Cute)": "Pacifico:style=Regular",
    "Dancing Script (Cursive Elegant)": "Dancing Script:style=Bold",
    "Satisfy (Cursive Smooth)": "Satisfy:style=Regular"
}
COMBINED_FONT_DICT = {**GLOBAL_FONT_DICT, **CURSIVE_FONTS}
COMBINED_FONT_OPTIONS = list(COMBINED_FONT_DICT.keys())

font_mono_option = st.sidebar.selectbox("Front Text Font:", COMBINED_FONT_OPTIONS, key="mono_font")
mono_name_font = COMBINED_FONT_DICT[font_mono_option]

st.sidebar.subheader("↕️ Vertical Position per Line (mm)")
y_off_1 = st.sidebar.slider("Line 1 Y Offset:", min_value=-50.0, max_value=50.0, value=0.0, step=1.0)
y_off_2 = st.sidebar.slider("Line 2 Y Offset:", min_value=-50.0, max_value=50.0, value=-15.0, step=1.0)
y_off_3 = st.sidebar.slider("Line 3 Y Offset:", min_value=-50.0, max_value=50.0, value=-30.0, step=1.0)

st.sidebar.subheader("↔️ Front Text Spacing")
mono_name_spacing = st.sidebar.slider("Character Spacing:", min_value=0.5, max_value=2.0, value=0.85, step=0.05)

st.sidebar.subheader("📏 Dimensions")
mono_big_size = st.sidebar.number_input("Main Initial Height (mm):", value=100)
mono_big_thick = st.sidebar.number_input("Main Initial Thickness (mm):", value=15)
mono_name_thick = st.sidebar.number_input("Front Insert Thickness (mm):", value=8)
mono_ratio = st.sidebar.slider("Name-to-Initial Size Ratio:", min_value=0.10, max_value=0.60, value=0.30, step=0.01)

st.sidebar.subheader("📐 Recess & Layout")
mono_recess = st.sidebar.number_input("Recess Depth (mm):", value=3)
mono_tolerance = st.sidebar.number_input("Fit Tolerance (mm):", value=0.2, step=0.05)
mono_spacing = st.sidebar.number_input("Separate Part Spacing (mm):", value=120)

FIX_BG_COLOR = "#2A2A2A"
FIX_BASE_COLOR = "#A0522D"
FIX_NAME_COLOR = "#00BFFF"

openscad_exe = get_openscad_path()
temp_dir = session_workdir("monogram_sign")

scad_m_base, scad_m_name = generate_monogram_scad_split(
    big_letter=mono_big_char if mono_big_char else "N",
    big_font=mono_big_font,
    line1=line_1,
    line2=line_2,
    line3=line_3,
    name_font=mono_name_font,
    big_size=mono_big_size,
    big_thick=mono_big_thick,
    name_thick=mono_name_thick,
    ratio=mono_ratio,
    recess_depth=mono_recess,
    tolerance=mono_tolerance,
    spacing=mono_spacing,
    name_char_spacing=mono_name_spacing,
    y_offset_1=y_off_1,
    y_offset_2=y_off_2,
    y_offset_3=y_off_3,
    view_mode=view_mode_key
)

render_gate([scad_m_base, scad_m_name], "monogram_sign")

if scad_m_base and scad_m_name:
    scad_mb_p = os.path.join(temp_dir, "mono_base.scad")
    stl_mb_p = os.path.join(temp_dir, "mono_base.stl")
    with open(scad_mb_p, "w", encoding="utf-8") as f:
        f.write(scad_m_base)

    scad_mn_p = os.path.join(temp_dir, "mono_name.scad")
    stl_mn_p = os.path.join(temp_dir, "mono_name.stl")
    with open(scad_mn_p, "w", encoding="utf-8") as f:
        f.write(scad_m_name)

    try:
        render_openscad(openscad_exe, scad_mb_p, stl_mb_p)
        render_openscad(openscad_exe, scad_mn_p, stl_mn_p)

        base_content = ""
        name_content = ""
        if os.path.exists(stl_mb_p):
            with open(stl_mb_p, "r", encoding="utf-8", errors="ignore") as f:
                base_content = f.read()
        if os.path.exists(stl_mn_p):
            with open(stl_mn_p, "r", encoding="utf-8", errors="ignore") as f:
                name_content = f.read()

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

                const baseMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_BASE_COLOR}', roughness: 0.4, metalness: 0.1 }});
                const nameMaterial = new THREE.MeshStandardMaterial({{ color: '{FIX_NAME_COLOR}', roughness: 0.2, metalness: 0.2 }});

                const loader = new THREE.STLLoader();

                const baseString = `{base_content}`;
                if (baseString && baseString.trim().length > 0) {{
                    try {{
                        const geomBase = loader.parse(baseString);
                        const meshBase = new THREE.Mesh(geomBase, baseMaterial);
                        scene.add(meshBase);
                    }} catch(e) {{}}
                }}

                const nameString = `{name_content}`;
                if (nameString && nameString.trim().length > 0) {{
                    try {{
                        const geomName = loader.parse(nameString);
                        const meshName = new THREE.Mesh(geomName, nameMaterial);
                        scene.add(meshName);
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

        st.markdown("---")
        st.markdown("### 📥 Download Separate STL Files (สำหรับพิมพ์แยกสี)")
        
        col1, col2 = st.columns(2)

        with col1:
            if os.path.exists(stl_mb_p):
                with open(stl_mb_p, "rb") as file1:
                    st.download_button(
                        label="💾 Download Back Big Letters (.STL)",
                        data=file1,
                        file_name=f"Monogram_Back_{mono_big_char}.stl",
                        mime="application/octet-stream",
                        use_container_width=True,
                        type="primary",
                        on_click=record_export,
                        args=("monogram_sign",)
                    )

        with col2:
            if os.path.exists(stl_mn_p):
                with open(stl_mn_p, "rb") as file2:
                    st.download_button(
                        label="💾 Download Front Insert Text (.STL)",
                        data=file2,
                        file_name=f"Monogram_Front_Text.stl",
                        mime="application/octet-stream",
                        use_container_width=True,
                        type="secondary",
                        on_click=record_export,
                        args=("monogram_sign",)
                    )

    except Exception as e:
        st.error(f"Render Error: {e}")
