"""Streamlit UI. Run with: streamlit run app.py"""

import os
from pathlib import Path
import tempfile

import streamlit as st

from agents.analysis import analyze_subject, get_analysis
from agents.diagnostics import latest_trace, model_status, recent_calls
from agents.quiz_agent import generate_questions_for_topic
from embeddings.embed_store import get_collection
from ingestion.pipeline import ingest_file
from ingestion.source_store import get_pages


def subjects() -> list[str]:
    metadata = get_collection().get(include=["metadatas"])["metadatas"]
    return sorted({m["subject"] for m in metadata if m.get("subject")})


def _upload_one(upload, source_type: str, subject: str, year: int | None) -> int:
    # Browser-supplied names may contain path separators. Keep only a basename.
    filename = Path(upload.name.replace("\\", "/")).name
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / filename
        path.write_bytes(upload.getvalue())
        return ingest_file(path, source_type, subject=subject, year=year)


def _study(subject: str) -> None:
    st.subheader("Analyze this course")
    pages = get_pages(subject)
    st.caption(f"{len(pages)} extracted source pages or transcript segments available for full-context analysis.")
    with st.expander("Inspect extracted text before analysis"):
        if pages:
            options = [f"{p['source_type']} · {p['filename']} · page/segment {p['page']}" for p in pages]
            selected = st.selectbox("Source page", range(len(pages)), format_func=lambda i: options[i])
            st.text_area("Extracted text", pages[selected]["text"], height=250)
        else:
            st.write("No full-page text saved yet. Index files using Add material.")
    if st.button("Analyze teaching material and past papers", type="primary"):
        try:
            with st.spinner("Extracting topics and complete exam questions with the configured LLM. This can take several minutes locally."):
                analyze_subject(subject)
            st.success("Analysis complete")
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
    analysis = get_analysis(subject)
    if not analysis:
        st.info("Run analysis after uploading teaching material and dated past papers. Earlier uploads need to be indexed again to save their full pages.")
        return
    st.caption(f"Analysis saved {analysis['generated_at']}. Re-uploading a source invalidates it.")
    min_years = st.slider("Show topics seen in at least this many exam years", 0, 5, 1)
    topics = [t for t in analysis["topics"] if t["num_years"] >= min_years]
    if not topics:
        st.info("No topics meet this threshold. Lower it to inspect teaching topics without exam matches.")
        return
    st.dataframe([
        {"Topic": t["name"], "Teaching context": t["summary"],
         "Exam years": ", ".join(map(str, t["years"])) or "—",
         "Teaching sources": ", ".join(f"{s['filename']} p.{s['page']}" for s in t["sources"][:3])}
        for t in topics
    ], hide_index=True, width="stretch")
    topic_name = st.selectbox("Explore a topic", [t["name"] for t in topics])
    topic = next(t for t in topics if t["name"] == topic_name)
    questions = [q for q in analysis["questions"] if q.get("topic") == topic_name]
    groups = [g for g in analysis["recurring_groups"] if g["topic"] == topic_name
              and len(g["years"]) >= max(2, min_years)]
    context_tab, questions_tab, recurring_tab, quiz_tab = st.tabs([
        "Teaching context", "Past-paper questions", "Recurring questions", "Practice quiz"
    ])
    with context_tab:
        st.write(topic["summary"])
        st.caption("Pages supplied when this topic was extracted:")
        for source in topic["sources"]:
            with st.expander(f"{source['filename']} · page/slide/segment {source['page']}"):
                matching = [p for p in pages if p["filename"] == source["filename"]
                            and p["page"] == source["page"]]
                if matching:
                    st.write(matching[0]["text"])
    with questions_tab:
        if not questions:
            st.write("No extracted past-paper questions mapped to this topic.")
        for q in questions:
            with st.expander(f"{q['year']} · {q['filename']} · page {q['page']}"):
                st.write(q["question"])
    with recurring_tab:
        st.caption("The LLM groups questions that ask substantially the same task across different years. Check the source pages before treating a group as a verified repeat.")
        if not groups:
            st.write("No recurring question groups found for this topic.")
        for i, group in enumerate(groups, 1):
            with st.expander(f"Group {i} · {', '.join(map(str, group['years']))}"):
                st.write(group["reason"])
                for q in group["questions"]:
                    st.markdown(f"**{q['year']} · {q['filename']} · page {q['page']}**")
                    st.write(q["question"])
    with quiz_tab:
        kind = st.selectbox("Question type", ["mcq", "2_mark", "3_mark", "5_mark"])
        count = st.slider("Questions", 1, 5, 2)
        if st.button("Generate practice questions"):
            try:
                with st.spinner("Generating from retrieved teaching passages..."):
                    st.session_state["quiz"] = generate_questions_for_topic(topic_name, count, kind, subject)
                st.session_state["quiz_for"] = (subject, topic_name, kind)
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
        visible = st.session_state.get("quiz", []) if st.session_state.get("quiz_for") == (subject, topic_name, kind) else []
        if st.session_state.get("quiz_for") == (subject, topic_name, kind) and not visible:
            st.info("The model did not return valid grounded questions for this topic.")
        for i, item in enumerate(visible, 1):
            st.markdown(f"**{i}. {item['question']}**")
            for option in item["options"]:
                st.write(f"• {option}")
            with st.expander("Answer and retrieved sources"):
                st.write(item["correct_answer"])
                st.write(item["explanation"])
                st.caption("Retrieved passages: " + "; ".join(item["sources"]))


