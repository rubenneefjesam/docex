elif choice == "Coge":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>🔍 Coge</h1>", unsafe_allow_html=True)
    import traceback, sys as _sys
    from pathlib import Path as _Path

    try:
        # Laat zien of import echt gelukt is + waar het bestand staat
        st.write("🔧 Import check:", coge)
        st.write("📄 coge-module file:", getattr(coge, "__file__", "n/a"))

        # Bestaat het bestand op schijf?
        coge_path = _Path(ROOT) / "tools" / "coge_tool" / "coge.py"
        st.write("🗂️ coge.py exists?:", coge_path.exists(), str(coge_path))

        st.write("✅ calling coge.app() …")
        coge.app()
        st.success("coge.app() executed")
    except Exception as e:
        st.error(f"❌ Fout in coge.app(): {e}")
        st.code("".join(traceback.format_exception(*_sys.exc_info())))
