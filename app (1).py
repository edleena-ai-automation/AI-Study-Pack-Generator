import json

import streamlit as st

from models import StudentProfile
from workflow import run_workflow

st.set_page_config(
    page_title="StudyPack AI",
    page_icon="📚",
    layout="wide",
)

st.title("📚 StudyPack AI")
st.caption("Personalized study packs generated through a multi-stage AI workflow")

st.markdown(
    """
This app uses five AI workflow stages:
**Planning → Content Generation → Assessment → Review → Refinement**
"""
)

with st.sidebar:
    st.header("Student Profile")

    subject = st.text_input("Subject", value="Chemistry")
    topic = st.text_input("Topic", value="Chemical Equilibrium")
    level = st.selectbox(
        "Academic level",
        ["Beginner", "Intermediate", "Advanced"],
    )
    goals = st.text_area(
        "Learning goals",
        value="Understand the topic clearly and prepare for an exam.",
    )
    study_time = st.slider(
        "Available study time (minutes)",
        min_value=15,
        max_value=240,
        value=60,
        step=15,
    )
    learning_style = st.selectbox(
        "Learning style",
        ["Mixed", "Visual", "Conceptual", "Practice-focused"],
    )
    language = st.selectbox(
        "Content language",
        ["English", "Urdu", "Urdu-English"],
    )

    generate = st.button(
        "Generate Study Pack",
        type="primary",
        use_container_width=True,
    )


if generate:
    student = StudentProfile(
        subject=subject,
        topic=topic,
        level=level,
        goals=goals,
        study_time=study_time,
        learning_style=learning_style,
        language=language,
    )

    stage_box = st.empty()

    def update_progress(stage: str, message: str) -> None:
        stage_box.info(f"**{stage}** — {message}")

    with st.spinner("Generating your personalized study pack..."):
        state = run_workflow(student, progress_callback=update_progress)

    if state.errors:
        stage_box.empty()
        st.error("Study pack generation failed.")
        with st.expander("Technical details"):
            st.code(state.errors[-1])
    else:
        stage_box.success("Study pack generated successfully.")
        st.session_state["study_pack"] = state.final_pack


if "study_pack" in st.session_state:
    pack = st.session_state["study_pack"]

    st.divider()
    st.header(pack["plan"]["title"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Study Time", f"{pack['student']['study_time']} min")
    col2.metric("Review Score", f"{pack['review']['score']:.0f}/100")
    col3.metric("Refinements", pack["refinement_count"])

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Study Plan", "Study Notes", "Examples", "Practice Quiz", "Quality Review"]
    )

    with tab1:
        st.subheader("Learning Objectives")
        for objective in pack["plan"]["objectives"]:
            st.markdown(f"- {objective}")

        st.subheader("Key Concepts")
        for concept in pack["plan"]["concepts"]:
            st.markdown(f"- {concept}")

        st.subheader("Study Schedule")
        for step in pack["plan"]["schedule"]:
            st.markdown(f"- {step}")

        st.info(f"Recommended difficulty: {pack['plan']['difficulty']}")

    with tab2:
        st.subheader("Summary")
        st.write(pack["content"]["summary"])

        st.subheader("Detailed Notes")
        st.markdown(pack["content"]["detailed_notes"])

        st.subheader("Important Concepts")
        for concept in pack["content"]["key_concepts"]:
            st.markdown(f"- {concept}")

        st.subheader("Common Misconceptions")
        for item in pack["content"]["misconceptions"]:
            st.warning(item)

    with tab3:
        for number, example in enumerate(pack["content"]["examples"], start=1):
            st.markdown(f"### Example {number}")
            st.write(example)

    with tab4:
        for number, question in enumerate(pack["assessment"]["questions"], start=1):
            st.markdown(f"### {number}. {question['question']}")
            st.caption(f"Difficulty: {question['difficulty'].title()}")

            if question.get("options"):
                for option in question["options"]:
                    st.markdown(f"- {option}")

            with st.expander("Show answer and explanation"):
                st.success(f"Answer: {question['answer']}")
                st.write(question["explanation"])

    with tab5:
        st.metric("Final Review Score", f"{pack['review']['score']:.0f}/100")
        st.write("**Passed:**", "Yes" if pack["review"]["passed"] else "No")

        if pack["review"]["issues"]:
            st.subheader("Issues Identified")
            for issue in pack["review"]["issues"]:
                st.markdown(f"- {issue}")

        if pack["review"]["suggestions"]:
            st.subheader("Reviewer Suggestions")
            for suggestion in pack["review"]["suggestions"]:
                st.markdown(f"- {suggestion}")

    st.divider()
    st.download_button(
        "Download Study Pack as JSON",
        data=json.dumps(pack, indent=2, ensure_ascii=False),
        file_name="study_pack.json",
        mime="application/json",
        use_container_width=True,
    )
