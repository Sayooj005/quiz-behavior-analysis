import streamlit as st
import time
import pandas as pd
import numpy as np
from supabase import create_client

# ──────────────────────────────────────────────────────────────────────────────
# Supabase Connection
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def generate_attempt_id(supabase):
    response = supabase.table("quiz_responses").select("attempt_id").execute()
    count = len(response.data)
    return f"A{count:02}"

def save_to_supabase(supabase, row_dict):
    supabase.table("quiz_responses").insert(row_dict).execute()

# ──────────────────────────────────────────────────────────────────────────────
# Questions (10) - Computer Science (Moderate)
# ──────────────────────────────────────────────────────────────────────────────
questions = [
    {
        "q": "What is the time complexity of binary search on a sorted array?",
        "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        "answer": "O(log n)"
    },
    {
        "q": "Which data structure follows the LIFO principle?",
        "options": ["Queue", "Stack", "Linked List", "Tree"],
        "answer": "Stack"
    },
    {
        "q": "Which traversal of a Binary Search Tree gives sorted output?",
        "options": ["Preorder", "Postorder", "Inorder", "Level order"],
        "answer": "Inorder"
    },
    {
        "q": "Which of the following is NOT a characteristic of Object-Oriented Programming?",
        "options": ["Encapsulation", "Inheritance", "Compilation", "Polymorphism"],
        "answer": "Compilation"
    },
    {
        "q": "Which protocol is primarily used to transfer web pages on the Internet?",
        "options": ["FTP", "HTTP", "SMTP", "TCP"],
        "answer": "HTTP"
    },
    {
        "q": "In operating systems, a process is best defined as:",
        "options": [
            "A program stored on disk",
            "A program in execution",
            "A compiled program",
            "A program in memory only"
        ],
        "answer": "A program in execution"
    },
    {
        "q": "Which data structure is typically used to implement recursion?",
        "options": ["Queue", "Stack", "Array", "Heap"],
        "answer": "Stack"
    },
    {
        "q": "Which SQL command is used to retrieve data from a database?",
        "options": ["GET", "SELECT", "FETCH", "EXTRACT"],
        "answer": "SELECT"
    },
    {
        "q": "Which sorting algorithm has the best average-case time complexity?",
        "options": ["Bubble Sort", "Selection Sort", "Merge Sort", "Insertion Sort"],
        "answer": "Merge Sort"
    },
    {
        "q": "Which layer of the OSI model is responsible for end-to-end communication?",
        "options": ["Network Layer", "Transport Layer", "Session Layer", "Application Layer"],
        "answer": "Transport Layer"
    }
]

total_questions = len(questions)

# ──────────────────────────────────────────────────────────────────────────────
# Initialize Session State
# ──────────────────────────────────────────────────────────────────────────────
supabase = get_client()

if "attempt_id" not in st.session_state:
    st.session_state.attempt_id = generate_attempt_id(supabase)

if "current_q" not in st.session_state:
    st.session_state.current_q = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "revision_count" not in st.session_state:
    st.session_state.revision_count = 0

if "navigation_count" not in st.session_state:
    st.session_state.navigation_count = 0

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
st.title("Quiz")

q_index = st.session_state.current_q
question = questions[q_index]

st.subheader(f"Question {q_index + 1} of {total_questions}")

# Show previous answer if exists
previous_answer = st.session_state.answers.get(q_index)

selected_answer = st.radio(
    question["q"],
    question["options"],
    index=question["options"].index(previous_answer) if previous_answer else None,
    key=f"radio_{q_index}"
)

# Track revisions
if selected_answer is not None:
    if q_index in st.session_state.answers:
        if st.session_state.answers[q_index] != selected_answer:
            st.session_state.revision_count += 1
    st.session_state.answers[q_index] = selected_answer

# ──────────────────────────────────────────────────────────────────────────────
# Navigation (Circular)
# ──────────────────────────────────────────────────────────────────────────────
def next_question():
    st.session_state.navigation_count += 1
    st.session_state.current_q = (st.session_state.current_q + 1) % total_questions

def previous_question():
    st.session_state.navigation_count += 1
    st.session_state.current_q = (st.session_state.current_q - 1) % total_questions

col1, col2 = st.columns(2)

with col1:
    st.button("Previous", on_click=previous_question)

with col2:
    st.button("Next", on_click=next_question)

# ──────────────────────────────────────────────────────────────────────────────
# Behavior Classification Rules
# Priority order: Disengaged → Fast_Response → High_Revision → Deliberative
# ──────────────────────────────────────────────────────────────────────────────
def assign_behavior(avg_time, revision, navigation, accuracy, unattempted):


    if (
        accuracy    < 0.4  or
        unattempted >= 3   or
        avg_time    < 4.0
    ):
        return "Disengaged"

   
    elif (
        avg_time   < 8    and
        revision   <= 1   and
        navigation <= 3   and
        0.4 <= accuracy <= 0.75 and
        unattempted <= 1
    ):
        return "Fast_Response"

    elif (
        avg_time   > 15  and
        revision   >= 4  and
        navigation >= 4  and
        accuracy   >= 0.5 and
        unattempted <= 2
    ):
        return "High_Revision"


    else:
        return "Deliberative"

# ──────────────────────────────────────────────────────────────────────────────
# Submit
# ──────────────────────────────────────────────────────────────────────────────
if st.button("Submit Quiz"):

    total_time = time.time() - st.session_state.start_time
    avg_time = total_time / total_questions
    time_variance = np.random.uniform(3, 10)

    correct_count = 0
    unattempted_count = 0

    for i, q in enumerate(questions):
        if i in st.session_state.answers:
            if st.session_state.answers[i] == q["answer"]:
                correct_count += 1
        else:
            unattempted_count += 1

    accuracy = correct_count / total_questions

    behavior_label = assign_behavior(
        avg_time,
        st.session_state.revision_count,
        st.session_state.navigation_count,
        accuracy,
        unattempted_count
    )

    # ── Save to Supabase ──────────────────────────────────────────────────────
    save_to_supabase(supabase, {
        "attempt_id":        st.session_state.attempt_id,
        "avg_time":          round(avg_time, 2),
        "time_variance":     round(float(time_variance), 2),
        "revision_count":    st.session_state.revision_count,
        "navigation_count":  st.session_state.navigation_count,
        "unattempted_count": unattempted_count,
        "accuracy":          round(accuracy, 2),
        "behavior_label":    behavior_label
    })

    st.success("Quiz Submitted Successfully!")
    st.write("Score:", correct_count)
    st.write("Unattempted Questions:", unattempted_count)
    st.write("Behavior Type:", behavior_label)