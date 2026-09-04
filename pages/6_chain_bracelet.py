import os
import json
import tempfile
import subprocess
import streamlit as st
import pyvista as pv
import streamlit.components.v1 as components
from config import get_openscad_path
from font_catalog import GLOBAL_FONT_OPTIONS, GLOBAL_FONT_DICT, LANGUAGE_FONT_EXAMPLES
from icon_catalog_v2 import get_icon_path
from icon_picker import visual_icon_picker
from ui_theme import apply_theme
from analytics import record_export
from render_engine import render_gate, render_openscad, session_workdir

apply_theme()

def generate_bracelet_scad_split(text_str, font_name, bead_shape, text_style, connection_mode, hole_shape, hole_w, hole_h, bead_size, bead_thick, spacing, icon_files=None, icon_position="Before Text", icon_scale=0.62):
    icon_files = [path for path in (icon_files or []) if path]
    string_len = len(text_str)
    icon_count = len(icon_files)
    has_icon = icon_count > 0
    if icon_position == "Icon Only":
        text_str = ""
        string_len = 0
        prefix_icons = icon_count
        suffix_icons = 0
    elif icon_position == "Before Text":
        prefix_icons = icon_count
        suffix_icons = 0
    elif icon_position == "After Text":
        prefix_icons = 0
        suffix_icons = icon_count
    else:
        prefix_icons = (icon_count + 1) // 2
        suffix_icons = icon_count - prefix_icons
    total_count = string_len + prefix_icons + suffix_icons
    icon_files_scad = json.dumps(icon_files, ensure_ascii=False)
    
    scad_base = f"""
    $fn = 60;
    Text_Str = "{text_str}";
    Font_Name = "{font_name}";
    Bead_Shape = "{bead_shape}";
    Text_Style = "{text_style}";
    Connection_Mode = "{connection_mode}";
    Hole_Shape = "{hole_shape}";
    Hole_W = {hole_w};
    Hole_H = {hole_h};
    Bead_Size = {bead_size};
    Bead_Thick = {bead_thick};
    Spacing = {spacing};
    string_len = {string_len};
    Has_Icon = {str(has_icon).lower()};
    Icon_Files = {icon_files_scad};
    Icon_Count = {icon_count};
    Icon_Scale = {icon_scale};
    Prefix_Icons = {prefix_icons};
    Suffix_Icons = {suffix_icons};
    Total_Count = {total_count};

    module base_shape() {{
        if (Bead_Shape == "Square") {{
            hull() {{
                translate([-Bead_Size/2 + Bead_Size*0.25, -Bead_Size/2 + Bead_Size*0.25, 0]) cylinder(h=Bead_Thick, r=Bead_Size*0.25);
                translate([Bead_Size/2 - Bead_Size*0.25, -Bead_Size/2 + Bead_Size*0.25, 0]) cylinder(h=Bead_Thick, r=Bead_Size*0.25);
                translate([-Bead_Size/2 + Bead_Size*0.25, Bead_Size/2 - Bead_Size*0.25, 0]) cylinder(h=Bead_Thick, r=Bead_Size*0.25);
                translate([Bead_Size/2 - Bead_Size*0.25, Bead_Size/2 - Bead_Size*0.25, 0]) cylinder(h=Bead_Thick, r=Bead_Size*0.25);
            }}
        }} else if (Bead_Shape == "Circle") {{
            cylinder(h=Bead_Thick, r=Bead_Size/2);
        }} else if (Bead_Shape == "Flower") {{
            union() {{
                cylinder(h=Bead_Thick, r=Bead_Size * 0.3);
                for (a = [0 : 60 : 300]) {{
                    rotate([0, 0, a])
                        translate([Bead_Size * 0.25, 0, 0])
                            cylinder(h=Bead_Thick, r=Bead_Size * 0.22);
                }}
            }}
        }} else if (Bead_Shape == "Star") {{
            linear_extrude(height=Bead_Thick)
                polygon(points=[
                    [0, Bead_Size/2], [Bead_Size*0.15, Bead_Size*0.15],
                    [Bead_Size/2, Bead_Size*0.15], [Bead_Size*0.2, -Bead_Size*0.1],
                    [Bead_Size*0.35, -Bead_Size*0.4], [0, -Bead_Size*0.2],
                    [-Bead_Size*0.35, -Bead_Size*0.4], [-Bead_Size*0.2, -Bead_Size*0.1],
                    [-Bead_Size/2, Bead_Size*0.15], [-Bead_Size*0.15, Bead_Size*0.15]
                ]);
        }}
    }}

    module custom_hole() {{
        translate([0, 0, Bead_Thick / 2]) {{
            rotate([0, 90, 0]) {{
                if (Hole_Shape == "Circle") {{
                    cylinder(h = Bead_Size + 2, r = Hole_W / 2, center = true);
                }} else {{
                    cube([Hole_H, Hole_W, Bead_Size + 2], center = true);
                }}
            }}
        }}
    }}

    module icon_2d(icon_index) {{
        resize([Bead_Size * Icon_Scale, Bead_Size * Icon_Scale], auto = true)
            import(file = Icon_Files[icon_index], center = true);
    }}

    module chain_segment_base(index) {{
        is_icon = Has_Icon && (
            index < Prefix_Icons ||
            index >= Prefix_Icons + string_len
        );
        icon_index = index < Prefix_Icons ? index : index - string_len;
        difference() {{
            union() {{
                base_shape();
                if (Connection_Mode == "Print-in-Place" && index < Total_Count - 1) {{
                    translate([Bead_Size/2, 0, Bead_Thick/2])
                        rotate([0, 90, 0])
                            cylinder(h = Spacing, r = Hole_W * 0.45, center = false);
                }}
            }}
            
            if (Text_Style == "Debossed (Engraved)") {{
                if (is_icon) {{
                    translate([0, 0, Bead_Thick - 1.2])
                        linear_extrude(height = 2.0)
                            icon_2d(icon_index);
                }} else {{
                    text_index = index - Prefix_Icons;
                    translate([0, 0, Bead_Thick - 1.2])
                        linear_extrude(height = 2.0)
                            text(Text_Str[text_index], size = Bead_Size * 0.5, font = Font_Name, halign = "center", valign = "center");
                }}
            }}
            
            custom_hole();
        }}
    }}

    for (i = [0 : Total_Count - 1]) {{
        translate([i * (Bead_Size + Spacing), 0, 0]) {{
            chain_segment_base(i);
        }}
    }}
    """

    scad_text = f"""
    $fn = 60;
    Text_Str = "{text_str}";
    Font_Name = "{font_name}";
    Text_Style = "{text_style}";
    Bead_Size = {bead_size};
    Bead_Thick = {bead_thick};
    Spacing = {spacing};
    string_len = {string_len};
    Has_Icon = {str(has_icon).lower()};
    Icon_Files = {icon_files_scad};
    Icon_Count = {icon_count};
    Icon_Scale = {icon_scale};
    Prefix_Icons = {prefix_icons};
    Suffix_Icons = {suffix_icons};
    Total_Count = {total_count};

    module icon_2d(icon_index) {{
        resize([Bead_Size * Icon_Scale, Bead_Size * Icon_Scale], auto = true)
            import(file = Icon_Files[icon_index], center = true);
    }}

    module chain_segment_text(index) {{
        is_icon = Has_Icon && (
            index < Prefix_Icons ||
            index >= Prefix_Icons + string_len
        );
        icon_index = index < Prefix_Icons ? index : index - string_len;
        if (Text_Style == "Embossed (Raised)") {{
            if (is_icon) {{
                translate([0, 0, Bead_Thick])
                    linear_extrude(height = 1.5)
                        icon_2d(icon_index);
            }} else {{
                text_index = index - Prefix_Icons;
                translate([0, 0, Bead_Thick])
                    linear_extrude(height = 1.5)
                        text(Text_Str[text_index], size = Bead_Size * 0.5, font = Font_Name, halign = "center", valign = "center");
            }}
        }}
    }}

    if (Text_Style == "Embossed (Raised)") {{
        for (i = [0 : Total_Count - 1]) {{
            translate([i * (Bead_Size + Spacing), 0, 0]) {{
                chain_segment_text(i);
            }}
        }}
    }}
    """
    return scad_base, scad_text

