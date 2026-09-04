import os
import tempfile
import subprocess
import streamlit as st
import pyvista as pv
import streamlit.components.v1 as components
from config import ICON_CHOICES, get_openscad_path
from font_catalog import GLOBAL_FONT_OPTIONS, GLOBAL_FONT_DICT, LANGUAGE_FONT_EXAMPLES
from ui_theme import apply_theme
from analytics import record_export
from render_engine import render_gate, render_openscad, session_workdir

apply_theme()

def build_threejs_viewer_box(obj_box_data, obj_lid_data, obj_text_data, color_box, color_text, bg_color="#2A2A2A"):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; background-color: {bg_color}; overflow: hidden; }}
            #canvas-container {{ width: 100vw; height: 500px; }}
        </style>
    </head>
    <body>
        <div id="canvas-container"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
        <script>
            const container = document.getElementById('canvas-container');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color('{bg_color}');

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 2000);
            camera.position.set(150, -200, 150);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            scene.add(ambientLight);

            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(100, 200, 200);
            scene.add(dirLight);

            const gridHelper = new THREE.GridHelper(300, 30, 0x444444, 0x222222);
            gridHelper.rotation.x = Math.PI / 2;
            scene.add(gridHelper);

            const loader = new THREE.OBJLoader();
            const boxMaterial = new THREE.MeshStandardMaterial({{ color: '{color_box}', roughness: 0.4 }});
            const textMaterial = new THREE.MeshStandardMaterial({{ color: '{color_text}', roughness: 0.3, metalness: 0.2 }});

            const objBoxData = "{obj_box_data}";
            if (objBoxData) {{
                const groupBox = loader.parse(objBoxData);
                groupBox.traverse(function (child) {{
                    if (child.isMesh) child.material = boxMaterial;
                }});
                scene.add(groupBox);
            }}

            const objLidData = "{obj_lid_data}";
            if (objLidData) {{
                const groupLid = loader.parse(objLidData);
                groupLid.traverse(function (child) {{
                    if (child.isMesh) child.material = boxMaterial;
                }});
                groupLid.position.x += 160; 
                scene.add(groupLid);
            }}

            const objTextData = "{obj_text_data}";
            if (objTextData) {{
                const groupText = loader.parse(objTextData);
                groupText.traverse(function (child) {{
                    if (child.isMesh) child.material = textMaterial;
                }});
                groupText.position.x += 160;
                scene.add(groupText);
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
    return html_code

def generate_custom_box_scad_split(
    box_shape, box_w, box_l, box_h, wall_thick, bottom_thick,
    cols, rows, enable_vents, vent_dia,
    generate_lid, lid_tolerance,
    line1, line2, line3,
    off1_x, off1_y, off2_x, off2_y, off3_x, off3_y,
    font_name, icon_str, icon_font,
    text_size, text_depth, tolerance
):
    # รวมข้อความ 3 บรรทัดพร้อมเว้นบรรทัดใน OpenSCAD
    text_block = ""
    if line1: text_block += line1
    if line2: text_block += "\\n" + line2
    if line3: text_block += "\\n" + line3

    # สร้างโมดูลข้อความแบบแยกบรรทัดพร้อมตัวปรับตำแหน่ง Offset X/Y เฉพาะตัว
    scad_text_builder = f"""
    module multi_line_text() {{
        // บรรทัดที่ 1
        if ("{line1}" != "") {{
            translate([{off1_x}, {off1_y}, 0])
                text("{line1}", size = {text_size}, font = "{font_name}", halign = "center", valign = "center");
        }}
        // บรรทัดที่ 2
        if ("{line2}" != "") {{
            translate([{off2_x}, {off2_y}, 0])
                text("{line2}", size = {text_size}, font = "{font_name}", halign = "center", valign = "center");
        }}
        // บรรทัดที่ 3
        if ("{line3}" != "") {{
            translate([{off3_x}, {off3_y}, 0])
                text("{line3}", size = {text_size}, font = "{font_name}", halign = "center", valign = "center");
        }}
    }}
    """

    scad_box = f"""
    $fn = 60;
    Box_Shape = "{box_shape}";
    Box_Width = {box_w};
    Box_Length = {box_l};
    Box_Height = {box_h};
    Wall_Thickness = {wall_thick};
    Bottom_Thickness = {bottom_thick};
    Cols = {cols};
    Rows = {rows};
    Enable_Vents = {str(enable_vents).lower()};
    Vent_Diameter = {vent_dia};

    module base_shape(w, l, h) {{
        if (Box_Shape == "Square") {{
            cube([w, l, h]);
        }} else if (Box_Shape == "Heart") {{
            linear_extrude(height=h)
            union() {{
                translate([-w/4, l/6, 0]) circle(r=w/3.2);
                translate([w/4, l/6, 0]) circle(r=w/3.2);
                polygon(points=[[-w/2.05, l/8], [w/2.05, l/8], [0, -l/2]]);
            }}
        }} else if (Box_Shape == "Circle") {{
            cylinder(h=h, r=w/2);
        }} else if (Box_Shape == "Oval") {{
            resize([w, l, h]) cylinder(h=h, r=w/2);
        }} else if (Box_Shape == "Flower") {{
            linear_extrude(height=h)
            union() {{
                circle(r=w*0.25);
                for (a = [0 : 60 : 300]) {{
                    rotate([0, 0, a])
                        translate([w*0.22, 0, 0])
                            circle(r=w*0.2);
                }}
            }}
        }}
    }}

    module compartment_box() {{
        difference() {{
            base_shape(Box_Width, Box_Length, Box_Height);
            
            if (Box_Shape == "Square") {{
                inner_w = Box_Width - (Wall_Thickness * 2);
                inner_l = Box_Length - (Wall_Thickness * 2);
                cell_w = (inner_w - (Cols - 1) * Wall_Thickness) / Cols;
                cell_l = (inner_l - (Rows - 1) * Wall_Thickness) / Rows;

                for (r = [0 : Rows - 1]) {{
                    for (c = [0 : Cols - 1]) {{
                        x_pos = Wall_Thickness + c * (cell_w + Wall_Thickness);
                        y_pos = Wall_Thickness + r * (cell_l + Wall_Thickness);
                        translate([x_pos, y_pos, Bottom_Thickness])
                            cube([cell_w, cell_l, Box_Height]);
                    }}
                }}
            }} else {{
                translate([0, 0, Bottom_Thickness])
                    base_shape(Box_Width - Wall_Thickness*2, Box_Length - Wall_Thickness*2, Box_Height + 5);
            }}
        }}
    }}
    compartment_box();
    """

    scad_lid = f"""
    $fn = 60;
    Box_Shape = "{box_shape}";
    Box_Width = {box_w};
    Box_Length = {box_l};
    Wall_Thickness = {wall_thick};
    Bottom_Thickness = {bottom_thick};
    Lid_Tolerance = {lid_tolerance};
    Text_Depth = {text_depth};
    Tolerance = {tolerance};

    lid_w = Box_Width + (Wall_Thickness * 2) + (Lid_Tolerance * 2);
    lid_l = Box_Length + (Wall_Thickness * 2) + (Lid_Tolerance * 2);
    lid_h = 16; 

    module base_shape(w, l, h) {{
        if (Box_Shape == "Square") {{
            cube([w, l, h]);
        }} else if (Box_Shape == "Heart") {{
            linear_extrude(height=h)
            union() {{
                translate([-w/4, l/6, 0]) circle(r=w/3.2);
                translate([w/4, l/6, 0]) circle(r=w/3.2);
                polygon(points=[[-w/2.05, l/8], [w/2.05, l/8], [0, -l/2]]);
            }}
        }} else if (Box_Shape == "Circle") {{
            cylinder(h=h, r=w/2);
        }} else if (Box_Shape == "Oval") {{
            resize([w, l, h]) cylinder(h=h, r=w/2);
        }} else if (Box_Shape == "Flower") {{
            linear_extrude(height=h)
            union() {{
                circle(r=w*0.25);
                for (a = [0 : 60 : 300]) {{
                    rotate([0, 0, a])
                        translate([w*0.22, 0, 0])
                            circle(r=w*0.2);
                }}
            }}
        }}
    }}

    {scad_text_builder}

    module box_lid() {{
        difference() {{
            base_shape(lid_w, lid_l, lid_h);
            
            translate([0, 0, -0.1])
            if (Box_Shape == "Square") {{
                translate([Wall_Thickness, Wall_Thickness, 0])
                    cube([lid_w - Wall_Thickness*2, lid_l - Wall_Thickness*2, lid_h - Bottom_Thickness + 0.1]);
            }} else {{
                base_shape(Box_Width + (Lid_Tolerance*2), Box_Length + (Lid_Tolerance*2), lid_h - Bottom_Thickness + 0.1);
            }}
                
            if (Box_Shape == "Square") {{
                translate([lid_w / 2, lid_l / 2, lid_h - Text_Depth])
                    linear_extrude(height = Text_Depth + 0.5)
                        offset(r = Tolerance)
                            multi_line_text();
            }} else {{
                translate([0, 0, lid_h - Text_Depth])
                    linear_extrude(height = Text_Depth + 0.5)
                        offset(r = Tolerance)
                            multi_line_text();
            }}
        }}
    }}
    box_lid();
    """

    scad_text = f"""
    $fn = 60;
    Box_Shape = "{box_shape}";
    Box_Width = {box_w};
    Box_Length = {box_l};
    Wall_Thickness = {wall_thick};
    Lid_Tolerance = {lid_tolerance};
    Text_Depth = {text_depth};

    lid_w = Box_Width + (Wall_Thickness * 2) + (Lid_Tolerance * 2);
    lid_l = Box_Length + (Wall_Thickness * 2) + (Lid_Tolerance * 2);
    lid_h = 16;

    {scad_text_builder}

    if (Box_Shape == "Square") {{
        translate([lid_w / 2, lid_l / 2, lid_h - Text_Depth])
            linear_extrude(height = Text_Depth)
                multi_line_text();
    }} else {{
        translate([0, 0, lid_h - Text_Depth])
            linear_extrude(height = Text_Depth)
                multi_line_text();
    }}
    """

    return scad_box, scad_lid, scad_text

st.title("🎁 Bespoke Gift Box & Packaging Pro")
st.subheader("Design luxury custom gift boxes with 3-line customizable text branding")

st.sidebar.subheader("🌟 Box Shape & Dimensions")
box_shape_option = st.sidebar.selectbox(
    "Choose Box Shape:",
    ["Square", "Heart", "Circle", "Oval", "Flower"],
    format_func=lambda x: {
        "Square": "🔲 Square (สี่เหลี่ยม)", 
        "Heart": "❤️ Heart (หัวใจ)", 
        "Circle": "⚪ Circle (วงกลม)", 
        "Oval": "🥚 Oval (วงรี)", 
        "Flower": "🌸 Flower (ดอกไม้)"
    }[x]
)

box_width = st.sidebar.number_input("Box Width (X / Diameter):", value=120.0, step=5.0)
box_length = st.sidebar.number_input("Box Length (Y):", value=120.0, step=5.0)
box_height = st.sidebar.number_input("Box Height (Z):", value=50.0, step=5.0)
wall_thick = st.sidebar.number_input("Wall Thickness:", value=1.6, step=0.2)
bottom_thick = st.sidebar.number_input("Bottom Thickness:", value=2.0, step=0.2)

if box_shape_option == "Square":
    st.sidebar.subheader("🗂️ Compartment Grid")
    cols = st.sidebar.number_input("Columns (Cols):", min_value=1, max_value=10, value=2)
    rows = st.sidebar.number_input("Rows (Rows):", min_value=1, max_value=10, value=2)
    
    st.sidebar.subheader("🌬️ Vent Holes")
    enable_vents = st.sidebar.checkbox("Enable Vent Holes", value=False)
    vent_dia = st.sidebar.number_input("Vent Diameter (mm):", value=6.0, step=0.5)
else:
    cols, rows = 1, 1
    enable_vents = False
    vent_dia = 6.0

st.sidebar.subheader("🧢 Lid Options")
generate_lid = st.sidebar.checkbox("Generate Slip-on Lid", value=True)
lid_tolerance = st.sidebar.number_input("Lid Tolerance:", value=0.4, step=0.05)

st.sidebar.subheader("✨ 3-Line Lid Branding Text")
line1 = st.sidebar.text_input("Line 1 Text:", value="HAPPY")
off1_x = st.sidebar.slider("Line 1 Offset X:", -50.0, 50.0, 0.0, 1.0)
off1_y = st.sidebar.slider("Line 1 Offset Y:", -50.0, 50.0, 15.0, 1.0)

line2 = st.sidebar.text_input("Line 2 Text:", value="BIRTHDAY")
off2_x = st.sidebar.slider("Line 2 Offset X:", -50.0, 50.0, 0.0, 1.0)
off2_y = st.sidebar.slider("Line 2 Offset Y:", -50.0, 50.0, 0.0, 1.0)

line3 = st.sidebar.text_input("Line 3 Text:", value="TO YOU")
off3_x = st.sidebar.slider("Line 3 Offset X:", -50.0, 50.0, 0.0, 1.0)
off3_y = st.sidebar.slider("Line 3 Offset Y:", -50.0, 50.0, -15.0, 1.0)

st.sidebar.subheader("🌐 Font Selection")
font_option = st.sidebar.selectbox("Language & Font:", GLOBAL_FONT_OPTIONS, key="box_font")
selected_font = GLOBAL_FONT_DICT[font_option]
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)

st.sidebar.subheader("⚙️ Inlay & Fit Tolerances")
text_size = st.sidebar.slider("Text Size:", min_value=6.0, max_value=25.0, value=10.0, step=1.0)
text_depth = st.sidebar.slider("Inlay Depth (mm):", min_value=0.5, max_value=3.0, value=1.2, step=0.1)
tolerance = st.sidebar.number_input("Text Fit Tolerance (mm):", value=0.15, step=0.05)

st.sidebar.subheader("🎨 Preview Colors")
col_c1, col_c2 = st.sidebar.columns(2)
color_box = col_c1.color_picker("Box & Lid Color", value="#FF69B4")
color_text = col_c2.color_picker("Inlay Text Color", value="#FFD700")

FIX_BG_COLOR = "#2A2A2A"

openscad_exe = get_openscad_path()
temp_dir = session_workdir("gift_box")

scad_box_code, scad_lid_code, scad_text_code = generate_custom_box_scad_split(
    box_shape=box_shape_option,
    box_w=box_width,
    box_l=box_length,
    box_h=box_height,
    wall_thick=wall_thick,
    bottom_thick=bottom_thick,
    cols=cols,
    rows=rows,
    enable_vents=enable_vents,
    vent_dia=vent_dia,
    generate_lid=generate_lid,
    lid_tolerance=lid_tolerance,
    line1=line1, line2=line2, line3=line3,
    off1_x=off1_x, off1_y=off1_y,
    off2_x=off2_x, off2_y=off2_y,
    off3_x=off3_x, off3_y=off3_y,
    font_name=selected_font,
    icon_str="", icon_font="",
    text_size=text_size,
    text_depth=text_depth,
    tolerance=tolerance
)

render_gate([scad_box_code, scad_lid_code, scad_text_code], "gift_box")

if scad_box_code and scad_lid_code and scad_text_code:
    scad_box_p = os.path.join(temp_dir, "custom_box.scad")
    stl_box_p = os.path.join(temp_dir, "custom_box.stl")
    with open(scad_box_p, "w", encoding="utf-8") as f:
        f.write(scad_box_code)

    scad_lid_p = os.path.join(temp_dir, "custom_lid.scad")
    stl_lid_p = os.path.join(temp_dir, "custom_lid.stl")
    with open(scad_lid_p, "w", encoding="utf-8") as f:
        f.write(scad_lid_code)

    scad_text_p = os.path.join(temp_dir, "custom_text.scad")
    stl_text_p = os.path.join(temp_dir, "custom_text.stl")
    with open(scad_text_p, "w", encoding="utf-8") as f:
        f.write(scad_text_code)

    try:
        render_openscad(openscad_exe, scad_box_p, stl_box_p)
        if generate_lid:
            render_openscad(openscad_exe, scad_lid_p, stl_lid_p)
            render_openscad(openscad_exe, scad_text_p, stl_text_p)

        m_box = pv.read(stl_box_p)
        obj_box_p = os.path.join(temp_dir, "custom_box.obj")
        m_box.save(obj_box_p)
        with open(obj_box_p, "r", encoding="utf-8") as f:
            obj_box_data = f.read().replace("\n", "\\n")

        if generate_lid:
            m_lid = pv.read(stl_lid_p)
            m_text = pv.read(stl_text_p)
            obj_lid_p = os.path.join(temp_dir, "custom_lid.obj")
            obj_text_p = os.path.join(temp_dir, "custom_text.obj")
            m_lid.save(obj_lid_p)
            m_text.save(obj_text_p)
            with open(obj_lid_p, "r", encoding="utf-8") as f:
                obj_lid_data = f.read().replace("\n", "\\n")
            with open(obj_text_p, "r", encoding="utf-8") as f:
                obj_text_data = f.read().replace("\n", "\\n")
            
            three_html = build_threejs_viewer_box(obj_box_data, obj_lid_data, obj_text_data, color_box, color_text, bg_color=FIX_BG_COLOR)
        else:
            three_html = build_threejs_viewer_box(obj_box_data, "", "", color_box, color_text, bg_color=FIX_BG_COLOR)

        st.markdown("### 👁️ 3D Real-time Preview")
        components.html(three_html, height=520, scrolling=False)

        st.markdown("---")
        if generate_lid:
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with open(stl_box_p, "rb") as f1:
                col_dl1.download_button("💾 Box Body .STL", f1, "Box_Body.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("gift_box",))
            with open(stl_lid_p, "rb") as f2:
                col_dl2.download_button("💾 Slip-on Lid .STL", f2, "Box_Lid.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("gift_box",))
            with open(stl_text_p, "rb") as f3:
                col_dl3.download_button("💾 Inlay Text .STL", f3, "Box_InlayText.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("gift_box",))
        else:
            with open(stl_box_p, "rb") as f1:
                st.download_button("💾 Box Body .STL", f1, "Box_Body.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("gift_box",))

    except Exception as e:
        st.error(f"Render Error: {e}")
