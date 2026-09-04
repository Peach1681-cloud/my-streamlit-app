import os
import tempfile
import subprocess
import streamlit as st
import pyvista as pv
import streamlit.components.v1 as components

try:
    import qrcode
    import cv2
    import numpy as np
    from PIL import Image
    HAS_QR_LIBS = True
except ImportError:
    HAS_QR_LIBS = False

st.set_page_config(
    page_title="Global 3D Creator Studio Pro",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASSCODE_CORRECT = "1681"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"

if not st.session_state["authenticated"]:
    st.title("🔒 3D Studio Generator - Web App Access")
    st.subheader("Please enter your PIN code to access the studio program.")
    
    col_login, col_contact = st.columns([1.5, 1])
    
    with col_login:
        input_pin = st.text_input("Access PIN Code:", type="password")
        if st.button("🔓 Login Studio", type="primary", use_container_width=True):
            if input_pin == PASSCODE_CORRECT:
                st.session_state["authenticated"] = True
                st.success("Correct PIN! Loading studio...")
                st.rerun()
            else:
                st.error("❌ Incorrect PIN code. Please try again.")
                
    with col_contact:
        st.info("📞 **Forgot PIN / Support & Inquiry**")
        st.write("Contact system administrator via channels below:")
        st.markdown("💬 **Facebook:** [Peach Studio](https://www.facebook.com/profile.php?id=61590771869852)")
        st.markdown("💚 **Line ID:** `peach1681` (https://line.me/ti/p/~peach1681)")
        st.markdown("📞 **Tel / WhatsApp:** +66 93 323 9693")
            
    st.stop()

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

def generate_qr_scad_split(qr_data, label_text="", qr_size=40, base_thick=3.0, qr_thick=1.5, hole_dia=5.0, ring_type="Corner Hole", hole_margin=3.0):
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
    label_txt = "{label_text.strip().upper()}";
    
    translate([0, 0, base_thick]) {{
        if (label_txt != "") {{
            translate([qr_size / 2, -6.5, 0])
                linear_extrude(height = qr_thick)
                    text(text = label_txt, size = 5, font = "Montserrat:style=Bold", halign = "center", valign = "baseline");
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

SCAD_BASE_TEMPLATE = """
Prefix_Icon = "{icon_str}";
Name = "{name}"; 
Show_Second_Line = {show_second_line}; 
Second_Line = "{second_line}"; 
Font_Name = "{font_name}"; 
Icon_Font = "{icon_font}";
Text_Size = {text_size}; 
Second_Line_Size = {second_line_size}; 
Base_Thickness = {base_thickness}; 
Outline_Size = {outline_size}; 
Hole_Diameter = {hole_diameter}; 
Hole_Ring_Thickness = {hole_ring_thickness}; 
Hole_X_Offset = {hole_x_offset};
Icon_Spacing = {icon_spacing};
$fn = 60; 

module text_2d() {{
    union() {{
        if (Prefix_Icon != "") {{
            text(text = Prefix_Icon, size = Text_Size, font = Icon_Font, halign = "left", valign = "baseline");
            translate([Icon_Spacing, 0, 0])
                text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
        }} else {{
            text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
        }}
        
        if (Show_Second_Line) {{
            translate([0, -(Second_Line_Size + 4), 0])
                text(text = Second_Line, size = Second_Line_Size, font = Font_Name, halign = "left", valign = "baseline");
        }}
    }}
}}

linear_extrude(height = Base_Thickness) {{
    union() {{
        offset(r = Outline_Size) {{ text_2d(); }}
        
        ring_outer_radius = (Hole_Diameter / 2) + Hole_Ring_Thickness;
        translate([Hole_X_Offset, Text_Size / 2, 0]) {{
            difference() {{
                circle(r = ring_outer_radius);
                circle(r = Hole_Diameter / 2);
            }}
        }}
    }}
}}
"""

SCAD_TEXT_TEMPLATE = """
Prefix_Icon = "{icon_str}";
Name = "{name}"; 
Show_Second_Line = {show_second_line}; 
Second_Line = "{second_line}"; 
Font_Name = "{font_name}"; 
Icon_Font = "{icon_font}";
Text_Size = {text_size}; 
Second_Line_Size = {second_line_size}; 
Base_Thickness = {base_thickness}; 
Text_Thickness = {text_thickness}; 
Icon_Spacing = {icon_spacing};
$fn = 60; 

module text_2d() {{
    union() {{
        if (Prefix_Icon != "") {{
            text(text = Prefix_Icon, size = Text_Size, font = Icon_Font, halign = "left", valign = "baseline");
            translate([Icon_Spacing, 0, 0])
                text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
        }} else {{
            text(text = Name, size = Text_Size, font = Font_Name, halign = "left", valign = "baseline");
        }}
        
        if (Show_Second_Line) {{
            translate([0, -(Second_Line_Size + 4), 0])
                text(text = Second_Line, size = Second_Line_Size, font = Font_Name, halign = "left", valign = "baseline");
        }}
    }}
}}

translate([0, 0, Base_Thickness]) {{
    linear_extrude(height = Text_Thickness) {{
        text_2d();
    }}
}}
"""

def generate_lightbox_scad_split(text_string, font_name, letter_size, letter_spacing, box_depth, wall_thick, cover_face_thick, lip_height, tolerance, lip_thick_reduce, cover_margin, cover_offset_y):
    string_len = len(text_string)
    
    scad_box = f"""
    $fn = 60;
    Text_String = "{text_string}";
    Font_Name = "{font_name}";
    Letter_Size = {letter_size};
    Letter_Spacing = {letter_spacing};
    Box_Depth = {box_depth};
    Wall_Thickness = {wall_thick};
    string_len = {string_len};

    for (i = [0 : string_len - 1]) {{
        translate([i * Letter_Spacing, 0, 0]) {{
            difference() {{
                linear_extrude(height = Box_Depth)
                    text(Text_String[i], size = Letter_Size, font = Font_Name, halign = "center", valign = "center");
                
                translate([0, 0, Wall_Thickness])
                    linear_extrude(height = Box_Depth)
                        offset(r = -Wall_Thickness)
                            text(Text_String[i], size = Letter_Size, font = Font_Name, halign = "center", valign = "center");
            }}
        }}
    }}
    """
    
    scad_cover = f"""
    $fn = 60;
    Text_String = "{text_string}";
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
    string_len = {string_len};

    module single_letter_cover(char) {{
        rotate([180, 0, 0]) {{
            mirror([1, 0, 0]) {{
                union() {{
                    linear_extrude(height = Cover_Face_Thick)
                        offset(r = Cover_Lip_Margin)
                            text(char, size = Letter_Size, font = Font_Name, halign = "center", valign = "center");
                        
                    translate([0, 0, Cover_Face_Thick]) {{
                        difference() {{
                            linear_extrude(height = Lip_Height)
                                offset(r = -Wall_Thickness - (Tolerance / 2))
                                    text(char, size = Letter_Size, font = Font_Name, halign = "center", valign = "center");
                                    
                            translate([0, 0, -0.1])
                                linear_extrude(height = Lip_Height + 0.2)
                                    offset(r = -Wall_Thickness - (Tolerance / 2) - (Wall_Thickness - Lip_Thick_Reduce))
                                        text(char, size = Letter_Size, font = Font_Name, halign = "center", valign = "center");
                        }}
                    }}
                }}
            }}
        }}
    }}

    for (i = [0 : string_len - 1]) {{
        translate([i * Letter_Spacing, Cover_Offset_Y, Cover_Face_Thick + Lip_Height])
            single_letter_cover(Text_String[i]);
    }}
    """
    
    return scad_box, scad_cover

def generate_monogram_scad_split(big_letter, big_font, name_text, name_font, big_size, big_thick, name_thick, ratio, recess_depth, tolerance, spacing, name_char_spacing, offset_y, view_mode="combined"):
    scad_base = f"""
    $fn = 60;
    Letter = "{big_letter}";
    Letter_Font = "{big_font}";
    Name = "{name_text}";
    Name_Font = "{name_font}";
    Letter_Size = {big_size};
    Letter_Thickness = {big_thick};
    Name_Size_Ratio = {ratio};
    Recess_Depth = {recess_depth};
    Tolerance = {tolerance};
    Offset_Y = {offset_y};

    module raw_base_letter() {{
        linear_extrude(height = Letter_Thickness) {{
            text(text = Letter, size = Letter_Size, font = Letter_Font, halign = "center", valign = "center");
        }}
    }}

    module name_cutter() {{
        translate([0, Offset_Y, 0])
            linear_extrude(height = Recess_Depth + 0.1) {{
                offset(r = 0.5 + Tolerance) {{
                    text(text = Name, size = Letter_Size * Name_Size_Ratio, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
                }}
            }}
    }}

    difference() {{
        raw_base_letter();
        translate([0, 0, Letter_Thickness - Recess_Depth]) {{
            name_cutter();
        }}
    }}
    """

    if view_mode == "combined":
        trans_y = offset_y
        trans_z = big_thick - recess_depth
    else:
        trans_y = -spacing + offset_y
        trans_z = 0

    scad_name = f"""
    $fn = 60;
    Name = "{name_text}";
    Name_Font = "{name_font}";
    Letter_Size = {big_size};
    Name_Thickness = {name_thick};
    Name_Size_Ratio = {ratio};

    translate([0, {trans_y}, {trans_z}]) {{
        linear_extrude(height = Name_Thickness) {{
            offset(r = 0.5) {{
                text(text = Name, size = Letter_Size * Name_Size_Ratio, font = Name_Font, halign = "center", valign = "center", spacing = {name_char_spacing});
            }}
        }}
    }}
    """
    
    return scad_base, scad_name

def get_openscad_path():
    exact = r"C:\Program Files (x86)\OpenSCAD\openscad.exe"
    if os.path.exists(exact):
        return exact
    return "openscad"

def build_threejs_viewer(obj_base_data, obj_text_data, color_base, color_text, bg_color="#1E1E1E"):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; overflow: hidden; background-color: {bg_color}; }}
            #canvas-container {{ width: 100vw; height: 100vh; }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
    </head>
    <body>
        <div id="canvas-container"></div>
        <script>
            const container = document.getElementById('canvas-container');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color("{bg_color}");

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, -80, 80);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            scene.add(ambientLight);

            const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight1.position.set(1, -1, 2);
            scene.add(dirLight1);

            const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
            dirLight2.position.set(-1, 1, -1);
            scene.add(dirLight2);

            const loader = new THREE.OBJLoader();

            const baseObj = loader.parse(`{obj_base_data}`);
            const baseMat = new THREE.MeshStandardMaterial({{ color: "{color_base}", roughness: 0.4, metalness: 0.1 }});
            baseObj.traverse((child) => {{ if (child.isMesh) child.material = baseMat; }});
            scene.add(baseObj);

            if (`{obj_text_data}`.trim() !== "") {{
                const textObj = loader.parse(`{obj_text_data}`);
                const textMat = new THREE.MeshStandardMaterial({{ color: "{color_text}", roughness: 0.4, metalness: 0.1 }});
                textObj.traverse((child) => {{ if (child.isMesh) child.material = textMat; }});
                scene.add(textObj);
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();

            window.addEventListener('resize', () => {{
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }});
        </script>
    </body>
    </html>
    """
    return html_code

st.sidebar.title("⚙️ Control Panel")

if st.sidebar.button("🏠 Dashboard Home", use_container_width=True):
    st.session_state["current_page"] = "dashboard"
    st.rerun()

if st.sidebar.button("🔒 Logout Studio", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["current_page"] = "dashboard"
    st.rerun()

st.sidebar.markdown("---")

if st.session_state["current_page"] == "dashboard":
    st.title("✨ Global 3D Creator Studio Pro")
    st.subheader("Welcome! Please select a 3D project generator to start.")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏷️ 3D Text Keychain")
        st.info("Create custom multi-color 3D text keychains supporting global fonts (Kanit, Prompt, Pacifico, etc.)")
        if st.button("👉 Launch Text Keychain Studio", type="primary", use_container_width=True):
            st.session_state["current_page"] = "text_keychain"
            st.rerun()
            
    with col2:
        st.markdown("### 📱 3D QR Code Keychain")
        st.info("Create scannable 3D QR Code keychains for PromptPay, Social Media, and website links.")
        if st.button("👉 Launch QR Code Studio", type="primary", use_container_width=True):
            st.session_state["current_page"] = "qr_keychain"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("### 📌 3D Monogram Name Sign")
        st.info("Create luxury multi-character recessed initial signs with removable front name inserts.")
        if st.button("👉 Launch Monogram Sign Studio", use_container_width=True):
            st.session_state["current_page"] = "monogram_sign"
            st.rerun()

    with col4:
        st.markdown("### 💡 3D LED Lightbox Studio")
        st.info("Create hollow 3D text lightboxes for LED strips with custom translucent face covers.")
        if st.button("👉 Launch LED Lightbox Studio", use_container_width=True):
            st.session_state["current_page"] = "led_lightbox"
            st.rerun()

elif st.session_state["current_page"] == "text_keychain":
    st.title("🏷️ 3D Text Keychain Generator")

    st.sidebar.subheader("🌐 Font Selection")
    font_option = st.sidebar.selectbox(
        "Choose Font Style:",
        [
            "Kanit (Modern Bold)",
            "Prompt (Elegant Clean)",
            "Pacifico (Cursive Cute)",
            "Montserrat (Wide Bold)",
            "Sarabun (Standard Serif)",
            "Noto Sans JP (Japanese)",
            "Noto Sans KR (Korean)",
            "Noto Sans SC (Chinese)",
            "Custom Font",
        ]
    )

    google_font_dict = {
        "Kanit (Modern Bold)": "Kanit:style=Bold",
        "Prompt (Elegant Clean)": "Prompt:style=Bold",
        "Pacifico (Cursive Cute)": "Pacifico:style=Regular",
        "Montserrat (Wide Bold)": "Montserrat:style=Bold",
        "Sarabun (Standard Serif)": "Sarabun:style=Bold",
        "Noto Sans JP (Japanese)": "Noto Sans JP:style=Bold",
        "Noto Sans KR (Korean)": "Noto Sans KR:style=Bold",
        "Noto Sans SC (Chinese)": "Noto Sans SC:style=Bold",
        "Custom Font": "Kanit:style=Bold",
    }

    if font_option == "Custom Font":
        input_font = st.sidebar.text_input("Custom Font Name:", value="Kanit:style=Bold")
    else:
        selected_font = google_font_dict[font_option]
        st.sidebar.info(f"🔤 Active Font: `{selected_font.split(':')[0]}`")
        input_font = selected_font

    st.sidebar.subheader("✨ Prefix Icon")
    icon_choices = {
        "None": "",
        "🎵 Music Note": "🎵",
        "★ Lucky Star": "★",
        "♥ Heart": "♥",
        "ॐ Om Symbol": "ॐ",
        "✿ Flower": "✿",
        "♔ Crown": "♔",
        "♣ Lucky Clover": "♣",
        "☯ Yin Yang": "☯",
        "✦ Sparkle": "✦",
        "⚡ Lightning": "⚡",
    }

    selected_icon_label = st.sidebar.selectbox("Choose Icon Symbol:", list(icon_choices.keys()))
    icon_symbol = icon_choices[selected_icon_label]

    if icon_symbol == "ॐ":
        icon_font = "Nirmala UI:style=Bold"
    else:
        icon_font = "Segoe UI Symbol:style=Regular"

    st.sidebar.subheader("📝 Text Configuration")
    input_name = st.sidebar.text_input("Main Text:", value="LUCKY")
    chk_second_line = st.sidebar.checkbox("Enable Sub-Text Line", value=True)
    input_second = st.sidebar.text_input("Sub-Text Line:", value="+66 93 323 9693", disabled=not chk_second_line)

    st.sidebar.subheader("🔤 Text Size")
    text_size = st.sidebar.number_input("Main Text Size (mm):", value=20)
    sub_size = st.sidebar.number_input("Sub-Text Size (mm):", value=10)

    st.sidebar.subheader("📍 Layout & Ring Position")
    icon_spacing_val = st.sidebar.slider("Icon - Text Spacing (mm):", min_value=15.0, max_value=40.0, value=25.0, step=0.5)
    hole_x_offset_val = st.sidebar.slider("Ring X Position:", min_value=-30.0, max_value=10.0, value=-5.0, step=0.5)

    st.sidebar.subheader("🎨 Preview Colors")
    col_c1, col_c2 = st.sidebar.columns(2)
    color_base = col_c1.color_picker("Base Color", value="#FF00FF")
    color_text = col_c2.color_picker("Text Color", value="#000000")

    st.sidebar.subheader("📏 Dimensions & Ring")
    base_thick = st.sidebar.number_input("Base Thickness (mm):", value=3.0)
    text_thick = st.sidebar.number_input("Raised Text Thickness (mm):", value=2.0)
    outline_size = st.sidebar.number_input("Base Outline Margin (mm):", value=3.0)
    hole_dia = st.sidebar.number_input("Hole Diameter (mm):", value=5.0)

    openscad_exe = get_openscad_path()
    temp_dir = tempfile.gettempdir()

    params = {
        "icon_str": icon_symbol,
        "icon_font": icon_font,
        "name": input_name,
        "show_second_line": "true" if chk_second_line else "false",
        "second_line": input_second,
        "font_name": input_font,
        "text_size": text_size,
        "second_line_size": sub_size,
        "base_thickness": base_thick,
        "text_thickness": text_thick,
        "outline_size": outline_size,
        "hole_diameter": hole_dia,
        "hole_ring_thickness": 3,
        "hole_x_offset": hole_x_offset_val,
        "icon_spacing": icon_spacing_val,
    }

    scad_base_p = os.path.join(temp_dir, "web_base.scad")
    stl_base_p = os.path.join(temp_dir, "web_base.stl")
    with open(scad_base_p, "w", encoding="utf-8") as f:
        f.write(SCAD_BASE_TEMPLATE.format(**params))

    scad_text_p = os.path.join(temp_dir, "web_text.scad")
    stl_text_p = os.path.join(temp_dir, "web_text.stl")
    with open(scad_text_p, "w", encoding="utf-8") as f:
        f.write(SCAD_TEXT_TEMPLATE.format(**params))

    try:
        subprocess.run([openscad_exe, "-o", stl_base_p, scad_base_p], check=True)
        subprocess.run([openscad_exe, "-o", stl_text_p, scad_text_p], check=True)

        m_base = pv.read(stl_base_p)
        m_text = pv.read(stl_text_p)

        obj_base_p = os.path.join(temp_dir, "base.obj")
        obj_text_p = os.path.join(temp_dir, "text.obj")

        m_base.save(obj_base_p)
        m_text.save(obj_text_p)

        with open(obj_base_p, "r", encoding="utf-8") as f:
            obj_base_data = f.read().replace("\n", "\\n")

        with open(obj_text_p, "r", encoding="utf-8") as f:
            obj_text_data = f.read().replace("\n", "\\n")

        three_html = build_threejs_viewer(obj_base_data, obj_text_data, color_base, color_text)
        components.html(three_html, height=520, scrolling=False)

        combined = m_base.merge(m_text)
        combined_stl_path = os.path.join(temp_dir, "keychain_final.stl")
        combined.save(combined_stl_path)

        with open(combined_stl_path, "rb") as file:
            st.download_button(
                label="💾 Save & Download .STL File",
                data=file,
                file_name=f"Keychain_{input_name}.stl",
                mime="application/octet-stream",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Render Error: {e}")

elif st.session_state["current_page"] == "qr_keychain":
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

    st.sidebar.subheader("🏷️ Bottom Label Text")
    qr_label_input = st.sidebar.text_input("Label Below QR (e.g., FACEBOOK, LINE, PAY):", value="FACEBOOK")

    st.sidebar.subheader("⭕ Hanging Ring Style")
    ring_type_option = st.sidebar.selectbox("Select Ring Style:", ["Corner Hole", "Thick Ring", "No Ring"])

    qr_size_input = st.sidebar.number_input("QR Width (mm):", value=40)
    qr_base_thick = st.sidebar.number_input("Base Thickness (mm):", value=3.0)
    qr_pixel_thick = st.sidebar.number_input("QR Pixel Raised Thickness (mm):", value=1.5)
    
    st.sidebar.subheader("📐 Ring Dimensions")
    hole_dia_input = st.sidebar.number_input("Hole Diameter (mm):", value=5.0, step=0.5)

    openscad_exe = get_openscad_path()
    temp_dir = tempfile.gettempdir()

    scad_base_code, scad_pixel_code = generate_qr_scad_split(
        qr_data=qr_final_text,
        label_text=qr_label_input,
        qr_size=qr_size_input,
        base_thick=qr_base_thick,
        qr_thick=qr_pixel_thick,
        hole_dia=hole_dia_input,
        ring_type=ring_type_option
    )

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
            subprocess.run([openscad_exe, "-o", stl_qr_base_p, scad_qr_base_p], check=True)
            subprocess.run([openscad_exe, "-o", stl_qr_pixel_p, scad_qr_pixel_p], check=True)

            m_qr_base = pv.read(stl_qr_base_p)
            m_qr_pixel = pv.read(stl_qr_pixel_p)

            obj_qr_base_p = os.path.join(temp_dir, "qr_base.obj")
            obj_qr_pixel_p = os.path.join(temp_dir, "qr_pixel.obj")

            m_qr_base.save(obj_qr_base_p)
            m_qr_pixel.save(obj_qr_pixel_p)

            with open(obj_qr_base_p, "r", encoding="utf-8") as f:
                obj_qr_base_data = f.read().replace("\n", "\\n")

            with open(obj_qr_pixel_p, "r", encoding="utf-8") as f:
                obj_qr_pixel_data = f.read().replace("\n", "\\n")

            three_qr_html = build_threejs_viewer(obj_qr_base_data, obj_qr_pixel_data, "#FFFFFF", "#000000")
            components.html(three_qr_html, height=520, scrolling=False)

            combined_qr = m_qr_base.merge(m_qr_pixel)
            combined_qr_stl_path = os.path.join(temp_dir, "3D_QRCode_Keychain.stl")
            combined_qr.save(combined_qr_stl_path)

            with open(combined_qr_stl_path, "rb") as file:
                st.download_button(
                    label="💾 Save & Download QR Code .STL",
                    data=file,
                    file_name=f"3D_QRCode_{qr_label_input.strip() if qr_label_input.strip() else 'Keychain'}.stl",
                    mime="application/octet-stream",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Render Error: {e}")

elif st.session_state["current_page"] == "monogram_sign":
    st.title("📌 3D Monogram Initial Name Sign Studio")
    st.subheader("Create luxury recessed initial signs with removable front name inserts")

    st.sidebar.subheader("👀 3D Preview Mode")
    mode_option = st.sidebar.radio(
        "Select Display Mode:",
        ["🧩 Combined Assembly View", "✂️ Separate Parts View"]
    )
    view_mode_key = "combined" if "Combined" in mode_option else "separate"

    st.sidebar.subheader("🔤 Back Big Letters")
    mono_big_char = st.sidebar.text_input("Main Initial (Max 5 chars):", value="PEACH")
    if len(mono_big_char) > 5:
        mono_big_char = mono_big_char[:5]

    st.sidebar.subheader("✍️ Front Insert Name")
    mono_name = st.sidebar.text_input("Front Insert Text:", value="Studio 3D")

    font_mono_option = st.sidebar.selectbox(
        "Front Text Font:",
        [
            "Kanit (Modern Bold)",
            "Prompt (Elegant Clean)",
            "Sarabun (Standard Serif)",
            "Pacifico (Cursive Cute)",
            "Dancing Script (Fluid Cursive)",
            "Satisfy (Classic Handwriting)",
            "Noto Sans JP (Japanese)",
            "Noto Sans KR (Korean)",
            "Noto Sans SC (Chinese)",
        ]
    )
    mono_font_dict = {
        "Kanit (Modern Bold)": "Kanit:style=Bold",
        "Prompt (Elegant Clean)": "Prompt:style=Bold",
        "Sarabun (Standard Serif)": "Sarabun:style=Bold",
        "Pacifico (Cursive Cute)": "Pacifico:style=Regular",
        "Dancing Script (Fluid Cursive)": "Dancing Script:style=Bold",
        "Satisfy (Classic Handwriting)": "Satisfy:style=Regular",
        "Noto Sans JP (Japanese)": "Noto Sans JP:style=Bold",
        "Noto Sans KR (Korean)": "Noto Sans KR:style=Bold",
        "Noto Sans SC (Chinese)": "Noto Sans SC:style=Bold",
    }
    mono_name_font = mono_font_dict[font_mono_option]

    st.sidebar.subheader("↔️ Front Text Spacing")
    mono_name_spacing = st.sidebar.slider("Character Spacing:", min_value=0.5, max_value=2.0, value=0.85, step=0.05)

    st.sidebar.subheader("↕️ Front Text Vertical Position")
    mono_offset_y = st.sidebar.slider("Vertical Offset (mm):", min_value=-50.0, max_value=50.0, value=0.0, step=1.0)

    st.sidebar.subheader("📏 Dimensions")
    mono_big_size = st.sidebar.number_input("Main Initial Height (mm):", value=100)
    mono_big_thick = st.sidebar.number_input("Main Initial Thickness (mm):", value=15)
    mono_name_thick = st.sidebar.number_input("Front Insert Thickness (mm):", value=8)
    mono_ratio = st.sidebar.slider("Name-to-Initial Size Ratio:", min_value=0.10, max_value=0.60, value=0.35, step=0.01)

    st.sidebar.subheader("📐 Recess & Layout")
    mono_recess = st.sidebar.number_input("Recess Depth (mm):", value=3)
    mono_tolerance = st.sidebar.number_input("Fit Tolerance (mm):", value=0.2, step=0.05)
    mono_spacing = st.sidebar.number_input("Separate Part Spacing (mm):", value=120)

    FIX_BG_COLOR = "#2A2A2A"
    FIX_BASE_COLOR = "#A0522D"
    FIX_NAME_COLOR = "#00BFFF"

    openscad_exe = get_openscad_path()
    temp_dir = tempfile.gettempdir()

    scad_m_base, scad_m_name = generate_monogram_scad_split(
        big_letter=mono_big_char if mono_big_char else "N",
        big_font="Montserrat:style=Bold",
        name_text=mono_name,
        name_font=mono_name_font,
        big_size=mono_big_size,
        big_thick=mono_big_thick,
        name_thick=mono_name_thick,
        ratio=mono_ratio,
        recess_depth=mono_recess,
        tolerance=mono_tolerance,
        spacing=mono_spacing,
        name_char_spacing=mono_name_spacing,
        offset_y=mono_offset_y,
        view_mode=view_mode_key
    )

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
            subprocess.run([openscad_exe, "-o", stl_mb_p, scad_mb_p], check=True)
            subprocess.run([openscad_exe, "-o", stl_mn_p, scad_mn_p], check=True)

            m_mb = pv.read(stl_mb_p)
            m_mn = pv.read(stl_mn_p)

            obj_mb_p = os.path.join(temp_dir, "mono_base.obj")
            obj_mn_p = os.path.join(temp_dir, "mono_name.obj")

            m_mb.save(obj_mb_p)
            m_mn.save(obj_mn_p)

            with open(obj_mb_p, "r", encoding="utf-8") as f:
                obj_mb_data = f.read().replace("\n", "\\n")

            with open(obj_mn_p, "r", encoding="utf-8") as f:
                obj_mn_data = f.read().replace("\n", "\\n")

            three_mono_html = build_threejs_viewer(obj_mb_data, obj_mn_data, FIX_BASE_COLOR, FIX_NAME_COLOR, bg_color=FIX_BG_COLOR)
            components.html(three_mono_html, height=520, scrolling=False)

            combined_mono = m_mb.merge(m_mn)
            combined_mono_stl_path = os.path.join(temp_dir, "Monogram_Name_Sign.stl")
            combined_mono.save(combined_mono_stl_path)

            with open(combined_mono_stl_path, "rb") as file:
                st.download_button(
                    label="💾 Save & Download Monogram .STL",
                    data=file,
                    file_name=f"Monogram_{mono_big_char}_{mono_name}.stl",
                    mime="application/octet-stream",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Render Error: {e}")

elif st.session_state["current_page"] == "led_lightbox":
    st.title("💡 3D LED Lightbox Studio Pro")
    st.subheader("Create hollow 3D text lightboxes with removable face covers")

    st.sidebar.subheader("📝 Lightbox Settings")
    lb_text = st.sidebar.text_input("Lightbox Text:", value="MKF")
    
    font_lb_option = st.sidebar.selectbox(
        "Lightbox Font:",
        [
            "Montserrat (Wide Bold)",
            "Kanit (Modern Bold)",
            "Prompt (Elegant Clean)",
            "Arial Bold",
        ]
    )
    lb_font_dict = {
        "Montserrat (Wide Bold)": "Montserrat:style=Bold",
        "Kanit (Modern Bold)": "Kanit:style=Bold",
        "Prompt (Elegant Clean)": "Prompt:style=Bold",
        "Arial Bold": "Arial:style=Bold",
    }
    lb_font_name = lb_font_dict[font_lb_option]

    col_l1, col_l2 = st.sidebar.columns(2)
    lb_letter_size = col_l1.number_input("Letter Height (mm):", value=60)
    lb_letter_spacing = col_l2.number_input("Letter Spacing (mm):", value=75)

    lb_box_depth = st.sidebar.number_input("Box Depth (mm):", value=25)
    lb_wall_thick = st.sidebar.number_input("Wall Thickness (mm):", value=2.0)

    st.sidebar.subheader("🔒 Translucent Cover Settings")
    lb_cover_face_thick = st.sidebar.number_input("Cover Face Thickness (mm):", value=1.2)
    lb_lip_height = st.sidebar.number_input("How to use Lip Height (mm):", value=3.5)
    lb_tolerance = st.sidebar.number_input("Fit Tolerance (mm):", value=0.4, step=0.05)
    lb_cover_offset_y = st.sidebar.number_input("Back Cover Offset Y (mm):", value=100)

    FIX_BG_COLOR = "#2A2A2A"
    FIX_BOX_COLOR = "#111111"
    FIX_COVER_COLOR = "#FFFFFF"

    openscad_exe = get_openscad_path()
    temp_dir = tempfile.gettempdir()

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

    if scad_box_code and scad_cover_code:
        scad_lb_box_p = os.path.join(temp_dir, "lb_box.scv")
        stl_lb_box_p = os.path.join(temp_dir, "lb_box.stl")
        with open(scad_lb_box_p, "w", encoding="utf-8") as f:
            f.write(scad_box_code)

        scad_lb_cover_p = os.path.join(temp_dir, "lb_cover.scad")
        stl_lb_cover_p = os.path.join(temp_dir, "lb_cover.stl")
        with open(scad_lb_cover_p, "w", encoding="utf-8") as f:
            f.write(scad_cover_code)

        try:
            subprocess.run([openscad_exe, "-o", stl_lb_box_p, scad_lb_box_p], check=True)
            subprocess.run([openscad_exe, "-o", stl_lb_cover_p, scad_lb_cover_p], check=True)

            m_lb_box = pv.read(stl_lb_box_p)
            m_lb_cover = pv.read(stl_lb_cover_p)

            obj_lb_box_p = os.path.join(temp_dir, "lb_box.obj")
            obj_lb_cover_p = os.path.join(temp_dir, "lb_cover.py")

            m_lb_box.save(obj_lb_box_p)
            m_lb_cover.save(obj_lb_cover_p)

            with open(obj_lb_box_p, "r", encoding="utf-8") as f:
                obj_lb_box_data = f.read().replace("\n", "\\n")

            with open(obj_lb_cover_p, "r", encoding="utf-8") as f:
                obj_lb_cover_data = f.read().replace("\n", "\\n")

            three_lb_html = build_threejs_viewer(obj_lb_box_data, obj_lb_cover_data, FIX_BOX_COLOR, FIX_COVER_COLOR, bg_color=FIX_BG_COLOR)
            components.html(three_lb_html, height=520, scrolling=False)

            combined_lb = m_lb_box.merge(m_lb_cover)
            combined_lb_stl_path = os.path.join(temp_dir, "LED_Lightbox.stl")
            combined_lb.save(combined_lb_stl_path)

            with open(combined_lb_stl_path, "rb") as file:
                st.download_button(
                    label="💾 Save & Download LED Lightbox .STL",
                    data=file,
                    file_name=f"LED_Lightbox_{lb_text}.stl",
                    mime="application/octet-stream",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Render Error: {e}")