st.title("📿 3D Print-in-Place Chain Bracelet Studio")
st.subheader("Create custom shape beads and flexible bracelets")

st.sidebar.subheader("🌟 Bead Shape & Style")
bead_shape_option = st.sidebar.selectbox(
    "Choose Bead Shape:", 
    ["Square", "Circle", "Flower", "Star"]
)

text_style_option = st.sidebar.radio(
    "Text Style:",
    ["Embossed (Raised)", "Debossed (Engraved)"]
)

connection_mode_option = st.sidebar.radio(
    "Connection & Export Mode:",
    ["Print-in-Place", "String Hole Only"]
)

st.sidebar.subheader("🕳️ Hole & Cord Settings")
hole_shape_option = st.sidebar.selectbox(
    "Hole Shape:",
    ["Circle", "Rectangle"]
)

col_h1, col_h2 = st.sidebar.columns(2)
hole_width_val = col_h1.number_input("Hole Width (mm):", value=3.0, step=0.2)
hole_height_val = col_h2.number_input("Hole Height (mm):", value=1.5, step=0.2)

st.sidebar.subheader("🧩 Bracelet Content")
bracelet_content_mode = st.sidebar.radio(
    "Content Mode / รูปแบบสร้อย:",
    ["Text + Icons", "Icons Only", "Text Only"],
    key="bracelet_content_mode",
)

