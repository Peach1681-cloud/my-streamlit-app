import streamlit as st
import os
import json
from ui_theme import apply_theme
from analytics import load_analytics

st.set_page_config(page_title="Dashboard & Overview", page_icon="📊", layout="wide")
apply_theme()

stats = load_analytics()

st.markdown("""
<div class="studio-hero">
  <div class="eyebrow">Your creative 3D workspace</div>
  <h1>Make something wonderful ✨</h1>
  <p>ออกแบบ ปรับแต่ง และส่งออกโมเดล 3D ของคุณได้ง่าย ๆ ในสตูดิโอเดียว</p>
  <div class="hero-pills">
    <span class="hero-pill">🌏 รองรับหลายภาษา</span>
    <span class="hero-pill">🎨 ปรับแต่งได้อิสระ</span>
    <span class="hero-pill">📦 พร้อมดาวน์โหลด</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-kicker">Studio at a glance</div>', unsafe_allow_html=True)
st.markdown("## ภาพรวมการใช้งาน 📈")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="👥 Total Logins", value=f"{stats.get('total_logins', 0)} times")

with col2:
    st.metric(label="📥 Total Exports / Downloads", value=f"{stats.get('total_exports', 0)} times")

with col3:
    st.metric(label="🛠️ Total Projects", value="8 Projects")

st.markdown("## เลือกสิ่งที่อยากสร้าง 🚀")
cards = [
    ("🏷️", "Text Keychain", "พวงกุญแจข้อความหลายภาษา"),
    ("📱", "QR Keychain", "QR Code สำหรับลิงก์และการชำระเงิน"),
    ("💝", "Monogram Sign", "ป้ายชื่อและตัวอักษรเฉพาะตัว"),
    ("💡", "LED Lightbox", "กล่องไฟตัวอักษรพร้อมฝาครอบ"),
    ("📿", "Chain Bracelet", "สร้อยข้อมือตัวอักษรหลากรูปทรง"),
    ("🎁", "Gift Box", "กล่องของขวัญออกแบบตามใจ"),
    ("🏺", "Threaded Jar", "กระปุกฝาเกลียวพร้อมข้อความ"),
    ("✨", "Ready to create?", "เลือกเครื่องมือจากเมนูด้านซ้ายเพื่อเริ่มต้น"),
]
for row_start in range(0, len(cards), 4):
    cols = st.columns(4)
    for col, (icon, title, description) in zip(cols, cards[row_start:row_start + 4]):
        with col:
            st.markdown(
                f'<div class="feature-card"><div class="feature-icon">{icon}</div>'
                f'<h3>{title}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )
