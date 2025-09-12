# tools/coge_tool/coge.py
import streamlit as st
import time

VERSION = "smoke-1"

# render op import (zie je dit niet? -> import-probleem)
st.write(f"🔎 coge.py geladen ({VERSION})")

def app():
    st.write(f"➡️ coge.app() start ({VERSION}) @ {time.strftime('%H:%M:%S')}")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("## 🔍 Coge")
    with col2:
        st.write("Hallo 👋 (smoke test)")