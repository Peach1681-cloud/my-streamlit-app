import streamlit as st
from ui_theme import apply_theme
from analytics import record_login

# ป้องกันปัญหาเรื่อง Import ตัวแปรพาสส์โค้ดจาก config ถ้าหาไม่เจอให้ใช้ค่าสำรองทันที
try:
    from config import PASSCODE_CORRECT
except ImportError:
    PASSCODE_CORRECT = "1681"

st.set_page_config(page_title="Global 3D Creator Studio Pro", page_icon="✨", layout="wide")
apply_theme()

# เพิ่ม CSS กำหนดให้แสดงคำว่า "Menu" ไว้ข้างปุ่มยุบ Sidebar ด้านบนซ้าย
st.markdown("""
    <style>
    [data-testid="collapsedControl"]::after {
        content: " Menu";
        font-size: 14px;
        font-weight: bold;
        color: #31333F;
        margin-left: 5px;
        vertical-align: middle;
    }
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_passcode():
    st.markdown("""
        <div class="login-wrap">
          <div class="login-icon">✨</div>
          <div class="section-kicker">Creative tools for makers</div>
          <h1>Global 3D Creator Studio</h1>
          <p>เปลี่ยนไอเดียของคุณให้กลายเป็นโมเดล 3D พร้อมพิมพ์</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info(
        "🎁 **Free Trial Notice:** This system is temporarily open for free evaluation before service closure.\n\n"
        "🔑 **Access Passcode:** `1681`\n\n"
        "🌐 **Supported Languages for 3D Text Production:** Our 3D generators fully support English, Thai, Chinese, Japanese, Korean, Arabic, and Hindi.\n\n"
        "💼 **Custom 3D Software Development:** If you are interested in custom 3D software development, special model designs, or commercial use licensing with a unique style, please feel free to contact the developer below."
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        passcode_input = st.text_input("Passcode:", type="password", key="pass_input")
        if st.button("Unlock Studio", use_container_width=True):
            if passcode_input == str(PASSCODE_CORRECT):
                st.session_state.authenticated = True
                record_login()
                st.rerun()
            else:
                st.error("❌ Incorrect Passcode. Please try again.")

    st.markdown(
        "<div class='footer-note'>"
        "<h4>💌 Contact Developer / Custom 3D Services</h4>"
        "<p>Interested in developing custom 3D applications or ordering specialized models?<br>"
        "💬 <b>Line ID:</b> peach1681<br>"
        "📱 <b>WhatsApp:</b> +66 93323-9639<br><br>"
        "🌐 Global 3D Creator Studio Pro - All Rights Reserved</p>"
        "</div>", 
        unsafe_allow_html=True
    )

if not st.session_state.authenticated:
    check_passcode()
else:
    dashboard_page = st.Page("pages/1_dashboard.py", title="Dashboard Home", icon="🏠", default=True)
    text_keychain_page = st.Page("pages/2_text_keychain.py", title="Text Keychain", icon="🏷️")
    qr_keychain_page = st.Page("pages/3_qr_keychain.py", title="QR Code Keychain", icon="📱")
    monogram_page = st.Page("pages/4_monogram_sign.py", title="Monogram Name Sign", icon="📌")
    lightbox_page = st.Page("pages/5_led_lightbox.py", title="LED Lightbox Studio", icon="💡")
    bracelet_page = st.Page("pages/6_chain_bracelet.py", title="Chain Bracelet Studio", icon="📿")
    gift_box_page = st.Page("pages/7_gift_box_packaging.py", title="Bespoke Gift Box", icon="🎁")
    threaded_jar_page = st.Page("pages/8_threaded_jar.py", title="Threaded Jar & Lid", icon="🏺")

    pg = st.navigation({
        "Studio Menu": [
            dashboard_page, 
            text_keychain_page, 
            qr_keychain_page, 
            monogram_page, 
            lightbox_page,
            bracelet_page,
            gift_box_page,
            threaded_jar_page
        ]
    })
    
    pg.run()
