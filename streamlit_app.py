"""
streamlit_app.py
Week 5: a minimal, real UI wired directly to the actual backend --
uploads files, runs the real onboarding pipeline, queries the real
assistant, and runs the real eval checks. Nothing here is mocked.

Run:
    streamlit run streamlit_app.py
"""

import os
import shutil
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from onboard import onboard_client
from ingestion.embedder import load_index
from ingestion.assistant import answer_question
from ingestion.llm_client import LLMClient
from eval.deteval_checks import run_checks

st.set_page_config(page_title="Client Onboarding Pipeline", layout="wide")

SAMPLES_DIR = "samples"
UPLOAD_DIR = "uploaded_clients"

if "llm_client" not in st.session_state:
    st.session_state.llm_client = LLMClient()


def list_existing_clients():
    clients = []
    if os.path.isdir("output"):
        for name in os.listdir("output"):
            full = os.path.join("output", name)
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, "index.faiss")):
                clients.append(name)
    return sorted(clients)


st.title("Client Onboarding Pipeline")
st.caption("Point it at a client's raw data. It figures out the rest.")

tab_build, tab_ask, tab_eval = st.tabs(["Build a client", "Ask", "Eval report"])

# ---------------------------------------------------------------- Build tab
with tab_build:
    st.subheader("Onboard a new client")

    col1, col2 = st.columns(2)
    with col1:
        client_id = st.text_input("Client folder name", value="new_client")
        uploaded_files = st.file_uploader(
            "Upload the client's raw files (CSV, XLSX, PDF, TXT, MD)",
            accept_multiple_files=True,
        )

        if st.button("Build client", type="primary", disabled=not uploaded_files):
            client_folder = os.path.join(UPLOAD_DIR, client_id)
            os.makedirs(client_folder, exist_ok=True)
            for uf in uploaded_files:
                with open(os.path.join(client_folder, uf.name), "wb") as f:
                    f.write(uf.getbuffer())

            progress_box = st.empty()
            log_lines = []

            def on_progress(msg):
                log_lines.append(msg)
                progress_box.code("\n".join(log_lines))

            with st.spinner("Running pipeline..."):
                summary = onboard_client(client_folder, progress_callback=on_progress)

            st.success(f"Built '{summary['customer_id']}' — {summary['chunk_count']} chunks from {summary['file_count']} file(s)")
            if summary["flagged_for_cleaning"]:
                st.warning(f"Flagged for cleaning: {', '.join(summary['flagged_for_cleaning'])}")

            st.subheader("Auto-config decisions")
            for cfg in summary["configs"]:
                st.markdown(f"**{cfg['filename']}** — {cfg['reason']}")

    with col2:
        st.subheader("Or try the sample clients")
        for sample in ["customer_a", "customer_b"]:
            sample_path = os.path.join(SAMPLES_DIR, sample)
            if os.path.isdir(sample_path):
                if st.button(f"Build {sample}", key=f"build_{sample}"):
                    progress_box = st.empty()
                    log_lines = []

                    def on_progress(msg, _box=progress_box, _log=log_lines):
                        _log.append(msg)
                        _box.code("\n".join(_log))

                    with st.spinner(f"Running pipeline for {sample}..."):
                        summary = onboard_client(sample_path, progress_callback=on_progress)
                    st.success(f"Built '{summary['customer_id']}' — {summary['chunk_count']} chunks")

    st.divider()
    existing = list_existing_clients()
    st.caption(f"Clients built so far: {', '.join(existing) if existing else 'none yet'}")

# ------------------------------------------------------------------ Ask tab
with tab_ask:
    existing = list_existing_clients()
    if not existing:
        st.info("Build a client first in the 'Build a client' tab.")
    else:
        selected = st.selectbox("Client", existing)
        question = st.text_input("Ask a question about this client's data")

        if st.button("Ask", disabled=not question):
            index, vectorizer, metadata = load_index(selected)
            result = answer_question(question, index, vectorizer, metadata, llm_client=st.session_state.llm_client)

            st.markdown(f"**Answer** _(via {result['provider']})_")
            st.write(result["answer"])

            if result["citations"]:
                st.caption("Sources:")
                for c in result["citations"]:
                    st.caption(f"— {c['source_file']} | {c['locator']}")

# ----------------------------------------------------------------- Eval tab
with tab_eval:
    existing = list_existing_clients()
    if not existing:
        st.info("Build a client first in the 'Build a client' tab.")
    else:
        selected = st.selectbox("Client to evaluate", existing, key="eval_select")
        test_question = st.text_input("Test question for the eval check", value="")

        if st.button("Run eval check", disabled=not test_question):
            index, vectorizer, metadata = load_index(selected)
            rag_result = answer_question(test_question, index, vectorizer, metadata, llm_client=st.session_state.llm_client)
            eval_result = run_checks(
                question=test_question,
                answer=rag_result["answer"],
                citations=rag_result["citations"],
                context_chunks=rag_result["context_chunks"],
                metadata=metadata,
            )

            status = "PASS" if eval_result["overall_pass"] else "FAIL"
            (st.success if eval_result["overall_pass"] else st.error)(f"Overall: {status}")

            for c in eval_result["checks"]:
                icon = "✅" if c["passed"] else "❌"
                st.write(f"{icon} **{c['check']}** — {c['detail']}")

        st.caption("Run `python run_eval_report.py` from the terminal for the full 10-question batch report per client.")