st.sidebar.subheader("✍️ Bracelet Text")
bracelet_text = st.sidebar.text_input(
    "Bracelet Text / Name:",
    value="NATALIA",
    disabled=bracelet_content_mode == "Icons Only",
)
bracelet_model_text = "" if bracelet_content_mode == "Icons Only" else bracelet_text

st.sidebar.subheader("🎨 Bracelet Icons")
if bracelet_content_mode == "Text Only":
    bracelet_icon_count = 0
    st.sidebar.caption("โหมดนี้ใช้เฉพาะข้อความ ไม่มีลูกปัดไอคอน")
else:
    bracelet_icon_count = int(st.sidebar.number_input(
        "Number of Icons / จำนวนไอคอน:",
        min_value=1,
        max_value=12,
        value=3 if bracelet_content_mode == "Icons Only" else 2,
        step=1,
        key="bracelet_icon_count",
    ))

bracelet_icon_choices = []
for icon_index in range(bracelet_icon_count):
    bracelet_icon_choices.append(
        visual_icon_picker(
            f"ไอคอนตำแหน่ง {icon_index + 1}",
            f"bracelet_icon_{icon_index}",
            host=st.sidebar,
        )
    )

bracelet_icon_files = [
    get_icon_path(choice)
    for choice in bracelet_icon_choices
    if get_icon_path(choice)
]
if bracelet_icon_count:
    st.sidebar.caption(
        f"เลือกแล้ว {len(bracelet_icon_files)} จาก {bracelet_icon_count} ตำแหน่ง"
    )

if bracelet_content_mode == "Icons Only":
    bracelet_icon_position = "Icon Only"
elif bracelet_content_mode == "Text Only":
    bracelet_icon_position = "Before Text"
else:
    bracelet_icon_position = st.sidebar.selectbox(
        "Icon Position:",
        ["Before Text", "After Text", "Both Ends"],
        key="bracelet_icon_position_multi",
        help="Both Ends จะแบ่งไอคอนครึ่งหนึ่งไว้ก่อนและหลังข้อความ",
    )

bracelet_icon_scale = st.sidebar.slider(
    "Icon Scale on Bead:",
    min_value=0.30,
    max_value=0.90,
    value=0.62,
    step=0.05,
)
st.sidebar.caption("เพิ่มไฟล์ SVG ในโฟลเดอร์ icon แล้วรีสตาร์ตเว็บ รายการจะอัปเดตอัตโนมัติ")

st.sidebar.subheader("🌐 Font Selection")
font_option = st.sidebar.selectbox("Language & Font:", GLOBAL_FONT_OPTIONS, key="chain_font")
selected_font = GLOBAL_FONT_DICT[font_option]
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)

st.sidebar.subheader("📏 Bead Dimensions")
bead_size = st.sidebar.number_input("Bead Size / Width (mm):", value=14.0)
bead_thick = st.sidebar.number_input("Bead Thickness (mm):", value=5.0)
spacing = st.sidebar.number_input("Link Spacing Gap (mm):", value=3.5, step=0.5)

