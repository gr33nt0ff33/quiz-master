import streamlit as st
import json
import random
from pathlib import Path

# ----------------- Page config (must be first Streamlit call) -----------------
st.set_page_config(
    page_title="Quiz Master",
    page_icon="🧠",
    layout="centered",
)

# ----------------- Helper functions -----------------
def load_subject_file(path: Path):
    """Load a JSON subject file. Returns list of blocks or [] on error."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Error loading {path.name}: {e}")
        return []

def gather_subjects(base_files):
    """Return dict: subject_name -> list of blocks"""
    subjects = {}
    for p in base_files:
        blocks = load_subject_file(Path(p))
        for block in blocks:
            subj = block.get("subject", "Unknown")
            subjects.setdefault(subj, []).append(block)
    return subjects

def get_topics_and_grades(blocks):
    """From a list of blocks, return sorted unique topics and grades"""
    topics = sorted({b.get("topic", "General") for b in blocks})
    grades = sorted({b.get("grade", None) for b in blocks if "grade" in b})
    return topics, grades

def collect_questions_from_blocks(blocks, selected_topic, selected_grade):
    """Return flattened list of question dicts filtered by topic & grade."""
    out = []
    for b in blocks:
        if (selected_topic in (None, "All") or b.get("topic") == selected_topic) and \
           (selected_grade in (None, "All") or b.get("grade") == selected_grade):
            qs = b.get("questions", [])
            for q in qs:
                if "type" in q and "question" in q and "answer" in q:
                    out.append(q)
    return out

def normalize_answer(ans):
    if ans is None:
        return ""
    return str(ans).strip().lower()

# ----------------- Load subject files -----------------
subject_files = ["math.json", "english.json", "science.json"]
subjects_data = gather_subjects(subject_files)

if not subjects_data:
    st.error("No subject JSON files found or files are empty. Place math.json, english.json, science.json in this folder.")
    st.stop()

# ----------------- Session state init -----------------
if "version" not in st.session_state:
    st.session_state.version = 0
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_subject" not in st.session_state:
    st.session_state.quiz_subject = None
if "quiz_config" not in st.session_state:
    st.session_state.quiz_config = {}

# ----------------- UI: Tabs per subject -----------------
tabs = st.tabs(list(subjects_data.keys()))
for tab, subject in zip(tabs, subjects_data.keys()):
    with tab:
        st.header(f"{subject}")
        blocks = subjects_data[subject]
        topics, grades = get_topics_and_grades(blocks)

        topic_choices = ["All"] + topics if topics else ["All"]
        grade_choices = ["All"] + grades if grades else ["All"]

        col1, col2 = st.columns([2, 1])
        with col1:
            chosen_topic = st.selectbox(f"Select topic ({subject})", topic_choices, key=f"topic_{subject}")
        with col2:
            chosen_grade = st.selectbox(f"Select grade ({subject})", grade_choices, key=f"grade_{subject}")

        start_col, info_col = st.columns([1, 3])
        with start_col:
            if st.button("▶ Start Quiz", key=f"start_{subject}"):
                all_qs = collect_questions_from_blocks(
                    blocks,
                    chosen_topic if chosen_topic != "All" else None,
                    chosen_grade if chosen_grade != "All" else None
                )
                if not all_qs:
                    st.warning("No questions found for that topic/grade. Try 'All' or another topic.")
                else:
                    # 1️⃣ Pick a random sample of up to 10 questions
                    selected = random.sample(all_qs, min(10, len(all_qs)))

                    # 2️⃣ Group by type
                    type_groups = {}
                    for q in selected:
                        q_type = q.get("type", "unknown")
                        type_groups.setdefault(q_type, []).append(q)

                    # 3️⃣ Shuffle within each type
                    for q_type in type_groups:
                        random.shuffle(type_groups[q_type])

                    # 4️⃣ Flatten back to a list, keeping type order
                    grouped_questions = []
                    for q_type in ["multiple_choice", "true_false", "short_answer", "fill_blank", "unknown"]:
                        grouped_questions.extend(type_groups.get(q_type, []))

                    # 5️⃣ Store in session
                    st.session_state.quiz_questions = grouped_questions

                    st.session_state.quiz_subject = subject
                    st.session_state.quiz_config = {"topic": chosen_topic, "grade": chosen_grade}
                    st.session_state.version += 1
                    st.rerun()  # ✅ use st.rerun (replaces experimental_rerun)

        with info_col:
            total_avail = len(
                collect_questions_from_blocks(
                    blocks,
                    chosen_topic if chosen_topic != "All" else None,
                    chosen_grade if chosen_grade != "All" else None,
                )
            )
            st.write(f"Selected topic: **{chosen_topic}** — Grade: **{chosen_grade}**")
            st.write(f"Available questions: **{total_avail}**")
            st.write("Click **Start Quiz** to begin!")

# ----------------- Quiz UI -----------------
if st.session_state.quiz_questions and st.session_state.quiz_subject:
    st.markdown("---")
    st.subheader(
        f"Quiz — {st.session_state.quiz_subject} "
        f"(Topic: {st.session_state.quiz_config.get('topic')}, "
        f"Grade: {st.session_state.quiz_config.get('grade')})"
    )

    questions = st.session_state.quiz_questions
    version = st.session_state.version

    with st.form("quiz_form"):
        user_answers = []
        # Define colors for each question type
        type_colors = {
            "multiple_choice": "#e0f7fa",  # light cyan
            "true_false": "#fff9c4",       # light yellow
            "short_answer": "#e1bee7",     # light purple
            "fill_blank": "#c8e6c9",       # light green
            "unknown": "#f5f5f5",          # light gray
        }

        current_type = None
        for i, q in enumerate(questions):
            q_type = q.get("type", "unknown")

            # -------------------- Type Header --------------------
            if q_type != current_type:
                current_type = q_type
                type_title = q_type.replace("_", " ").title()
                # start a container with background color
                st.markdown("---")  # horizontal line between questions
                st.markdown(f"<div style='background-color: {type_colors.get(q_type, '#f5f5f5')}; padding:10px; border-radius:8px; color: #000000;'>  <!-- dark text color -->"
                            f"<h2 style='margin-bottom:5px'>{type_title} Questions</h2></div>",unsafe_allow_html=True)
                            
            # -------------------- Question Separator --------------------
            st.markdown("---")  # horizontal line between questions

            # -------------------- Question Text --------------------
            st.markdown(f"### Q{i+1}")
            st.markdown(f"**{q.get('question')}**")
            key = f"q{i}_v{version}"

            # -------------------- Question Input --------------------
            if q_type == "multiple_choice":
                choices = q.get("choices", [])
                ans = st.radio(
                    f"Choose answer for Q{i+1}",
                    ["Select an answer"] + choices if choices else ["Select an answer"],
                    key=key,
                    index=0,
                )
                user_answers.append(ans)

            elif q_type == "true_false":
                ans = st.radio(
                    f"True or False for Q{i+1}",
                    ["Select an answer", "True", "False"],
                    key=key,
                    index=0,
                )
                user_answers.append(ans)

            elif q_type == "short_answer":
                ans = st.text_input(f"Answer for Q{i+1}", key=key)
                user_answers.append(ans)

            elif q_type == "fill_blank":
                ans = st.text_input(f"Fill the blank for Q{i+1}", key=key, placeholder="Type the missing word/number")
                user_answers.append(ans)

            else:
                ans = st.text_input(f"Answer for Q{i+1}", key=key)
                user_answers.append(ans)

        # Close the colored container at the end of each type section
        st.markdown("</div>", unsafe_allow_html=True)


        submitted = st.form_submit_button("Submit Answers")

    if submitted:
        score = 0
        total = len(questions)
        st.subheader("Results")
        for i, q in enumerate(questions):
            correct_raw = q.get("answer")
            correct = normalize_answer(correct_raw)
            user_raw = user_answers[i]
            user = normalize_answer(user_raw)

            q_type = q.get("type")
            pass_mark = False

            if q_type in ("short_answer", "fill_blank"):
                if user == correct:
                    pass_mark = True
            elif q_type == "multiple_choice":
                if normalize_answer(user_raw) == correct:
                    pass_mark = True
            elif q_type == "true_false":
                if user in ("true", "false") and user == correct:
                    pass_mark = True
            else:
                if user == correct:
                    pass_mark = True

            if pass_mark:
                st.success(f"✅ Q{i+1}: Correct — {q.get('question')}")
                score += 1
            else:
                st.error(f"❌ Q{i+1}: Incorrect — Your answer: **{user_raw or 'Blank'}** | Correct: **{q.get('answer')}**")

        st.markdown(f"### Final Score: **{score} / {total}**")
        if score == total:
            st.balloons()
            st.success("Perfect score! 🎉")

    reset_col, spacer = st.columns([1, 4])
    with reset_col:
        if st.button("🔄 New Set of Questions"):
            st.session_state.quiz_questions = []
            st.session_state.quiz_subject = None
            st.session_state.quiz_config = {}
            st.session_state.version += 1
            st.rerun()  # ✅ use st.rerun instead of st.experimental_rerun
else:
    st.info("No active quiz. Choose a subject tab, pick topic/grade, and click 'Start Quiz' to begin.")
