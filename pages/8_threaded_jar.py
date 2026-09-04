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

def build_threejs_jar_viewer(obj_jar_data, obj_lid_data, color_jar, color_lid, bg_color="#2A2A2A"):
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
            camera.position.set(120, -180, 120);

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
            const jarMaterial = new THREE.MeshStandardMaterial({{ color: '{color_jar}', roughness: 0.3 }});
            const lidMaterial = new THREE.MeshStandardMaterial({{ color: '{color_lid}', roughness: 0.3 }});

            const objJarData = "{obj_jar_data}";
            if (objJarData) {{
                const groupJar = loader.parse(objJarData);
                groupJar.traverse(function (child) {{
                    if (child.isMesh) child.material = jarMaterial;
                }});
                scene.add(groupJar);
            }}

            const objLidData = "{obj_lid_data}";
            if (objLidData) {{
                const groupLid = loader.parse(objLidData);
                groupLid.traverse(function (child) {{
                    if (child.isMesh) child.material = lidMaterial;
                }});
                groupLid.position.x += 80; 
                scene.add(groupLid);
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

def generate_jar_scad_split(
    jar_outer_size, jar_height, wall_thick, outer_shape,
    lid_height, enable_thread, thread_pitch, thread_turns, tolerance,
    enable_keychain, keychain_orientation,
    line1, line2, text_size, text_style, thai_font
):
    scad_jar = f"""
    $fn = 60;
    Jar_Outer_Size = {jar_outer_size};
    Jar_Height = {jar_height};
    Wall_Thickness = {wall_thick};
    Outer_Shape = "{outer_shape}";
    Lid_Height = {lid_height};
    Enable_Thread = {str(enable_thread).lower()};
    Thread_Pitch = {thread_pitch};
    Thread_Turns = {thread_turns};
    Tolerance = {tolerance};

    jar_r = Jar_Outer_Size / 2;
    thread_h = Enable_Thread ? (Thread_Turns * Thread_Pitch) : 0;
    thread_depth = Enable_Thread ? (Thread_Pitch * 0.4) : 0;
    body_h = Jar_Height - thread_h;

    outer_fn = (Outer_Shape == "Hexagon") ? 6 : ((Outer_Shape == "Square") ? 4 : 100);
    hex_flat_r = (Outer_Shape == "Hexagon") ? jar_r * cos(30) : ((Outer_Shape == "Square") ? jar_r : jar_r);

    module base_shape(shape, size, h) {{
        if (shape == "Cylinder") {{
            cylinder(r = size/2, h = h, $fn = 100);
        }} else if (shape == "Hexagon") {{
            cylinder(r = size/2, h = h, $fn = 6);
        }} else if (shape == "Square") {{
            translate([-size/2, -size/2, 0]) cube([size, size, h]);
        }}
    }}

    module polygon_point_tri(r_in, r_out, p) {{
        rotate([90, 0, 0])
            linear_extrude(height = 0.1, center = true)
                polygon(points = [[r_in, -p/3], [r_out, 0], [r_in, p/3]]);
    }}

    module jar_male_thread(d, p, h) {{
        r_inner = d / 2;
        r_outer = r_inner + thread_depth;
        turns = h / p;
        steps_per_turn = 32;
        total_steps = floor(turns * steps_per_turn);
        
        for (i = [0 : total_steps - 1]) {{
            a1 = i * (360 / steps_per_turn);
            a2 = (i + 1) * (360 / steps_per_turn);
            z1 = i * (p / steps_per_turn);
            z2 = (i + 1) * (p / steps_per_turn);
            
            if (z2 < h) {{
                hull() {{
                    rotate([0, 0, a1]) translate([0, 0, z1]) polygon_point_tri(r_inner, r_outer, p);
                    rotate([0, 0, a2]) translate([0, 0, z2]) polygon_point_tri(r_inner, r_outer, p);
                }}
            }}
        }}
    }}

    cavity_r = hex_flat_r - Wall_Thickness;

    union() {{
        difference() {{
            union() {{
                // 1. โครงนอกหลัก
                base_shape(Outer_Shape, Jar_Outer_Size, body_h);
                
                // 2. คอเกลียว/คอปากกระปุก
                if (Enable_Thread) {{
                    translate([0, 0, body_h])
                        cylinder(r = cavity_r + Wall_Thickness - 0.2, h = thread_h, $fn = 100);

                    translate([0, 0, body_h])
                        jar_male_thread((cavity_r + Wall_Thickness - 0.2) * 2, Thread_Pitch, thread_h);
                }}
            }}
            
            // 3. คว้านโพรงกลมภายใน
            translate([0, 0, Wall_Thickness])
                cylinder(r = cavity_r, h = Jar_Height + 1, $fn = 100);
        }}
    }}
    """

    scad_lid = f"""
    $fn = 60;
    Jar_Outer_Size = {jar_outer_size};
    Wall_Thickness = {wall_thick};
    Outer_Shape = "{outer_shape}";
    Lid_Height = {lid_height};
    Enable_Thread = {str(enable_thread).lower()};
    Thread_Pitch = {thread_pitch};
    Tolerance = {tolerance};

    Enable_Keychain = {str(enable_keychain).lower()};
    Keychain_Orientation = "{keychain_orientation}";

    Custom_Text_Line1 = "{line1}";
    Custom_Text_Line2 = "{line2}";
    Text_Size = {text_size};
    Text_Style = "{text_style}";
    Thai_Font = "{thai_font}";

    jar_r = Jar_Outer_Size / 2;
    hex_flat_r = (Outer_Shape == "Hexagon") ? jar_r * cos(30) : ((Outer_Shape == "Square") ? jar_r : jar_r);
    cavity_r = hex_flat_r - Wall_Thickness;
    thread_depth = Enable_Thread ? (Thread_Pitch * 0.4) : 0;

    male_outer_r = Enable_Thread ? ((cavity_r + Wall_Thickness - 0.2) + thread_depth) : jar_r;
    lid_cut_r = male_outer_r + (Tolerance / 2);
    lid_outer_r = (Outer_Shape == "Hexagon") ? (lid_cut_r + Wall_Thickness) / cos(30) : (lid_cut_r + Wall_Thickness); 
    lid_outer_size = lid_outer_r * 2;
    lid_depth = Lid_Height - Wall_Thickness;
    y_offset = (len(Custom_Text_Line2) > 0) ? (Text_Size * 0.7) : 0;

    module base_shape(shape, size, h) {{
        if (shape == "Cylinder") {{
            cylinder(r = size/2, h = h, $fn = 100);
        }} else if (shape == "Hexagon") {{
            cylinder(r = size/2, h = h, $fn = 6);
        }} else if (shape == "Square") {{
            translate([-size/2, -size/2, 0]) cube([size, size, h]);
        }}
    }}

    module jar_female_thread_cutter(d, p, h) {{
        r_outer = d / 2;
        r_inner = r_outer - thread_depth;
        turns = h / p;
        steps_per_turn = 32;
        total_steps = floor(turns * steps_per_turn);
        
        cylinder(r = r_inner, h = h + 0.2, $fn = 100);
        
        for (i = [0 : total_steps - 1]) {{
            a1 = i * (360 / steps_per_turn);
            a2 = (i + 1) * (360 / steps_per_turn);
            z1 = i * (p / steps_per_turn);
            z2 = (i + 1) * (p / steps_per_turn);
            
            if (z2 < h) {{
                hull() {{
                    rotate([0, 0, a1]) translate([0, 0, z1]) polygon_point_tri_cutter(r_inner - 0.1, r_outer + 0.2, p);
                    rotate([0, 0, a2]) translate([0, 0, z2]) polygon_point_tri_cutter(r_inner - 0.1, r_outer + 0.2, p);
                }}
            }}
        }}
    }}

    module polygon_point_tri_cutter(r_in, r_out, p) {{
        rotate([90, 0, 0])
            linear_extrude(height = 0.1, center = true)
                polygon(points = [[r_in, -p/3], [r_out, 0], [r_in, p/3]]);
    }}

    difference() {{
        union() {{
            base_shape(Outer_Shape, lid_outer_size, Lid_Height);
            
            if (Enable_Keychain) {{
                translate([lid_outer_r + 3.5, 0, Lid_Height / 2])
                    if (Keychain_Orientation == "Vertical") {{
                        rotate([90, 0, 0])
                            difference() {{
                                cylinder(r = 5, h = 3, center = true, $fn=50);
                                cylinder(r = 2.5, h = 4, center = true, $fn=50);
                            }}
                    }} else {{
                        rotate([0, 90, 0])
                            difference() {{
                                cylinder(r = 5, h = 3, center = true, $fn=50);
                                cylinder(r = 2.5, h = 4, center = true, $fn=50);
                            }}
                    }}
            }}

            if (Text_Style == "Embossed") {{
                translate([0, y_offset, Lid_Height])
                    linear_extrude(height = 1.0)
                        text(Custom_Text_Line1, size = Text_Size, halign = "center", valign = "center", font = Thai_Font);
                if (len(Custom_Text_Line2) > 0) {{
                    translate([0, -y_offset, Lid_Height])
                        linear_extrude(height = 1.0)
                            text(Custom_Text_Line2, size = Text_Size * 0.85, halign = "center", valign = "center", font = Thai_Font);
                }}
            }}
        }}
        
        translate([0, 0, -0.1])
            if (Enable_Thread) {{
                jar_female_thread_cutter(lid_cut_r * 2, Thread_Pitch, lid_depth + 0.1);
            }} else {{
                cylinder(r = lid_cut_r, h = lid_depth + 0.1, $fn = 100);
            }}
            
        if (Text_Style == "Engraved") {{
            translate([0, y_offset, Lid_Height - 0.8])
                linear_extrude(height = 1.0)
                    text(Custom_Text_Line1, size = Text_Size, halign = "center", valign = "center", font = Thai_Font);
            if (len(Custom_Text_Line2) > 0) {{
                translate([0, -y_offset, Lid_Height - 0.8])
                    linear_extrude(height = 1.0)
                        text(Custom_Text_Line2, size = Text_Size * 0.85, halign = "center", valign = "center", font = Thai_Font);
            }}
        }}
    }}
    """
    return scad_jar, scad_lid

st.title("Jar & Lid Studio")
st.subheader("Design parametric jars & custom threaded lids")

st.sidebar.subheader("Jar Dimensions & Shape")
jar_outer_size = st.sidebar.number_input("Outer Diameter / Width (mm):", value=50.0, step=5.0)
jar_height = st.sidebar.number_input("Jar Height (mm):", value=30.0, step=5.0)
wall_thick = st.sidebar.number_input("Wall Thickness (mm):", value=3.0, step=0.5)

outer_shape = st.sidebar.selectbox(
    "Outer Shape:", 
    ["Hexagon", "Cylinder", "Square"], 
    format_func=lambda x: {"Hexagon": "Hexagon (หกเหลี่ยม)", "Cylinder": "Cylinder (ทรงกลม)", "Square": "Square (สี่เหลี่ยม)"}[x]
)

st.sidebar.subheader("Thread & Lid Settings")
enable_thread = st.sidebar.checkbox("Enable Thread (เกลียวหมุน)", value=True)
lid_height = st.sidebar.number_input("Lid Height (mm):", value=12.0, step=1.0)
if enable_thread:
    thread_pitch = st.sidebar.number_input("Thread Pitch:", value=3.5, step=0.5)
    thread_turns = st.sidebar.number_input("Thread Turns:", value=2.0, step=0.5)
    tolerance = st.sidebar.number_input("Tolerance:", value=0.7, step=0.05)
else:
    thread_pitch, thread_turns, tolerance = 3.5, 2.0, 0.4

st.sidebar.subheader("Keychain & Lid Text")
enable_keychain = st.sidebar.checkbox("Enable Keychain Loop", value=True)
keychain_orientation = st.sidebar.selectbox("Keychain Orientation:", ["Vertical", "Horizontal"])

custom_text_line1 = st.sidebar.text_input("Line 1 Text:", value="Vit C")
custom_text_line2 = st.sidebar.text_input("Line 2 Text:", value="วิตามินซี")
text_size = st.sidebar.slider("Text Size:", 3.0, 10.0, 5.0, 0.5)
text_style = st.sidebar.selectbox("Text Style:", ["Engraved", "Embossed"], format_func=lambda x: "Engraved (ตัวจม)" if x == "Engraved" else "Embossed (ตัวนูน)")

font_option = st.sidebar.selectbox("Language & Font:", GLOBAL_FONT_OPTIONS, key="jar_font")
thai_font = GLOBAL_FONT_DICT[font_option]
st.sidebar.caption(LANGUAGE_FONT_EXAMPLES)

color_jar = "#3A8891"
color_lid = "#E25E3E"

FIX_BG_COLOR = "#2A2A2A"
openscad_exe = get_openscad_path()
temp_dir = session_workdir("threaded_jar")

scad_jar_code, scad_lid_code = generate_jar_scad_split(
    jar_outer_size=jar_outer_size,
    jar_height=jar_height,
    wall_thick=wall_thick,
    outer_shape=outer_shape,
    lid_height=lid_height,
    enable_thread=enable_thread,
    thread_pitch=thread_pitch if enable_thread else 0,
    thread_turns=thread_turns if enable_thread else 0,
    tolerance=tolerance if enable_thread else 0.4,
    enable_keychain=enable_keychain,
    keychain_orientation=keychain_orientation,
    line1=custom_text_line1,
    line2=custom_text_line2,
    text_size=text_size,
    text_style=text_style,
    thai_font=thai_font
)

render_gate([scad_jar_code, scad_lid_code], "threaded_jar")

if scad_jar_code and scad_lid_code:
    scad_jar_p = os.path.join(temp_dir, "jar_body.scad")
    stl_jar_p = os.path.join(temp_dir, "jar_body.stl")
    with open(scad_jar_p, "w", encoding="utf-8") as f:
        f.write(scad_jar_code)

    scad_lid_p = os.path.join(temp_dir, "jar_lid.scad")
    stl_lid_p = os.path.join(temp_dir, "jar_lid.stl")
    with open(scad_lid_p, "w", encoding="utf-8") as f:
        f.write(scad_lid_code)

    try:
        render_openscad(openscad_exe, scad_jar_p, stl_jar_p)
        render_openscad(openscad_exe, scad_lid_p, stl_lid_p)

        m_jar = pv.read(stl_jar_p)
        m_lid = pv.read(stl_lid_p)
        obj_jar_p = os.path.join(temp_dir, "jar_body.obj")
        obj_lid_p = os.path.join(temp_dir, "jar_lid.obj")
        m_jar.save(obj_jar_p)
        m_lid.save(obj_lid_p)

        with open(obj_jar_p, "r", encoding="utf-8") as f:
            obj_jar_data = f.read().replace("\n", "\\n")
        with open(obj_lid_p, "r", encoding="utf-8") as f:
            obj_lid_data = f.read().replace("\n", "\\n")

        st.markdown("### 👁️ 3D Real-time Preview")
        three_html = build_threejs_jar_viewer(obj_jar_data, obj_lid_data, color_jar, color_lid, bg_color=FIX_BG_COLOR)
        components.html(three_html, height=520, scrolling=False)

        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        with open(stl_jar_p, "rb") as f1:
            col_dl1.download_button("💾 Download Jar Body .STL", f1, "Jar_Body.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("threaded_jar",))
        with open(stl_lid_p, "rb") as f2:
            col_dl2.download_button("💾 Download Jar Lid .STL", f2, "Jar_Lid.stl", mime="application/octet-stream", use_container_width=True, on_click=record_export, args=("threaded_jar",))

    except Exception as e:
        st.error(f"Render Error: {e}")