def _index_submitted_files() -> None:
    """Process form values before Streamlit draws the next page."""
    subject = st.session_state.get("ingest_subject", "").strip()
    if not subject:
        st.session_state["ingest_messages"] = [("error", "Enter a subject before indexing")]
        return
    year = st.session_state.get("ingest_year", 0)
    selected = ([(f, "lecture_note", None) for f in (st.session_state.get("ingest_notes") or [])]
                + [(f, "textbook", None) for f in (st.session_state.get("ingest_textbooks") or [])]
                + [(f, "lecture_video", None) for f in (st.session_state.get("ingest_videos") or [])]
                + [(f, "past_qp", int(year) if year else None)
                   for f in (st.session_state.get("ingest_papers") or [])])
    if not selected:
        st.session_state["ingest_messages"] = [("error", "Choose at least one file")]
        return
    messages = []
    for upload, source_type, file_year in selected:
        try:
            count = _upload_one(upload, source_type, subject, file_year)
            messages.append(("success", f"{upload.name}: indexed {count} chunks and saved full extracted text"))
        except Exception as exc:
            messages.append(("error", f"{upload.name}: {exc}"))
    st.session_state["ingest_messages"] = messages
    if any(level == "success" for level, _ in messages):
        st.session_state["subject_picker"] = subject


def _uploads(current_subject: str | None) -> None:
    st.subheader("Add course material")
    st.write("Use one subject name for material that belongs to the same course. You can add more files later.")
    if "ingest_subject" not in st.session_state:
        st.session_state["ingest_subject"] = current_subject or ""
    with st.form("ingestion"):
        st.text_input("Subject/course", key="ingest_subject")
        st.file_uploader("Lecture notes and slides", type=["pdf", "pptx", "ppt", "docx", "txt", "md"],
                         accept_multiple_files=True, key="ingest_notes")
        st.file_uploader("Textbooks and reference material", type=["pdf", "pptx", "ppt", "docx", "txt", "md"],
                         accept_multiple_files=True, key="ingest_textbooks")
        st.file_uploader("Lecture video or audio", type=["mp4", "mp3", "wav", "m4a", "webm"],
                         accept_multiple_files=True, key="ingest_videos")
        st.file_uploader("Past-year question papers", type=["pdf"], accept_multiple_files=True,
                         key="ingest_papers")
        st.number_input("Fallback exam year for papers without a year in the filename (0 = none)",
                        min_value=0, max_value=2100, value=0, key="ingest_year")
        st.form_submit_button("Index selected files", type="primary", on_click=_index_submitted_files)


def _diagnostics() -> None:
    st.subheader("Model diagnostics")
    status = model_status()
    st.json(status)
    if status.get("provider") == "Ollama":
        if not status.get("reachable"):
            st.error("Ollama is not responding. Start the Ollama app or run `ollama serve` in a terminal, then check this panel again.")
        else:
            installed = status.get("installed_models", [])
            for required in (status["chat_model"], status["embed_model"]):
                if required not in installed and f"{required}:latest" not in installed:
                    st.warning(f"Model {required} is missing. Run `ollama pull {required}`.")
        st.code('Get-Content "$env:LOCALAPPDATA\\Ollama\\server.log" -Tail 100 -Wait', language="powershell")
        st.caption("That command shows Ollama server events on Windows. The app trace below records request sizes, duration, and failures; it does not expose hidden model reasoning.")
    st.text_area("Recent app LLM calls", recent_calls(), height=250)
    if os.getenv("MODE", "local").lower() == "local":
        trace = latest_trace()
        if trace:
            with st.expander("Latest prompt and response (local trace)"):
                st.caption(f"Model: {trace['model']}")
                st.text_area("Prompt", trace["prompt"], height=250)
                st.text_area("Response", trace["response"], height=250)
        else:
            st.caption("To save full local prompts and responses, set LOG_LLM_CONTENT=1 in .env and restart the app. The trace stays in db/llm_trace.jsonl.")


def main() -> None:
    st.set_page_config(page_title="Exam Prep Synthesizer", layout="wide")
    demo = os.getenv("MODE", "local").lower() == "demo"
    if demo:
        from demo_seed import seed_demo
        seed_demo()
    st.title("Exam Prep Synthesizer")
    st.caption("Analyze complete course pages, inspect past-paper questions, and practice from grounded sources.")
    for level, message in st.session_state.pop("ingest_messages", []):
        (st.success if level == "success" else st.error)(message)
    if demo:
        st.info("Public preview with synthetic DBMS material. Uploads are disabled.")
    existing = subjects()
    subject = st.selectbox("Subject", existing, index=0 if existing else None, key="subject_picker")
    tabs = st.tabs(["Study", "Add material", "Diagnostics"] if not demo else ["Study", "Diagnostics"])
    with tabs[0]:
        if subject:
            _study(subject)
        else:
            st.info("Add teaching material and dated past papers to begin.")
    if demo:
        with tabs[1]:
            _diagnostics()
    else:
        with tabs[1]:
            _uploads(subject)
        with tabs[2]:
            _diagnostics()


if __name__ == "__main__":
    main()
