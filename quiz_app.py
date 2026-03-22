import streamlit as st
import time
import numpy as np
import uuid
from supabase import create_client

# --- Supabase Connection ---
@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def generate_attempt_id():
    return str(uuid.uuid4())[:8].upper()

def save_to_supabase(supabase, row_dict):
    supabase.table("quiz_responses").insert(row_dict).execute()

def get_cohort_avg_time(supabase):
    """
    Fetch mean avg_time from all previous attempts.
    Used for RTE = avg_time / cohort_avg_time.
    Returns None if no previous data exists.
    """
    try:
        response = supabase.table("quiz_responses").select("avg_time").execute()
        times = [row["avg_time"] for row in response.data if row["avg_time"] is not None]
        if len(times) == 0:
            return None
        return float(np.mean(times))
    except:
        return None

# --- Questions ---
questions = [
    {"q": "What is the time complexity of binary search on a sorted array?",
     "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "answer": "O(log n)"},
    {"q": "Which data structure follows the LIFO principle?",
     "options": ["Queue", "Stack", "Linked List", "Tree"], "answer": "Stack"},
    {"q": "Which traversal of a Binary Search Tree gives sorted output?",
     "options": ["Preorder", "Postorder", "Inorder", "Level order"], "answer": "Inorder"},
    {"q": "Which of the following is NOT a characteristic of Object-Oriented Programming?",
     "options": ["Encapsulation", "Inheritance", "Compilation", "Polymorphism"], "answer": "Compilation"},
    {"q": "Which protocol is primarily used to transfer web pages on the Internet?",
     "options": ["FTP", "HTTP", "SMTP", "TCP"], "answer": "HTTP"},
    {"q": "In operating systems, a process is best defined as:",
     "options": ["A program stored on disk", "A program in execution",
                 "A compiled program", "A program in memory only"], "answer": "A program in execution"},
    {"q": "Which data structure is typically used to implement recursion?",
     "options": ["Queue", "Stack", "Array", "Heap"], "answer": "Stack"},
    {"q": "Which SQL command is used to retrieve data from a database?",
     "options": ["GET", "SELECT", "FETCH", "EXTRACT"], "answer": "SELECT"},
    {"q": "Which sorting algorithm has the best average-case time complexity?",
     "options": ["Bubble Sort", "Selection Sort", "Merge Sort", "Insertion Sort"], "answer": "Merge Sort"},
    {"q": "Which layer of the OSI model is responsible for end-to-end communication?",
     "options": ["Network Layer", "Transport Layer", "Session Layer", "Application Layer"],
     "answer": "Transport Layer"}
]

total_questions = len(questions)

# --- Session State ---
if "attempt_id" not in st.session_state:
    st.session_state.attempt_id = generate_attempt_id()
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "revision_count" not in st.session_state:
    st.session_state.revision_count = 0
if "navigation_count" not in st.session_state:
    st.session_state.navigation_count = 0
if "quiz_start_time" not in st.session_state:
    st.session_state.quiz_start_time = time.time()
if "q_start_time" not in st.session_state:
    st.session_state.q_start_time = time.time()
if "question_durations" not in st.session_state:
    st.session_state.question_durations = {i: 0.0 for i in range(total_questions)}

if "wr_count" not in st.session_state:
    st.session_state.wr_count = 0
if "rw_count" not in st.session_state:
    st.session_state.rw_count = 0

supabase = get_client()

# --- Behavior Classification ---
def assign_behavior(avg_time, revision, navigation, accuracy,
                    unattempted, wr_ratio, rw_ratio, rte_score, time_variance):

    # ── 🔴 DISENGAGED ─────────────────────────────────────────────────────
    if unattempted >= 4:
        return "Disengaged"

    if avg_time < 3:
        return "Disengaged"

    if avg_time < 6 and accuracy < 0.40 and revision <= 2:
        return "Disengaged"

    if rte_score > 1.2 and accuracy < 0.30:
        return "Disengaged"

    # ── 🟢 FAST_RESPONSE ──────────────────────────────────────────────────
    if (avg_time < 8 and accuracy >= 0.80
            and revision <= 3 and wr_ratio < 0.3):
        return "Fast_Response"

    if (rte_score < 0.75 and accuracy >= 0.75
            and unattempted == 0):
        return "Fast_Response"

    # ── 🟡 HIGH_REVISION ──────────────────────────────────────────────────
    if (revision >= 5 and wr_ratio >= 0.4
            and accuracy >= 0.60):
        return "High_Revision"

    if (rw_ratio > 0.4 and revision >= 4
            and accuracy >= 0.50):
        return "High_Revision"

    if (navigation > 12 and revision >= 5
            and accuracy >= 0.60):
        return "High_Revision"

    # ── 🔵 DELIBERATIVE ───────────────────────────────────────────────────
    if (rte_score >= 1.0 and accuracy >= 0.60
            and revision >= 1):
        return "Deliberative"

    if (avg_time >= 8 and accuracy >= 0.60
            and rw_ratio <= 0.3 and time_variance > 10):
        return "Deliberative"

    return "Deliberative"

# --- Time Tracking ---
def log_duration():
    elapsed = time.time() - st.session_state.q_start_time
    idx = st.session_state.current_q
    st.session_state.question_durations[idx] += elapsed
    st.session_state.q_start_time = time.time()

def next_question():
    log_duration()
    st.session_state.navigation_count += 1
    st.session_state.current_q = (st.session_state.current_q + 1) % total_questions

def previous_question():
    log_duration()
    st.session_state.navigation_count += 1
    st.session_state.current_q = (st.session_state.current_q - 1) % total_questions

# --- UI ---
st.title("Quiz")

q_index = st.session_state.current_q
question = questions[q_index]

st.subheader(f"Question {q_index + 1} of {total_questions}")

previous_answer = st.session_state.answers.get(q_index)

selected_answer = st.radio(
    question["q"],
    question["options"],
    index=question["options"].index(previous_answer) if previous_answer else None,
    key=f"radio_{q_index}"
)

if selected_answer is not None:
    if q_index in st.session_state.answers:
        old_answer = st.session_state.answers[q_index]
        if old_answer != selected_answer:
            st.session_state.revision_count += 1

            correct_answer  = question["answer"]
            old_was_correct = (old_answer == correct_answer)
            new_is_correct  = (selected_answer == correct_answer)

            if not old_was_correct and new_is_correct:
                st.session_state.wr_count += 1
            elif old_was_correct and not new_is_correct:
                st.session_state.rw_count += 1

    st.session_state.answers[q_index] = selected_answer

col1, col2 = st.columns(2)
with col1:
    st.button("Previous", on_click=previous_question)
with col2:
    st.button("Next", on_click=next_question)

# --- Submit ---
if st.button("Submit Quiz"):
    log_duration()

    total_duration = time.time() - st.session_state.quiz_start_time

    durations = [st.session_state.question_durations[i] for i in range(total_questions)]

    # Free submit fix — distribute time equally if user never navigated
    if len([d for d in durations if d > 0]) <= 1:
        durations = [total_duration / total_questions] * total_questions

    avg_time = sum(durations) / total_questions

    # NaN/Inf guard on time_variance
    raw_variance = np.var(durations)
    if np.isnan(raw_variance) or np.isinf(raw_variance):
        time_variance = 0.0
    else:
        time_variance = round(float(raw_variance), 2)

    # Accuracy
    correct_count     = 0
    unattempted_count = 0
    for i, q in enumerate(questions):
        if i in st.session_state.answers:
            if st.session_state.answers[i] == q["answer"]:
                correct_count += 1
        else:
            unattempted_count += 1

    accuracy = correct_count / total_questions

    # wr_ratio & rw_ratio
    total_revisions = st.session_state.revision_count
    if total_revisions > 0:
        wr_ratio = round(float(st.session_state.wr_count) / total_revisions, 4)
        rw_ratio = round(float(st.session_state.rw_count) / total_revisions, 4)
    else:
        wr_ratio = 0.0
        rw_ratio = 0.0

    # rte_score from cohort avg
    cohort_avg = get_cohort_avg_time(supabase)
    if cohort_avg is not None and cohort_avg > 0:
        rte_score = round(float(avg_time) / cohort_avg, 4)
    else:
        rte_score = 1.0

    # ✅ Fix — time_variance now passed correctly
    behavior_label = assign_behavior(
        avg_time,
        st.session_state.revision_count,
        st.session_state.navigation_count,
        accuracy,
        unattempted_count,
        wr_ratio,
        rw_ratio,
        rte_score,
        time_variance        # ← was missing before
    )

    save_to_supabase(supabase, {
        "attempt_id":        str(st.session_state.attempt_id),
        "avg_time":          round(float(avg_time), 2),
        "time_variance":     time_variance,
        "revision_count":    int(st.session_state.revision_count),
        "navigation_count":  int(st.session_state.navigation_count),
        "unattempted_count": int(unattempted_count),
        "accuracy":          round(float(accuracy), 2),
        "wr_ratio":          wr_ratio,
        "rw_ratio":          rw_ratio,
        "rte_score":         rte_score,
        "behavior_label":    str(behavior_label)
    })

    st.success("Quiz Submitted Successfully!")
    st.write("Score:", correct_count)
    st.write("Unattempted:", unattempted_count)
    st.write("Behavior:", behavior_label)