st.sidebar.subheader("🎨 Preview Colors")
col_c1, col_c2 = st.sidebar.columns(2)
color_bead = col_c1.color_picker("Bead Base Color", value="#FADADD")
color_text = col_c2.color_picker("Embossed Text Color", value="#FFD700")

FIX_BG_COLOR = "#2A2A2A"

openscad_exe = get_openscad_path()
temp_dir = session_workdir("chain_bracelet")

if not bracelet_model_text.strip() and not bracelet_icon_files:
    st.info("กรุณาเลือกอย่างน้อย 1 ไอคอน หรือป้อนข้อความก่อนสร้างสร้อย")
    st.stop()

scad_base_code, scad_text_code = generate_bracelet_scad_split(
    text_str=bracelet_model_text,
    font_name=selected_font,
    bead_shape=bead_shape_option,
    text_style=text_style_option,
    connection_mode=connection_mode_option,
    hole_shape=hole_shape_option,
    hole_w=hole_width_val,
    hole_h=hole_height_val,
    bead_size=bead_size,
    bead_thick=bead_thick,
    spacing=spacing,
    icon_files=bracelet_icon_files,
    icon_position=bracelet_icon_position,
    icon_scale=bracelet_icon_scale,
)

render_gate([scad_base_code, scad_text_code], "chain_bracelet")

if scad_base_code and scad_text_code:
    scad_base_p = os.path.join(temp_dir, "bracelet_base.scad")
    stl_base_p = os.path.join(temp_dir, "bracelet_base.stl")
    with open(scad_base_p, "w", encoding="utf-8") as f:
        f.write(scad_base_code)

    scad_text_p = os.path.join(temp_dir, "bracelet_text.scad")
    stl_text_p = os.path.join(temp_dir, "bracelet_text.stl")
    with open(scad_text_p, "w", encoding="utf-8") as f:
        f.write(scad_text_code)

    try:
        render_openscad(openscad_exe, scad_base_p, stl_base_p)
        has_raised_layer = text_style_option == "Embossed (Raised)"
        if has_raised_layer:
            render_openscad(openscad_exe, scad_text_p, stl_text_p)
        elif os.path.exists(stl_text_p):
            os.remove(stl_text_p)

        base_content = ""
        text_content = ""
        if os.path.exists(stl_base_p):
            with open(stl_base_p, "r", encoding="utf-8", errors="ignore") as f:
                base_content = f.read()
        if has_raised_layer and os.path.exists(stl_text_p):
            with open(stl_text_p, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()

        st.markdown("### 👁️ 3D Real-time Preview")

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

                const baseMaterial = new THREE.MeshStandardMaterial({{ color: '{color_bead}', roughness: 0.4, metalness: 0.1 }});
                const textMaterial = new THREE.MeshStandardMaterial({{ color: '{color_text}', roughness: 0.2, metalness: 0.2 }});

                const loader = new THREE.STLLoader();

                const baseString = `{base_content}`;
                if (baseString && baseString.trim().length > 0) {{
                    try {{
                        const geomBase = loader.parse(baseString);
                        const meshBase = new THREE.Mesh(geomBase, baseMaterial);
                        scene.add(meshBase);
                    }} catch(e) {{}}
                }}

                const textString = `{text_content}`;
                if (textString && textString.trim().length > 0) {{
                    try {{
                        const geomText = loader.parse(textString);
                        const meshText = new THREE.Mesh(geomText, textMaterial);
                        scene.add(meshText);
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
        m_base = pv.read(stl_base_p)
        if has_raised_layer and os.path.exists(stl_text_p):
            m_text = pv.read(stl_text_p)
            combined_bracelet = m_base.merge(m_text)
        else:
            combined_bracelet = m_base
        combined_stl_path = os.path.join(temp_dir, "PrintInPlace_Bracelet.stl")
        combined_bracelet.save(combined_stl_path)

        with open(combined_stl_path, "rb") as file:
            bracelet_file_label = bracelet_text.strip() or "Icons_Only"
            st.download_button(
                label="💾 Save & Download Chain Bracelet .STL",
                data=file,
                file_name=f"Bracelet_{bracelet_file_label}.stl",
                mime="application/octet-stream",
                use_container_width=True,
                on_click=record_export,
                args=("chain_bracelet",)
            )

    except Exception as e:
        st.error(f"Render Error: {e}")
