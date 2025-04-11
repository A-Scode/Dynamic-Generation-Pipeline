import os , re
import streamlit as st
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Google GenerativeAI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")




# Summarization prompt
summary_prompt = """Welcome, Video Summarizer! Your task is to analyze the provided YouTube video transcript and generate a comprehensive, detailed summary that thoroughly captures the main points, key insights, and supporting details discussed throughout the video. You are encouraged to use important phrases, sentences, or even direct quotes from the transcript if they enhance clarity or accuracy. Present the summary in a well-structured format using bullet points for clarity. Focus on preserving the original tone and depth of the content. Do not limit the word count — prioritize completeness and context."""

# Get transcript from YouTube
def extract_transcript_details(youtube_video_url):
    video_id = youtube_video_url.split("v=")[1].split("&")[0]
    transcript_text = YouTubeTranscriptApi.get_transcript(video_id, languages=["hi", "en"])
    transcript = " ".join([i["text"] for i in transcript_text])
    return transcript, video_id

# Load from SRT
def extract_transcript_from_srt(uploaded_file):
    content = uploaded_file.read().decode("utf-8")
    import re
    lines = re.findall(r"(\d+\n)?(\d{2}:\d{2}:\d{2},\d{3} --> .+\n)?(.+)", content)
    transcript = " ".join([line[2] for line in lines if line[2]])
    return transcript

# Gemini Summary
def generate_summary(transcript):
    response = model.generate_content(summary_prompt + transcript)
    return response.text

# 🔍 Better Search Function
def search_transcript(transcript, keyword):
    sentences = re.split(r'(?<=[.?!])\s+', transcript)  # split into sentences
    keyword_pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    results = []

    for sent in sentences:
        if keyword_pattern.search(sent):
            sent_clean = sent.strip()
            if sent_clean not in results:
                results.append(sent_clean)

    return results

# Q&A
def ask_question(transcript, question):
    qna_prompt = f"Use this transcript to answer the question: {question}\n\nTranscript: {transcript}\nAnswer:"
    response = model.generate_content(qna_prompt)
    return response.text

# Quiz
def generate_quiz(transcript):
    quiz_prompt = """You are a quiz generator. Create exactly 3 multiple-choice questions based on the transcript below. Each question must test understanding of the content — including facts, concepts, or insights from different parts of the transcript.

Guidelines:
- Each question must have **4 unique, clearly different options**, labeled **a)** to **d)**.
- Only **one correct answer** per question.
- **Do NOT include the correct answer inside any of the options**.
- **Number the questions correctly as Q1., Q2., Q3.**
- Format exactly as shown below.

Format:
Q1. Question text here
a) Option 1  
b) Option 2  
c) Option 3  
d) Option 4  
Correct Answer: a)

Q2. Question text here
...

Use only the format above. Do not add any commentary or explanation. Begin below:
"""
    response = model.generate_content(quiz_prompt + transcript)
    return response.text

# Get video metadata
def get_video_info(video_id):
    api_key = os.getenv("YOUTUBE_API_KEY")
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        items = response.json().get("items")
        if items:
            snippet = items[0]["snippet"]
            return snippet["title"], snippet["thumbnails"]["high"]["url"]
    return "Untitled Video", f"http://img.youtube.com/vi/{video_id}/0.jpg"

# --- Streamlit UI ---
st.set_page_config(page_title="Dynamic Generation Pipeline")



# Title with actual YouTube icon
st.markdown(
    """
    <h1 style="display: flex; align-items: center;">
        <img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" alt="YouTube" width="40" style="margin-right: 10px;">
        Dynamic Generation Pipeline
    </h1>
    """,
    unsafe_allow_html=True
)

# Session State Setup
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "video_title" not in st.session_state:
    st.session_state.video_title = ""
if "video_thumbnail" not in st.session_state:
    st.session_state.video_thumbnail = ""

# --- Tabs ---
tabs = st.tabs(["📋 Summary", "🔍 Search", "🤖 Q&A", "🧠 Quiz"])

