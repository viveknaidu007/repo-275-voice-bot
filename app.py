import streamlit as st
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
from dotenv import load_dotenv
import os
import io
import time
from datetime import datetime
import threading
from typing import Optional

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Voice Bot Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .chat-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
        color: #0d47a1;
    }
    .bot-message {
        background-color: #f1f8e9;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
        color: #1b5e20;
    }
    .user-message strong, .bot-message strong { color: inherit; }
    textarea, .stTextArea textarea {
        color: #111 !important;
        background-color: #fff !important;
    }
    .timestamp { opacity: 0.7; font-weight: normal; font-size: 0.9em; }
    .voice-button {
        background-color: #ff4444;
        color: white;
        border: none;
        border-radius: 50px;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        cursor: pointer;
    }
    .status-indicator {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .status-listening {
        background-color: #ffebee;
        color: #c62828;
    }
    .status-processing {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .status-ready {
        background-color: #e8f5e8;
        color: #2e7d32;
    }
    .scroll-box { max-height: 360px; overflow-y: auto; padding-right: 0.5rem; }
</style>
""", unsafe_allow_html=True)

class VoiceBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Microphone and TTS can fail if drivers or audio stack aren't available (e.g., PyAudio issues)
        self.has_microphone = False
        self.tts_engine = None
        try:
            # Probe microphone availability without keeping a persistent context
            with sr.Microphone() as _:
                self.has_microphone = True
        except Exception as e:
            self.has_microphone = False
            st.warning(f"Microphone setup failed. Voice input will be disabled. Details: {e}")
        try:
            self.tts_engine = pyttsx3.init()
        except Exception as e:
            st.warning(f"Text-to-Speech setup failed. Audio responses will be disabled. Details: {e}")
        self.setup_tts()
        self.setup_gemini()
        
    def setup_tts(self):
        """Configure text-to-speech engine"""
        if not self.tts_engine:
            return
        voices = self.tts_engine.getProperty('voices')
        if voices:
            # Try to use a female voice if available
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            else:
                self.tts_engine.setProperty('voice', voices[0].id)

        self.tts_engine.setProperty('rate', 180)  # Speed of speech
        self.tts_engine.setProperty('volume', 0.8)  # Volume level
    
    def setup_gemini(self):
        """Configure Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_gemini_api_key_here':
            st.error("❌ Please set your GEMINI_API_KEY in the .env file")
            st.stop()
        
        genai.configure(api_key=api_key)
        # Prefer newer model if available, fall back gracefully
        preferred_models = ['gemini-1.5-flash', 'gemini-pro']
        model = None
        for m in preferred_models:
            try:
                model = genai.GenerativeModel(m)
                break
            except Exception:
                continue
        if not model:
            # As an ultimate fallback keep original
            model = genai.GenerativeModel('gemini-pro')
        self.model = model
    
    def listen_for_speech(self, timeout: int = 5) -> Optional[str]:
        """Capture and convert speech to text"""
        try:
            if not self.has_microphone:
                st.error("Microphone unavailable. Please install PyAudio correctly or use text input.")
                return None
            # Use a fresh microphone context each call to avoid nested context errors
            with sr.Microphone() as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                st.info("🎤 Listening... Please speak now!")
                
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                
                st.info("🔄 Processing speech...")
                # Convert speech to text
                text = self.recognizer.recognize_google(audio)
                return text
                
        except sr.WaitTimeoutError:
            st.warning("⏰ No speech detected. Please try again.")
            return None
        except sr.UnknownValueError:
            st.warning("❓ Could not understand the speech. Please try again.")
            return None
        except sr.RequestError as e:
            st.error(f"❌ Speech recognition error: {e}")
            return None
    
    def get_personal_context(self) -> str:
        """Return personal context for the AI to respond as the applicant"""
        return """
        Answer the questions naturally and conversationally,
        Keep responses concise but informative.
        """
    
    def generate_response(self, question: str) -> str:
        """Generate response using Gemini API"""
        try:
            context = self.get_personal_context()
            # Include recent conversation context (last 6 messages = 3 turns)
            convo_lines = []
            history = st.session_state.get('chat_history', [])[-6:]
            for msg in history:
                role = 'Interviewer' if msg.get('role') == 'user' else 'Candidate'
                convo_lines.append(f"{role}: {msg.get('content','')}")
            convo = "\n".join(convo_lines)
            prompt = (
                f"{context}\n\n"
                f"Conversation so far:\n{convo}\n\n"
                f"Question: {question}\n\n"
                f"Your Response:"
            )
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"I apologize, I'm having trouble processing that question right now. Error: {str(e)}"
    
    def speak_text(self, text: str):
        """Convert text to speech"""
        try:
            if not self.tts_engine:
                st.info("TTS unavailable. Skipping audio playback.")
                return
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            st.error(f"Text-to-speech error: {e}")

def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Voice Bot </h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'voice_bot' not in st.session_state:
        st.session_state.voice_bot = VoiceBot()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'voice_history' not in st.session_state:
        st.session_state.voice_history = []
    if 'text_history' not in st.session_state:
        st.session_state.text_history = []
    
    if 'is_listening' not in st.session_state:
        st.session_state.is_listening = False
    if 'voice_active' not in st.session_state:
        st.session_state.voice_active = False
    if 'voice_processing' not in st.session_state:
        st.session_state.voice_processing = False
    if 'status' not in st.session_state:
        st.session_state.status = 'ready'  # ready | listening | processing | speaking
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Interview Voice Bot")
        st.markdown("""
        This voice bot is designed to answer interview questions as the job applicant.
        
        **How to use:**
        1. Click 'Start Voice Input' to speak your question
        2. Or type your question in the text box
        3. Get personalized responses
        
        **Sample Questions:**
        - What should we know about your life story?
        - What's your #1 superpower?
        - What are the top 3 areas you'd like to grow in?
        - What misconception do your coworkers have about you?
        - How do you push your boundaries and limits?
        """)
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Install help if audio stack missing
        if st.session_state.get('voice_bot') and (not st.session_state.voice_bot.has_microphone):
            st.warning("Voice input is disabled. To enable, install PyAudio wheels for Windows.")
            st.code(
                """
pip install --upgrade pip wheel setuptools
pip install pyaudio==0.2.14
                """.strip(),
                language="bash"
            )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Chat Interface")
        
        # Voice input section
        st.markdown("### 🎤 Voice Input")
        voice_col1, voice_col2 = st.columns([1, 1])
        
        with voice_col1:
            disabled = (not st.session_state.voice_bot.has_microphone)
            # Toggle Start/End voice session
            if not st.session_state.voice_active:
                if st.button("🎤 Start Voice Input", key="voice_button_start", help="Start continuous voice conversation", disabled=disabled):
                    st.session_state.voice_active = True
                    st.session_state.status = 'ready'
                    st.rerun()
            else:
                if st.button("⏹ End Voice Input", key="voice_button_end", help="Stop continuous voice conversation"):
                    st.session_state.voice_active = False
                    st.session_state.voice_processing = False
                    st.session_state.status = 'ready'
                    st.rerun()
        
        with voice_col2:
            if not st.session_state.voice_bot.has_microphone:
                st.info("🎙️ Microphone not available. Use text input below.")
            else:
                if not st.session_state.voice_active:
                    st.info("🎙️ Click Start to begin hands-free voice conversation.")
                else:
                    st.info("🎙️ Voice session active. Click End to stop.")

        # Continuous voice loop: run one cycle per rerun while active
        if st.session_state.voice_active and not st.session_state.voice_processing:
            try:
                st.session_state.voice_processing = True
                st.session_state.status = 'listening'
                # Listen
                question = st.session_state.voice_bot.listen_for_speech(timeout=10)
                if not question:
                    # If no speech detected, set ready and iterate
                    st.session_state.status = 'ready'
                    st.session_state.voice_processing = False
                    st.rerun()

                # Record user question
                st.success(f"📝 Captured: {question}")
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.voice_history.append({
                    "role": "user",
                    "content": question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })

                # Generate response
                st.session_state.status = 'processing'
                response = st.session_state.voice_bot.generate_response(question)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.voice_history.append({
                    "role": "assistant",
                    "content": response,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })

                # Speak response
                st.session_state.status = 'speaking'
                st.session_state.voice_bot.speak_text(response)

            finally:
                # Prepare for next cycle
                st.session_state.status = 'ready'
                st.session_state.voice_processing = False
                if st.session_state.voice_active:
                    st.rerun()
        
        # Text input section
        st.markdown("### ⌨️ Text Input")
        text_question = st.text_area(
            "Type your interview question:",
            placeholder="e.g., What should we know about your life story in a few sentences?",
            height=100
        )
        
        if st.button("📤 Send Question", key="text_button"):
            if text_question.strip():
                # Add to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": text_question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.text_history.append({
                    "role": "user",
                    "content": text_question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                
                # Generate response
                with st.spinner("🤔 Generating response..."):
                    response = st.session_state.voice_bot.generate_response(text_question)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "ts": datetime.now().strftime("%H:%M:%S")
                    })
                    st.session_state.text_history.append({
                        "role": "assistant",
                        "content": response,
                        "ts": datetime.now().strftime("%H:%M:%S")
                    })
                
                st.rerun()
        
        # Helper: render a list of messages inside a scroll box
        def render_history(messages, empty_hint: str):
            if not messages:
                st.info(empty_hint)
                return
            parts = ['<div class="chat-container scroll-box">']
            for message in messages:
                ts = message.get("ts", "")
                time_str = f" ({ts})" if ts else ""
                if message.get("role") == "user":
                    parts.append(
                        f'<div class="user-message"><strong>🧑 Interviewer{time_str}:</strong> {message.get("content","")}</div>'
                    )
                else:
                    parts.append(
                        f'<div class="bot-message"><strong>🤖 Candidate{time_str}:</strong> {message.get("content","")}</div>'
                    )
            parts.append('</div>')
            st.markdown("".join(parts), unsafe_allow_html=True)

        # All conversation
        st.markdown("### 💭 Conversation History (All)")
        render_history(st.session_state.chat_history, "👋 Start the conversation by asking an interview question!")

        # Split sections
        st.markdown("### 🎙️ Voice Conversation History")
        render_history(st.session_state.voice_history, "No voice interactions yet.")

        st.markdown("### ⌨️ Text Conversation History")
        render_history(st.session_state.text_history, "No text interactions yet.")
    
    with col2:
        st.subheader("📋 Instructions")
        st.markdown("""
        **Quick Start:**
        1. Make sure your microphone is working
        2. Click the voice button to ask questions
        3. Or type your questions manually
        4. The bot will respond
        
        **Technical Notes:**
        - Uses Google Speech Recognition
        - Powered by Gemini AI
        - Text-to-speech for audio responses
        - Designed for 100x AI Agent Team interview
        """)
        
        # Status indicator
        current_status = st.session_state.get('status', 'ready')
        if current_status == 'listening':
            st.markdown('<div class="status-indicator status-listening">🎤 LISTENING</div>', unsafe_allow_html=True)
        elif current_status == 'processing':
            st.markdown('<div class="status-indicator status-processing">⏳ PROCESSING</div>', unsafe_allow_html=True)
        elif current_status == 'speaking':
            st.markdown('<div class="status-indicator status-processing">🔊 SPEAKING</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-ready">✅ READY</div>', unsafe_allow_html=True)
        
        # Sample questions
        st.markdown("**💡 Sample Questions:**")
        sample_questions = [
            "What should we know about your life story?",
            "What's your #1 superpower?",
            "What are the top 3 areas you'd like to grow in?",
            "What misconception do your coworkers have about you?",
            "How do you push your boundaries and limits?"
        ]
        
        for question in sample_questions:
            if st.button(f"❓ {question}", key=f"sample_{question}"):
                # Add to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.text_history.append({
                    "role": "user",
                    "content": question,
                    "ts": datetime.now().strftime("%H:%M:%S")
                })
                
                # Generate response
                with st.spinner("🤔 Generating response..."):
                    response = st.session_state.voice_bot.generate_response(question)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "ts": datetime.now().strftime("%H:%M:%S")
                    })
                    st.session_state.text_history.append({
                        "role": "assistant",
                        "content": response,
                        "ts": datetime.now().strftime("%H:%M:%S")
                    })
                
                st.rerun()

if __name__ == "__main__":
    main()