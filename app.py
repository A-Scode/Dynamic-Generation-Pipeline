import os, re
import streamlit as st
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# --- Streamlit UI ---
st.set_page_config(
    page_title="Dynamic Generation Pipeline",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Configure Google GenerativeAI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Custom CSS for styling
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load custom CSS
local_css("styles.css")

# --- Animation Components ---
def fade_in():
    return """
    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-in {
            animation: fadeIn 0.8s ease-out forwards;
        }
    </style>
    """

def pulse_animation():
    return """
    <style>
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .pulse {
            animation: pulse 2s infinite;
        }
    </style>
    """

# Inject animations
st.markdown(fade_in(), unsafe_allow_html=True)
st.markdown(pulse_animation(), unsafe_allow_html=True)

# Summarization prompt
summary_prompt = """Welcome, Video Summarizer! Your task is to analyze the provided YouTube video transcript and generate a comprehensive, detailed summary that thoroughly captures the main points, key insights, and supporting details discussed throughout the video. You are encouraged to use important phrases, sentences, or even direct quotes from the transcript if they enhance clarity or accuracy. Present the summary in a well-structured format using bullet points for clarity. Focus on preserving the original tone and depth of the content. Do not limit the word count — prioritize completeness and context."""

# Get transcript from YouTube
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[1].split("&")[0]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id, languages=["hi", "en"])
        transcript = " ".join([i["text"] for i in transcript_text])
        return transcript, video_id
    except Exception as e:
        st.error(f"Error extracting transcript: {str(e)}")
        return None, None

# Load from SRT
def extract_transcript_from_srt(uploaded_file):
    try:
        content = uploaded_file.read().decode("utf-8")
        lines = re.findall(r"(\d+\n)?(\d{2}:\d{2}:\d{2},\d{3} --> .+\n)?(.+)", content)
        transcript = " ".join([line[2] for line in lines if line[2]])
        return transcript
    except Exception as e:
        st.error(f"Error reading SRT file: {str(e)}")
        return None

# Gemini Summary
def generate_summary(transcript):
    try:
        response = model.generate_content(summary_prompt + transcript)
        return response.text
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return None

# Search Function
def search_transcript(transcript, keyword):
    try:
        sentences = re.split(r'(?<=[.?!])\s+', transcript)
        keyword_pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        results = []
        for sent in sentences:
            if keyword_pattern.search(sent):
                sent_clean = sent.strip()
                if sent_clean not in results:
                    results.append(sent_clean)
        return results
    except Exception as e:
        st.error(f"Error searching transcript: {str(e)}")
        return []

# Q&A
def ask_question(transcript, question):
    try:
        qna_prompt = f"Use this transcript to answer the question: {question}\n\nTranscript: {transcript}\nAnswer:"
        response = model.generate_content(qna_prompt)
        return response.text
    except Exception as e:
        st.error(f"Error answering question: {str(e)}")
        return None

# Quiz Generation and Parsing
def generate_quiz(transcript):
    try:
        quiz_prompt = """Generate exactly 3 multiple-choice questions based on the transcript below. Each question must have:
        - 4 unique options labeled a) to d)
        - Only one correct answer
        - Don't include answers in options
        - Numbered as Q1., Q2., Q3.
        - Format:
        Q1. Question text
        a) Option 1
        b) Option 2
        c) Option 3
        d) Option 4
        Correct Answer: a)
        """
        response = model.generate_content(quiz_prompt + transcript)
        return response.text
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
        return None

def parse_quiz(raw_quiz):
    questions = []
    try:
        question_blocks = re.split(r'Q\d+\.', raw_quiz)[1:]  # Split by question numbers
        for i, block in enumerate(question_blocks, 1):
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 6:  # At least question + 4 options + answer
                question_text = lines[0]
                options = lines[1:5]
                answer_line = next((line for line in lines if "Correct Answer:" in line), "")
                answer = answer_line.split(":")[1].strip() if answer_line else ""
                
                questions.append({
                    "question": f"Q{i}. {question_text}",
                    "options": options,
                    "answer": answer
                })
    except Exception as e:
        st.error(f"Error parsing quiz: {str(e)}")
    return questions

# Get video metadata
def get_video_info(video_id):
    try:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return "Untitled Video", f"http://img.youtube.com/vi/{video_id}/0.jpg"
            
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            items = response.json().get("items")
            if items:
                snippet = items[0]["snippet"]
                return snippet["title"], snippet["thumbnails"]["high"]["url"]
        return "Untitled Video", f"http://img.youtube.com/vi/{video_id}/0.jpg"
    except Exception as e:
        st.error(f"Error getting video info: {str(e)}")
        return "Untitled Video", f"http://img.youtube.com/vi/{video_id}/0.jpg"

