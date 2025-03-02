import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
from groq import Groq
from googleapiclient.discovery import build
from dotenv import load_dotenv
import random

load_dotenv()

client = Groq(api_key=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)
YOUTUBE_API_KEY = AIzaSyBKBX2BIFv84gcXW0blwht21edprKMpljw
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Checklist Functions
def generate_checklist(topic):
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": f"Generate a concise checklist (max 10 items) of key topics for studying {topic}."}],
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        stream=False,
    )
    checklist = chat_completion.choices[0].message.content.split("\n")
    checklist = [item.strip() for item in checklist if item.strip() and not item.lower().startswith("Here's a")]
    checklist.pop(0)
    return checklist

def get_best_youtube_video(query):
    request = youtube.search().list(
        part="snippet",
        maxResults=3,
        q=query,
        type="video",
        order="relevance"
    )
    response = request.execute()
    if response['items']:
        video_id = response['items'][0]['id']['videoId']
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

def generate_youtube_links(checklist):
    youtube_links = {}
    for item in checklist:
        video_link = get_best_youtube_video(item)
        if video_link:
            youtube_links[item] = video_link
    return youtube_links

# Quiz Functions
def generate_quiz_question(topic, checklist_item, difficulty):
    prompt = f"Create a {difficulty}-difficulty multiple choice question about '{checklist_item}' in the context of {topic}. Provide 1 correct answer and 3 incorrect answers. Return in this format:\nQuestion: [question text]\nA) [correct answer]\nB) [incorrect1]\nC) [incorrect2]\nD) [incorrect3]"
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        stream=False,
    )
    response = chat_completion.choices[0].message.content.split("\n")
    question = response[0].replace("Question: ", "")
    options = [line[3:] for line in response[1:5]]
    correct_answer = options[0]
    random.shuffle(options)
    return question, options, correct_answer

def generate_quiz(topic, checklist, difficulty):
    questions = []
    random_items = random.sample(checklist, min(5, len(checklist)))
    for item in random_items:
        q, opts, correct = generate_quiz_question(topic, item, difficulty)
        questions.append({"question": q, "options": opts, "correct": correct})
    return questions

# Streamlit UI
st.title("Study Preparation App")

# Main Checklist Section
topic = st.text_input("Enter the topic you want to study:")
if st.button("Generate Checklist"):
    if topic:
        checklist = generate_checklist(topic)
        youtube_links = generate_youtube_links(checklist)
        
        if checklist:
            st.session_state["checklist"] = checklist
            st.session_state["progress"] = {item: False for item in checklist}
            st.session_state["topic"] = topic
            st.session_state["show_quiz"] = False
        else:
            st.error("Failed to generate checklist. Try again.")

        if youtube_links:
            st.session_state["youtube_links"] = youtube_links
        else:
            st.session_state["youtube_links"] = {}
    else:
        st.error("Please enter a topic.")

if "checklist" in st.session_state:
    st.subheader("Your Study Checklist")
    for item in st.session_state["checklist"]:
        st.session_state["progress"][item] = st.checkbox(item, st.session_state["progress"].get(item, False), key=item)

    completed = sum(st.session_state["progress"].values())
    total = len(st.session_state["progress"])
    st.progress(completed / total)

    progress_df = pd.DataFrame({"Status": ["Completed", "Remaining"], "Count": [completed, total - completed]})
    fig = px.pie(progress_df, names="Status", values="Count", title="Progress Overview")
    st.plotly_chart(fig)

    st.subheader("Recommended YouTube Videos")
    if "youtube_links" in st.session_state and st.session_state["youtube_links"]:
        for item, link in st.session_state["youtube_links"].items():
            st.markdown(f"**{item}**: [📺 Watch Video]({link})")
    else:
        st.write("No YouTube links available.")

    # Quiz Section Trigger
    difficulty = st.selectbox("Select Quiz Difficulty", ["Easy", "Medium", "Hard"], key="difficulty")
    if st.button("Take Quiz"):
        st.session_state["show_quiz"] = True
        st.session_state["quiz"] = generate_quiz(st.session_state["topic"], st.session_state["checklist"], difficulty)
        st.session_state["answers"] = {}
        st.session_state["submitted"] = False

    # Quiz Display
    if st.session_state.get("show_quiz", False):
        st.subheader(f"Study Quiz ({difficulty} Difficulty)")
        if "quiz" not in st.session_state:
            st.session_state["quiz"] = generate_quiz(st.session_state["topic"], st.session_state["checklist"], difficulty)
            st.session_state["answers"] = {}
            st.session_state["submitted"] = False

        quiz = st.session_state["quiz"]
        
        with st.form(key="quiz_form"):
            for i, q in enumerate(quiz, 1):
                st.write(f"**Question {i}: {q['question']}**")
                # Use index=None to ensure no default selection
                answer = st.radio(
                    f"Select an answer for Q{i}",
                    q["options"],
                    index=None,  # No default selection
                    key=f"q{i}"
                )
                st.session_state["answers"][i] = answer
            
            submit_button = st.form_submit_button("Submit Quiz")
            
            if submit_button:
                # Check if all questions have been answered
                if all(st.session_state["answers"].get(i) is not None for i in range(1, len(quiz) + 1)):
                    st.session_state["submitted"] = True
                else:
                    st.error("Please answer all questions before submitting.")

        if st.session_state["submitted"]:
            score = 0
            st.subheader("Results")
            for i, q in enumerate(quiz, 1):
                user_answer = st.session_state["answers"].get(i)
                is_correct = user_answer == q["correct"]
                score += 1 if is_correct else 0
                st.write(f"Q{i}: {q['question']}")
                st.write(f"Your answer: {user_answer}")
                st.write(f"Correct answer: {q['correct']}")
                st.write(f"{'✅ Correct' if is_correct else '❌ Incorrect'}")
                st.write("---")

            st.write(f"Your Score: {score}/{len(quiz)} ({(score/len(quiz)*100):.1f}%)")
            
            if st.button("Retake Quiz"):
                del st.session_state["quiz"]
                del st.session_state["answers"]
                del st.session_state["submitted"]
                st.session_state["quiz"] = generate_quiz(st.session_state["topic"], st.session_state["checklist"], difficulty)
                st.session_state["answers"] = {}
                st.session_state["submitted"] = False
                st.session_state["show_quiz"] = True
                st.rerun()
            
            if st.button("Back to Checklist"):
                st.session_state["show_quiz"] = False
                st.rerun()

# Run with: streamlit run Home.py

