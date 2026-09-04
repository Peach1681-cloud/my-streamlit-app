"""Reusable visual SVG picker for Streamlit pages."""

from pathlib import Path

import streamlit as st

from icon_catalog_v2 import ICON_DIR, get_icon_choices


def _plain_name(label: str) -> str:
    """Remove the decorative prefix while keeping a readable icon name."""
    if label == "None":
        return "None"
    parts = label.split(" ", 1)
    return parts[1] if len(parts) == 2 else label


def visual_icon_picker(label: str, key: str, host=None) -> str:
    """Render a searchable SVG gallery and return the selected catalog label."""
    host = host or st
    choices = get_icon_choices()
    state_key = f"{key}_selected"
    search_key = f"{key}_search"

    if st.session_state.get(state_key) not in choices:
        st.session_state[state_key] = "None"

    selected = st.session_state[state_key]
    button_label = f"{label}: {_plain_name(selected)}"

    with host.popover(button_label, use_container_width=True):
        search = st.text_input(
            "🔎 Search icons / ค้นหาไอคอน",
            key=search_key,
            placeholder="เช่น cat, heart, sport...",
        ).strip().lower()

        filtered = [
            (name, filename)
            for name, filename in choices.items()
            if not search or search in _plain_name(name).lower()
        ]
        st.caption(f"แสดง {len(filtered)} จาก {len(choices) - 1} ไอคอน")

        columns = st.columns(3)
        for index, (name, filename) in enumerate(filtered):
            with columns[index % 3]:
                if filename:
                    icon_path = ICON_DIR / filename
                    if icon_path.is_file():
                        st.image(str(icon_path), width=54)
                else:
                    st.markdown(
                        "<div style='height:54px;display:grid;place-items:center;"
                        "border:1px dashed #b9afd4;border-radius:10px;color:#776d91;'>"
                        "No icon</div>",
                        unsafe_allow_html=True,
                    )

                is_selected = name == selected
                if st.button(
                    ("✓ " if is_selected else "") + _plain_name(name),
                    key=f"{key}_option_{index}_{filename or 'none'}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state[state_key] = name
                    st.rerun()

    selected = st.session_state[state_key]
    filename = choices.get(selected)
    if filename:
        selected_path = Path(ICON_DIR / filename)
        preview_col, name_col = host.columns([1, 4])
        preview_col.image(str(selected_path), width=38)
        name_col.caption(f"เลือกแล้ว: {_plain_name(selected)}")
    else:
        host.caption(f"พบ SVG {len(choices) - 1} แบบ • ยังไม่ได้เลือกไอคอน")

    return selected