# Custom header
st.markdown("""
<div class="header">
    <div class="header-content">
        <img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" class="youtube-icon">
        <h1>Dynamic Generation Pipeline</h1>
        <p class="subtitle">Transform YouTube videos into knowledge</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Session State Setup
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "video_title" not in st.session_state:
    st.session_state.video_title = ""
if "video_thumbnail" not in st.session_state:
    st.session_state.video_thumbnail = ""
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🔍 Search", "🤖 Q&A", "🧠 Quiz"])

# 📋 SUMMARY TAB
with tab1:
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.subheader("Extract Transcript and Generate Summary", divider='rainbow')
    
    with st.expander("📌 How to use", expanded=True):
        st.markdown("""
        - Paste a YouTube URL **or** upload an SRT file
        - Click "Generate Summary" to create detailed notes
        - Download your summary as Markdown
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        youtube_link = st.text_input("Enter YouTube Video Link:", placeholder="https://www.youtube.com/watch?v=...")
    with col2:
        uploaded_file = st.file_uploader("Or upload a transcript (.srt) file", type=["srt"])
    
    if youtube_link:
        try:
            with st.spinner("🔍 Extracting transcript..."):
                transcript, video_id = extract_transcript_details(youtube_link)
                if transcript and video_id:
                    st.session_state.transcript = transcript
                    video_title, thumbnail_url = get_video_info(video_id)
                    st.session_state.video_title = video_title
                    st.session_state.video_thumbnail = thumbnail_url
                    st.success("✅ Transcript loaded successfully!")
                    
                    col_img, col_title = st.columns([1, 3])
                    with col_img:
                        st.image(thumbnail_url, use_container_width=True, caption="Video Thumbnail")
                    with col_title:
                        st.markdown(f"""<div class="video-info"><h3>{video_title}</h3></div>""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    elif uploaded_file:
        with st.spinner("📂 Processing SRT file..."):
            transcript = extract_transcript_from_srt(uploaded_file)
            if transcript:
                st.session_state.transcript = transcript
                st.success("✅ Transcript loaded from .srt file.")

    if st.button("✨ Generate Summary", type="primary", use_container_width=True):
        if st.session_state.transcript:
            with st.spinner("🧠 Generating detailed summary..."):
                summary = generate_summary(st.session_state.transcript)
                if summary:
                    st.markdown("## 📝 Detailed Notes")
                    st.markdown('<div class="summary-box">', unsafe_allow_html=True)
                    st.markdown(summary)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.download_button("📥 Download Notes", summary, "summary.md", mime="text/markdown")
        else:
            st.warning("⚠️ Please provide a YouTube link or upload an .srt file.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 🔍 SEARCH TAB
with tab2:
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.subheader("Search Transcript Content", divider='rainbow')
    
    if not st.session_state.transcript:
        st.warning("No transcript loaded. Please use the Summary tab first.")
    else:
        with st.expander("🔎 Search Tips", expanded=False):
            st.markdown("""
            - Use specific keywords or phrases
            - Try different variations of your search term
            - Results show the context around your keyword
            """)
        
        keyword = st.text_input("Enter keyword or phrase to search:", placeholder="Search within transcript...")
        if keyword:
            with st.spinner("Searching transcript..."):
                results = search_transcript(st.session_state.transcript, keyword)
                if results:
                    st.success(f"🔍 Found {len(results)} result(s):")
                    for i, res in enumerate(results, 1):
                        highlighted = re.sub(f"(?i)({re.escape(keyword)})", r"<mark>\1</mark>", res)
                        st.markdown(f"""
                        <div class="search-result">
                            <div class="result-number">{i}.</div>
                            <div class="result-text">{highlighted}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No matches found. Try a different search term.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 🤖 Q&A TAB
with tab3:
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.subheader("Ask Questions About the Content", divider='rainbow')
    
    if not st.session_state.transcript:
        st.warning("No transcript loaded. Please use the Summary tab first.")
    else:
        with st.expander("💡 Question Examples", expanded=False):
            st.markdown("""
            - "What are the three main points discussed?"
            - "Explain the concept of X mentioned in the video"
            - "What examples were given for Y?"
            """)
        
        question = st.text_input("Ask a question about the video content:", placeholder="Type your question here...")
        if question:
            with st.spinner("Analyzing transcript..."):
                answer = ask_question(st.session_state.transcript, question)
                if answer:
                    st.markdown("### 🤖 Answer")
                    st.markdown(f"""<div class="answer-box"><div class="answer-content">{answer}</div></div>""", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 🧠 QUIZ TAB
with tab4:
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.subheader("Test Your Knowledge", divider='rainbow')
    
    if not st.session_state.transcript:
        st.warning("No transcript loaded. Please use the Summary tab first.")
    else:
        with st.expander("ℹ️ About the Quiz", expanded=False):
            st.markdown("""
            - Questions test understanding of key concepts
            - Each question has exactly one correct answer
            - Immediate feedback is provided
            """)
        
        if st.button("🎯 Generate New Quiz", type="primary", use_container_width=True):
            with st.spinner("Creating quiz questions..."):
                raw_quiz = generate_quiz(st.session_state.transcript)
                if raw_quiz:
                    st.session_state.quiz_data = parse_quiz(raw_quiz)
                    if st.session_state.quiz_data:
                        st.success("Quiz generated successfully!")
                    else:
                        st.error("Failed to parse quiz questions.")
        
        if st.session_state.quiz_data:
            st.markdown("### 📝 Quiz Time!")
            st.markdown("Select the correct answer for each question.")
            
            for i, q in enumerate(st.session_state.quiz_data):
                with st.container(border=True):
                    st.markdown(f"#### {q['question']}")
                    selected = st.radio(
                        label="Choose your answer:",
                        options=q["options"],
                        index=None,
                        key=f"quiz_q_{i}",
                        label_visibility="collapsed"
                    )
                    if selected:
                        if selected.startswith(q["answer"]):
                            st.success("✅ Correct! Well done!")
                        else:
                            st.error(f"❌ Incorrect. The correct answer is: **{q['answer']}**")
        else:
            st.info("Click 'Generate New Quiz' to create a quiz based on the transcript.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""<div class="footer"><p>Dynamic Generation Pipeline • Powered by Gemini AI • Streamlit</p></div>""", unsafe_allow_html=True)