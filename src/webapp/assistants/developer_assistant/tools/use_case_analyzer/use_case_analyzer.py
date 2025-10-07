# use_case_analyzer.py
import os
import streamlit as st

# UI only; does NOT contain templates or prompt config.
# It dynamically imports one of: story, feature, epic, acceptatie_criteria

def load_templates_folder(templates_dir: str):
    # kept for backwards compatibility if you want file-based templates,
    # but not used for prompt/config — modules have their own templates.
    if not os.path.isdir(templates_dir):
        return {}
    templates = {}
    for fn in sorted(os.listdir(templates_dir)):
        path = os.path.join(templates_dir, fn)
        if fn.startswith(".") or not os.path.isfile(path):
            continue
        key = os.path.splitext(fn)[0]
        with open(path, encoding="utf-8") as f:
            templates[key] = f.read()
    return templates

def app():
    st.set_page_config(page_title="Use-case Generator (modulair)", layout="wide")
    st.title("Use-case Generator — generieke IT stories / features / epics")
    st.markdown("Links de input (ongewijzigd zoals gevraagd). Rechts de uiteindelijke output.\n\nKies wat je wilt genereren en klik op *Genereer*.")

    left_col, right_col = st.columns([1, 1.1])

    with left_col:
        choice = st.selectbox("Wat wil je genereren?", ["Story", "Feature", "Epic", "Acceptatie Criteria"])
        desc = st.text_area("Korte omschrijving", height=150, placeholder="Kort & generiek, bv. 'Unit tests voor LLM-verrijking met documenten'")
        gen = st.button("Genereer")

    with right_col:
        st.header("Output")
        output_area = st.empty()
        debug_expander = st.expander("Debug / raw response", expanded=False)
        with debug_expander:
            st.write("Raw LLM-response en eventuele foutmeldingen verschijnen hier (alleen voor debugging).")
            if "last_raw" in st.session_state:
                st.code(st.session_state.get("last_raw", ""), language="text")
            if "last_error" in st.session_state:
                st.error(st.session_state.get("last_error", ""))

    if gen:
        # clear old debug
        st.session_state.pop("last_raw", None)
        st.session_state.pop("last_error", None)

        # map selection to module name
        module_map = {
            "story": "story",
            "feature": "feature",
            "epic": "epic",
            "acceptatie criteria": "acceptatie_criteria",
            "acceptatie_criteria": "acceptatie_criteria",
            "acceptatie": "acceptatie_criteria",
        }
        key = choice.lower()
        module_name = module_map.get(key, None)
        if not module_name:
            st.error("Onbekende keuze.")
            return

        # dynamic import
        try:
            generator_mod = __import__(module_name)
        except Exception as e:
            st.session_state["last_error"] = f"Kan module '{module_name}' importeren: {e}"
            st.error(st.session_state["last_error"])
            return

        # call generate(short_input) — module returns dict with result/raw/error
        try:
            status = st.empty()
            progress = st.progress(0)
            status.info("Voorbereiden...")
            progress.progress(10)

            status.info("Genereren...")
            progress.progress(30)

            result_pkg = generator_mod.generate(desc.strip())

            progress.progress(70)
            result_text = result_pkg.get("result", "") or ""
            output_area.code(result_text, language="markdown")

            # store debug info
            st.session_state["last_raw"] = result_pkg.get("raw", "")
            st.session_state["last_error"] = result_pkg.get("error", "")

            progress.progress(100)
            status.empty()
        except Exception as e:
            st.session_state["last_error"] = str(e)
            st.error(f"Fout bij genereren: {e}")

if __name__ == "__main__":
    app()