# 📋 SUMMARY TAB
with tabs[0]:
    st.subheader("Extract Transcript and Generate Summary")

    youtube_link = st.text_input("Enter YouTube Video Link:")
    uploaded_file = st.file_uploader("Or upload a transcript (.srt) file", type=["srt"])

    if youtube_link:
        try:
            transcript, video_id = extract_transcript_details(youtube_link)
            st.session_state.transcript = transcript
            video_title, thumbnail_url = get_video_info(video_id)
            st.session_state.video_title = video_title
            st.session_state.video_thumbnail = thumbnail_url
            st.image(thumbnail_url, use_container_width=True)
            st.markdown(f"### 📌 {video_title}")
        except Exception as e:
            st.error(f"Error: {e}")

    elif uploaded_file:
        transcript = extract_transcript_from_srt(uploaded_file)
        st.session_state.transcript = transcript
        st.success("Transcript loaded from .srt file.")

    if st.button("Generate Summary"):
        if st.session_state.transcript:
            summary = generate_summary(st.session_state.transcript)
            st.markdown("## 📝 Detailed Notes:")
            st.write(summary)

            st.download_button("📥 Download Notes", summary, "summary.md", mime="text/markdown")
        else:
            st.warning("Please provide a YouTube link or upload an .srt file.")

# 🔍 SEARCH TAB
with tabs[1]:
    st.subheader("Search Specific Keywords in Transcript")

    keyword = st.text_input("Enter keyword or phrase to search:")

    if keyword and st.session_state.transcript:
        results = search_transcript(st.session_state.transcript, keyword)

        if results:
            st.success(f"Found {len(results)} result(s):")
            for i, res in enumerate(results, 1):
                # Highlight keyword
                highlighted = re.sub(f"(?i)({re.escape(keyword)})", r"**\1**", res)
                st.markdown(f"**{i}.** {highlighted}")
        else:
            st.warning("No matches found.")

# 🤖 Q&A TAB
with tabs[2]:
    st.subheader("Ask Questions About the Transcript")
    if st.session_state.transcript:
        question = st.text_input("Ask a question:")
        if question:
            with st.spinner("Thinking..."):
                answer = ask_question(st.session_state.transcript, question)
                st.markdown("### 🤖 Answer")
                st.write(answer)
    else:
        st.warning("Transcript not loaded. Please use the Summary tab.")

# 🧠 QUIZ TAB
with tabs[3]:
    st.subheader("Generate and Take Quiz from Transcript")

    if st.session_state.transcript:

        if "quiz_data" not in st.session_state:
            st.session_state.quiz_data = []

        def parse_quiz(raw_text):
            questions = []
            blocks = raw_text.strip().split("Q")
            for block in blocks:
                if block.strip():
                    lines = block.strip().split("\n")
                    q_line = lines[0].strip()
                    q_text = f"Q{q_line}" if not q_line.startswith("Q") else q_line
                    options = [l.strip() for l in lines[1:5] if l.strip() and ")" in l]
                    while len(options) < 4:  # Ensure 4 options
                        options.append(f"Option {len(options)+1}) Placeholder")
                    correct_line = [l for l in lines if "Correct Answer" in l]
                    correct = correct_line[0].split(":")[1].strip() if correct_line else ""
                    questions.append({
                        "question": q_text,
                        "options": options,
                        "answer": correct
                    })
            return questions

        if st.button("Generate Quiz"):
            with st.spinner("Creating quiz..."):
                raw_quiz = generate_quiz(st.session_state.transcript)
                st.session_state.quiz_data = parse_quiz(raw_quiz)

        if st.session_state.quiz_data:
            st.markdown("### 🧠 Take the Quiz")

            for i, q in enumerate(st.session_state.quiz_data):
                st.markdown(f"**{q['question']}**")

                # Display radio with no default selection
                selected = st.radio(
                    label=f"Choose your answer for {q['question']}",
                    options=q["options"],
                    index=None,
                    key=f"quiz_q_{i}"
                )

                if selected:
                    if selected.startswith(q["answer"]):
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Incorrect. **Correct Answer:** {q['answer']}")
                st.markdown("---")

    else:
        st.warning("Transcript not loaded. Please use the Summary tab.")
